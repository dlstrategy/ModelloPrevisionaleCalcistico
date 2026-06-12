"""Promotion gate — giudizio tecnico candidato vs baseline (walk-forward)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.backtesting.metrics import BacktestMetrics
from src.backtesting.walk_forward import WalkForwardReport

PROMOTED = "promoted"
REJECTED = "rejected"
INCONCLUSIVE = "inconclusive"

# Regressioni chiare oltre la tolleranza configurata.
CLEAR_BRIER_REGRESSION = 0.03
CLEAR_LOGLOSS_REGRESSION = 0.05
HIGH_OVERCONFIDENCE_REJECT = 0.75


@dataclass(frozen=True)
class PromotionThresholds:
    min_tested_matches: int = 50
    min_windows: int = 3
    max_brier_delta: float = 0.0
    max_logloss_delta: float = 0.0
    min_accuracy_delta: float = 0.0
    max_calibration_gap_delta: float = 0.02
    max_pick_overconfidence_rate: float = 0.65
    min_feature_reduction_ratio: float | None = None


@dataclass(frozen=True)
class PromotionDecision:
    candidate_name: str
    baseline_name: str
    status: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    metric_deltas: dict[str, float]
    baseline_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    tested_matches: int
    windows: int


def summarize_metrics(metrics: BacktestMetrics) -> dict[str, float]:
    return {
        "samples": float(metrics.samples),
        "accuracy": metrics.accuracy,
        "brier_score": metrics.brier_score,
        "log_loss": metrics.log_loss,
        "brier_skill_score": metrics.brier_skill_score,
        "mean_calibration_gap": metrics.mean_calibration_gap,
        "pick_overconfidence_rate": metrics.pick_overconfidence_rate,
        "pick_underconfidence_rate": metrics.pick_underconfidence_rate,
    }


def compare_metrics(
    candidate_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
) -> dict[str, float]:
    """Delta = candidate - baseline (negativo su Brier/log-loss/gap = candidato migliore)."""
    keys = (
        "accuracy",
        "brier_score",
        "log_loss",
        "brier_skill_score",
        "mean_calibration_gap",
        "pick_overconfidence_rate",
        "pick_underconfidence_rate",
    )
    return {
        key: float(candidate_metrics.get(key, 0.0)) - float(baseline_metrics.get(key, 0.0))
        for key in keys
    }


def _decision(
    *,
    candidate_name: str,
    baseline_name: str,
    status: str,
    reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    metric_deltas: dict[str, float],
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    tested_matches: int,
    windows: int,
) -> PromotionDecision:
    return PromotionDecision(
        candidate_name=candidate_name,
        baseline_name=baseline_name,
        status=status,
        reasons=tuple(dict.fromkeys(reasons)),
        warnings=tuple(dict.fromkeys(warnings)),
        metric_deltas=metric_deltas,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        tested_matches=tested_matches,
        windows=windows,
    )


def evaluate_promotion(
    candidate_report: WalkForwardReport,
    baseline_report: WalkForwardReport,
    thresholds: PromotionThresholds,
    *,
    candidate_name: str | None = None,
    baseline_name: str | None = None,
    candidate_avg_features: float | None = None,
    baseline_avg_features: float | None = None,
) -> PromotionDecision:
    """Valuta candidato vs baseline usando metriche aggregate walk-forward."""
    cand_label = candidate_name or f"{candidate_report.model_name}/{getattr(candidate_report, 'feature_policy', 'default')}"
    base_label = baseline_name or f"{baseline_report.model_name}/baseline"

    baseline_m = summarize_metrics(baseline_report.aggregate_metrics)
    candidate_m = summarize_metrics(candidate_report.aggregate_metrics)
    deltas = compare_metrics(candidate_m, baseline_m)

    tested = candidate_report.total_tested_matches
    windows = len(candidate_report.windows)
    reasons: list[str] = []
    warnings: list[str] = []

    if tested < thresholds.min_tested_matches:
        warnings.append("dataset_small_for_promotion")
        reasons.append(
            f"Match testati insufficienti per promozione ({tested} < {thresholds.min_tested_matches})"
        )
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=INCONCLUSIVE,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if windows < thresholds.min_windows:
        warnings.append("insufficient_walk_forward_windows")
        reasons.append(f"Finestre walk-forward insufficienti ({windows} < {thresholds.min_windows})")
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=INCONCLUSIVE,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if candidate_m["pick_overconfidence_rate"] > HIGH_OVERCONFIDENCE_REJECT:
        reasons.append(
            f"Overconfidence eccessiva ({candidate_m['pick_overconfidence_rate']:.3f} > {HIGH_OVERCONFIDENCE_REJECT})"
        )
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=REJECTED,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if candidate_m["pick_overconfidence_rate"] > thresholds.max_pick_overconfidence_rate:
        warnings.append(
            f"pick_overconfidence_rate={candidate_m['pick_overconfidence_rate']:.3f}"
        )

    brier_worse = deltas["brier_score"] > thresholds.max_brier_delta
    logloss_worse = deltas["log_loss"] > thresholds.max_logloss_delta
    calib_worse = deltas["mean_calibration_gap"] > thresholds.max_calibration_gap_delta
    accuracy_better_brier_worse = deltas["accuracy"] > thresholds.min_accuracy_delta and brier_worse

    if deltas["brier_score"] > thresholds.max_brier_delta + CLEAR_BRIER_REGRESSION:
        reasons.append(
            f"Brier score peggiora chiaramente (delta={deltas['brier_score']:+.4f})"
        )
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=REJECTED,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if deltas["log_loss"] > thresholds.max_logloss_delta + CLEAR_LOGLOSS_REGRESSION:
        reasons.append(
            f"Log-loss peggiora chiaramente (delta={deltas['log_loss']:+.4f})"
        )
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=REJECTED,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if accuracy_better_brier_worse:
        reasons.append("Accuracy migliore ma Brier peggiore — accuracy da sola non basta")
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=REJECTED,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if calib_worse:
        reasons.append(
            f"Calibration gap peggiora oltre soglia (delta={deltas['mean_calibration_gap']:+.4f})"
        )
        if deltas["mean_calibration_gap"] > thresholds.max_calibration_gap_delta + 0.03:
            return _decision(
                candidate_name=cand_label,
                baseline_name=base_label,
                status=REJECTED,
                reasons=tuple(reasons),
                warnings=tuple(warnings),
                metric_deltas=deltas,
                baseline_metrics=baseline_m,
                candidate_metrics=candidate_m,
                tested_matches=tested,
                windows=windows,
            )
        warnings.append("calibration_gap_slightly_worse")

    feature_reduction_note = False
    if (
        candidate_avg_features is not None
        and baseline_avg_features is not None
        and baseline_avg_features > 0
    ):
        reduction = 1.0 - (candidate_avg_features / baseline_avg_features)
        if thresholds.min_feature_reduction_ratio is not None:
            if reduction >= thresholds.min_feature_reduction_ratio:
                feature_reduction_note = True
                warnings.append(f"feature_reduction={reduction:.1%}")

    promotion_ok = (
        not brier_worse
        and not logloss_worse
        and not calib_worse
    )

    if promotion_ok and not warnings:
        reasons.append("Candidato non peggiore su Brier, log-loss e calibration gap")
        if feature_reduction_note:
            reasons.append("Riduzione feature significativa con metriche equivalenti")
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=PROMOTED,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if promotion_ok and warnings:
        reasons.append("Metriche accettabili ma con warning — dataset mock non conclusivo")
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=INCONCLUSIVE,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    if brier_worse or logloss_worse:
        reasons.append("Metriche miste o peggioramento moderato — non promuovere")
        return _decision(
            candidate_name=cand_label,
            baseline_name=base_label,
            status=INCONCLUSIVE,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            metric_deltas=deltas,
            baseline_metrics=baseline_m,
            candidate_metrics=candidate_m,
            tested_matches=tested,
            windows=windows,
        )

    reasons.append("Differenze minime su dataset limitato — valutazione non conclusiva")
    return _decision(
        candidate_name=cand_label,
        baseline_name=base_label,
        status=INCONCLUSIVE,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        metric_deltas=deltas,
        baseline_metrics=baseline_m,
        candidate_metrics=candidate_m,
        tested_matches=tested,
        windows=windows,
    )


def decision_as_dict(decision: PromotionDecision) -> dict[str, Any]:
    return {
        "candidate_name": decision.candidate_name,
        "baseline_name": decision.baseline_name,
        "status": decision.status,
        "reasons": list(decision.reasons),
        "warnings": list(decision.warnings),
        "metric_deltas": decision.metric_deltas,
        "baseline_metrics": decision.baseline_metrics,
        "candidate_metrics": decision.candidate_metrics,
        "tested_matches": decision.tested_matches,
        "windows": decision.windows,
    }


def decision_to_json(decision: PromotionDecision) -> str:
    return json.dumps(decision_as_dict(decision), indent=2)
