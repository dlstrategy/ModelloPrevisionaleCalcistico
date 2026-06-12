"""Walk-forward con refit reale per feature_trained."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.backtesting.walk_forward import WalkForwardReport, WalkForwardWindow
from src.config import BACKTESTS_DIR, Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import MatchOutcome
from src.domain.models import Prediction
from src.models.feature_trained import FeatureTrainedModel
from src.prediction.predict_match import predict_match
from src.training.dataset import build_training_samples
from src.training.feature_policy import (
    apply_feature_policy_to_sample,
    collect_feature_names,
    parse_feature_policy,
    select_features_for_policy,
)
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model

TRAINING_MODE_REFIT = "walk_forward_refit"


def _ensure_disjoint_train_test(train_ids: frozenset[int], test_ids: frozenset[int]) -> None:
    overlap = train_ids & test_ids
    if overlap:
        raise ValueError(
            f"Walk-forward leakage: train e test condividono fixture_ids {sorted(overlap)}"
        )


def _training_config_for_policy(
    policy_name: str,
    *,
    l2: float | None = None,
    clip_value: float | None = None,
) -> SoftmaxTrainingConfig:
    policy = parse_feature_policy(policy_name)
    return SoftmaxTrainingConfig(
        epochs=200,
        min_samples=5,
        l2=l2 if l2 is not None else policy.default_l2,
        clip_value=clip_value if clip_value is not None else policy.default_clip_value,
    )


def run_walk_forward_refit(
    dataset: MatchDataset,
    settings: Settings,
    *,
    profile: str | None = None,
    min_train_matches: int = 10,
    test_window_size: int = 5,
    step_size: int = 5,
    feature_policy: str = "full",
    l2: float | None = None,
    clip_value: float | None = None,
) -> WalkForwardReport:
    """Walk-forward con refit per finestra — valutazione onesta per feature_trained."""
    profile_name = parse_data_profile(profile or settings.data_profile)
    policy = parse_feature_policy(feature_policy)
    finished = [
        m
        for m in dataset.matches
        if m.is_finished and m.actual_outcome is not None
    ]
    finished.sort(key=lambda m: m.starting_at)

    windows: list[WalkForwardWindow] = []
    all_predictions: list[Prediction] = []
    all_actuals: list[MatchOutcome] = []

    train_config = _training_config_for_policy(
        policy.name,
        l2=l2,
        clip_value=clip_value,
    )
    train_end_idx = min_train_matches
    window_index = 0

    while train_end_idx + test_window_size <= len(finished):
        train_matches = finished[:train_end_idx]
        test_matches = finished[train_end_idx : train_end_idx + test_window_size]
        train_ids = frozenset(m.id for m in train_matches)
        test_ids = frozenset(m.id for m in test_matches)
        _ensure_disjoint_train_test(train_ids, test_ids)

        train_samples = build_training_samples(
            dataset,
            settings,
            profile=profile_name,
            only_match_ids=train_ids,
        )

        original_count = len(collect_feature_names(train_samples))
        selected_names, selection_warnings = select_features_for_policy(train_samples, policy)
        filtered_samples = [
            apply_feature_policy_to_sample(sample, selected_names) for sample in train_samples
        ]

        artifact = train_softmax_model(
            filtered_samples,
            league_id=dataset.league_id,
            data_profile=profile_name,
            config=train_config,
            feature_names=selected_names,
            feature_policy=policy.name,
            original_feature_count=original_count,
            feature_selection_warnings=tuple(selection_warnings),
            regularization_notes=(f"walk_forward_policy={policy.name}",),
        )
        window_model = FeatureTrainedModel.from_artifact(settings, dataset, artifact)

        predictions: list[Prediction] = []
        actuals: list[MatchOutcome] = []
        for match in test_matches:
            pred = predict_match(
                dataset,
                match,
                window_model,
                settings,
                as_of=match.starting_at,
            )
            predictions.append(pred)
            actuals.append(match.actual_outcome)  # type: ignore[arg-type]

        metrics = compute_metrics(predictions, actuals)
        windows.append(
            WalkForwardWindow(
                window_index=window_index,
                train_until=train_matches[-1].starting_at.isoformat(sep=" "),
                test_from=test_matches[0].starting_at.isoformat(sep=" "),
                test_to=test_matches[-1].starting_at.isoformat(sep=" "),
                train_matches=len(train_matches),
                test_matches=len(test_matches),
                metrics=metrics,
                predictions=tuple(predictions),
                actuals=tuple(actuals),
                train_from=train_matches[0].starting_at.isoformat(sep=" "),
                training_features=len(artifact.feature_names),
                training_warnings=artifact.warnings,
                feature_policy=policy.name,
                original_feature_count=original_count,
                feature_selection_warnings=tuple(selection_warnings),
                clip_value=train_config.clip_value,
                training_l2=train_config.l2,
            )
        )
        all_predictions.extend(predictions)
        all_actuals.extend(actuals)

        window_index += 1
        train_end_idx += step_size

    aggregate = compute_metrics(all_predictions, all_actuals)

    return WalkForwardReport(
        model_name="feature_trained",
        league_id=dataset.league_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        min_train_matches=min_train_matches,
        test_window_size=test_window_size,
        step_size=step_size,
        training_mode=TRAINING_MODE_REFIT,
        total_tested_matches=len(all_predictions),
        windows=tuple(windows),
        aggregate_metrics=aggregate,
        data_profile=profile_name,
    )


def _avg_feature_count(report: WalkForwardReport) -> float:
    if not report.windows:
        return 0.0
    total = sum(w.training_features or 0 for w in report.windows)
    return total / len(report.windows)


def _metrics_summary(metrics: BacktestMetrics) -> dict:
    return {
        "accuracy": metrics.accuracy,
        "brier_score": metrics.brier_score,
        "log_loss": metrics.log_loss,
        "mean_calibration_gap": metrics.mean_calibration_gap,
    }


def compare_feature_policies_walk_forward(
    dataset: MatchDataset,
    settings: Settings,
    *,
    profile: str | None = None,
    min_train_matches: int = 10,
    test_window_size: int = 5,
    step_size: int = 5,
    l2: float | None = None,
    clip_value: float | None = None,
    output_dir: Path | None = None,
) -> dict:
    """Confronto walk-forward full vs compact — valutazione onesta."""
    common = {
        "profile": profile,
        "min_train_matches": min_train_matches,
        "test_window_size": test_window_size,
        "step_size": step_size,
        "l2": l2,
        "clip_value": clip_value,
    }
    full_report = run_walk_forward_refit(
        dataset,
        settings,
        feature_policy="full",
        **common,
    )
    compact_report = run_walk_forward_refit(
        dataset,
        settings,
        feature_policy="compact",
        **common,
    )

    full_metrics = _metrics_summary(full_report.aggregate_metrics)
    compact_metrics = _metrics_summary(compact_report.aggregate_metrics)
    full_avg_features = _avg_feature_count(full_report)
    compact_avg_features = _avg_feature_count(compact_report)

    notes: list[str] = []
    if compact_avg_features < full_avg_features * 0.75:
        notes.append(
            f"compact usa ~{compact_avg_features:.0f} feature vs ~{full_avg_features:.0f} full"
        )
    if compact_metrics["brier_score"] <= full_metrics["brier_score"]:
        notes.append("compact brier <= full su questo mock dataset")
    else:
        notes.append("compact brier > full — full potrebbe overfittare sul mock")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": dataset.league_id,
        "profile": full_report.data_profile,
        "full": {
            "feature_policy": "full",
            "windows": len(full_report.windows),
            "avg_selected_features": full_avg_features,
            "aggregate_metrics": full_metrics,
        },
        "compact": {
            "feature_policy": "compact",
            "windows": len(compact_report.windows),
            "avg_selected_features": compact_avg_features,
            "aggregate_metrics": compact_metrics,
        },
        "comparison_notes": notes,
    }

    out_dir = output_dir or BACKTESTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"walk_forward_feature_policy_comparison_{stamp}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(json_path)
    return payload
