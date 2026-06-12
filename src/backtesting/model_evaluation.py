"""Orchestrazione valutazione modelli e report promotion gate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.backtesting.metrics import BacktestMetrics
from src.backtesting.promotion_gate import (
    PromotionDecision,
    PromotionThresholds,
    decision_as_dict,
    evaluate_promotion,
    summarize_metrics,
)
from src.backtesting.walk_forward import WalkForwardReport, run_walk_forward
from src.backtesting.walk_forward_trained import run_walk_forward_refit
from src.config import BACKTESTS_DIR, Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.dataset_builder import MatchDataset
from src.models.registry import build_ensemble


def _avg_feature_count(report: WalkForwardReport) -> float:
    if not report.windows:
        return 0.0
    total = sum(w.training_features or 0 for w in report.windows)
    return total / len(report.windows)


def _report_block(
    report: WalkForwardReport,
    *,
    model: str,
    feature_policy: str | None = None,
) -> dict:
    return {
        "model": model,
        "feature_policy": feature_policy,
        "metrics": summarize_metrics(report.aggregate_metrics),
        "windows": len(report.windows),
        "tested_matches": report.total_tested_matches,
        "avg_selected_features": _avg_feature_count(report),
        "training_mode": report.training_mode,
    }


def run_model_evaluation(
    dataset: MatchDataset,
    settings: Settings,
    *,
    profile: str | None = None,
    baseline_policy: str = "full",
    candidate_policy: str = "compact",
    min_train_matches: int = 10,
    test_window_size: int = 5,
    step_size: int = 5,
    thresholds: PromotionThresholds | None = None,
    include_ensemble_baseline: bool = False,
    output_dir: Path | None = None,
) -> dict:
    """Esegue walk-forward baseline/candidate e promotion gate."""
    profile_name = parse_data_profile(profile or settings.data_profile)
    gate_thresholds = thresholds or PromotionThresholds()

    common_wf = {
        "profile": profile_name,
        "min_train_matches": min_train_matches,
        "test_window_size": test_window_size,
        "step_size": step_size,
    }

    baseline_report = run_walk_forward_refit(
        dataset,
        settings,
        feature_policy=baseline_policy,
        **common_wf,
    )
    candidate_report = run_walk_forward_refit(
        dataset,
        settings,
        feature_policy=candidate_policy,
        **common_wf,
    )

    baseline_features = _avg_feature_count(baseline_report)
    candidate_features = _avg_feature_count(candidate_report)

    decision = evaluate_promotion(
        candidate_report,
        baseline_report,
        gate_thresholds,
        candidate_name=f"feature_trained/{candidate_policy}",
        baseline_name=f"feature_trained/{baseline_policy}",
        candidate_avg_features=candidate_features,
        baseline_avg_features=baseline_features,
    )

    informational: dict = {}
    if include_ensemble_baseline:
        ensemble = build_ensemble(settings, dataset)
        ensemble_report = run_walk_forward(
            dataset,
            ensemble,
            settings,
            min_train_matches=min_train_matches,
            test_window_size=test_window_size,
            step_size=step_size,
        )
        informational["ensemble"] = {
            "metrics": summarize_metrics(ensemble_report.aggregate_metrics),
            "windows": len(ensemble_report.windows),
            "tested_matches": ensemble_report.total_tested_matches,
            "training_mode": ensemble_report.training_mode,
            "note": "not directly equivalent to feature_trained refit",
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": dataset.league_id,
        "profile": profile_name,
        "evaluation_mode": "walk_forward_refit_policy_comparison",
        "baseline": _report_block(
            baseline_report,
            model="feature_trained",
            feature_policy=baseline_policy,
        ),
        "candidate": _report_block(
            candidate_report,
            model="feature_trained",
            feature_policy=candidate_policy,
        ),
        "promotion_decision": decision_as_dict(decision),
        "informational_baselines": informational,
        "thresholds": {
            "min_tested_matches": gate_thresholds.min_tested_matches,
            "min_windows": gate_thresholds.min_windows,
            "max_brier_delta": gate_thresholds.max_brier_delta,
            "max_logloss_delta": gate_thresholds.max_logloss_delta,
            "max_calibration_gap_delta": gate_thresholds.max_calibration_gap_delta,
            "max_pick_overconfidence_rate": gate_thresholds.max_pick_overconfidence_rate,
        },
    }

    out_dir = output_dir or BACKTESTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"model_evaluation_{stamp}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(json_path)
    payload["_decision"] = decision
    return payload


def format_evaluation_console(payload: dict) -> str:
    """Formatta output console leggibile."""
    baseline = payload["baseline"]
    candidate = payload["candidate"]
    decision: PromotionDecision = payload["_decision"]
    base_m = baseline["metrics"]
    cand_m = candidate["metrics"]
    deltas = decision.metric_deltas

    lines = [
        f"Model evaluation — league {payload['league_id']}, profile {payload['profile']}",
        "",
        f"Baseline:  {decision.baseline_name}",
        f"Candidate: {decision.candidate_name}",
        "",
        f"Windows: {decision.windows}",
        f"Tested matches: {decision.tested_matches}",
        "",
        "Metrics:",
        (
            f"  Brier:    baseline={base_m['brier_score']:.4f} "
            f"candidate={cand_m['brier_score']:.4f} "
            f"delta={deltas['brier_score']:+.4f}"
        ),
        (
            f"  LogLoss:  baseline={base_m['log_loss']:.4f} "
            f"candidate={cand_m['log_loss']:.4f} "
            f"delta={deltas['log_loss']:+.4f}"
        ),
        (
            f"  Accuracy: baseline={base_m['accuracy']:.3f} "
            f"candidate={cand_m['accuracy']:.3f} "
            f"delta={deltas['accuracy']:+.3f}"
        ),
        (
            f"  CalGap:   baseline={base_m['mean_calibration_gap']:.4f} "
            f"candidate={cand_m['mean_calibration_gap']:.4f} "
            f"delta={deltas['mean_calibration_gap']:+.4f}"
        ),
        (
            f"  Features: baseline={baseline['avg_selected_features']:.0f} "
            f"candidate={candidate['avg_selected_features']:.0f}"
        ),
        "",
        f"Decision: {decision.status.upper()}",
    ]
    if decision.reasons:
        lines.append("Reasons:")
        for reason in decision.reasons:
            lines.append(f"  - {reason}")
    if decision.warnings:
        lines.append("Warnings:")
        for warning in decision.warnings:
            lines.append(f"  - {warning}")
    if payload.get("informational_baselines"):
        lines.append("")
        lines.append("Informational baselines:")
        for name, block in payload["informational_baselines"].items():
            m = block["metrics"]
            lines.append(
                f"  {name}: brier={m['brier_score']:.4f} "
                f"accuracy={m['accuracy']:.3f} ({block.get('note', '')})"
            )
    lines.append("")
    lines.append(f"Report JSON: {payload.get('report_path', '')}")
    return "\n".join(lines)
