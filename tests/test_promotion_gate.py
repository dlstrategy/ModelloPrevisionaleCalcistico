"""Test promotion gate logic."""

import json

import pytest

from src.backtesting.metrics import BacktestMetrics
from src.backtesting.promotion_gate import (
    INCONCLUSIVE,
    PROMOTED,
    REJECTED,
    PromotionThresholds,
    compare_metrics,
    decision_as_dict,
    decision_to_json,
    evaluate_promotion,
    summarize_metrics,
)
from src.backtesting.walk_forward import WalkForwardReport


def _metrics(
    *,
    samples: int = 30,
    accuracy: float = 0.35,
    brier: float = 0.65,
    log_loss: float = 1.1,
    cal_gap: float = 0.15,
    overconf: float = 0.4,
) -> BacktestMetrics:
    return BacktestMetrics(
        samples=samples,
        accuracy=accuracy,
        brier_score=brier,
        log_loss=log_loss,
        brier_skill_score=0.0,
        pick_overconfidence_rate=overconf,
        pick_underconfidence_rate=0.1,
        mean_calibration_gap=cal_gap,
    )


def _report(
    metrics: BacktestMetrics,
    *,
    windows: int = 5,
    tested: int | None = None,
) -> WalkForwardReport:
    return WalkForwardReport(
        model_name="feature_trained",
        league_id=384,
        generated_at="2025-01-01T00:00:00+00:00",
        min_train_matches=10,
        test_window_size=5,
        step_size=5,
        training_mode="walk_forward_refit",
        total_tested_matches=tested if tested is not None else metrics.samples,
        windows=tuple(
            [object()] * windows  # type: ignore[list-item]
        ),
        aggregate_metrics=metrics,
        data_profile="advanced",
    )


@pytest.fixture
def thresholds_test() -> PromotionThresholds:
    return PromotionThresholds(
        min_tested_matches=20,
        min_windows=3,
        max_brier_delta=0.0,
        max_logloss_delta=0.0,
        max_calibration_gap_delta=0.02,
        max_pick_overconfidence_rate=0.65,
    )


def test_inconclusive_if_few_matches(thresholds_test):
    baseline = _report(_metrics(samples=30), windows=5)
    candidate = _report(_metrics(samples=15, brier=0.60), windows=5, tested=15)
    decision = evaluate_promotion(candidate, baseline, thresholds_test)
    assert decision.status == INCONCLUSIVE
    assert any("dataset_small" in w for w in decision.warnings)


def test_inconclusive_if_few_windows(thresholds_test):
    baseline = _report(_metrics(samples=30), windows=5)
    candidate = _report(_metrics(samples=30, brier=0.60), windows=2)
    low_windows = PromotionThresholds(
        min_tested_matches=20,
        min_windows=3,
    )
    decision = evaluate_promotion(candidate, baseline, low_windows)
    assert decision.status == INCONCLUSIVE


def test_promoted_if_better_metrics(thresholds_test):
    baseline = _report(_metrics(brier=0.70, log_loss=1.20, cal_gap=0.20))
    candidate = _report(_metrics(brier=0.65, log_loss=1.10, cal_gap=0.15))
    decision = evaluate_promotion(
        candidate,
        baseline,
        thresholds_test,
        candidate_avg_features=90,
        baseline_avg_features=160,
    )
    assert decision.status == PROMOTED


def test_rejected_if_clearly_worse_brier(thresholds_test):
    baseline = _report(_metrics(brier=0.60, log_loss=1.0))
    candidate = _report(_metrics(brier=0.75, log_loss=1.0))
    decision = evaluate_promotion(candidate, baseline, thresholds_test)
    assert decision.status == REJECTED


def test_rejected_if_accuracy_better_but_brier_worse(thresholds_test):
    baseline = _report(_metrics(accuracy=0.30, brier=0.60, log_loss=1.0))
    candidate = _report(_metrics(accuracy=0.45, brier=0.62, log_loss=1.0))
    decision = evaluate_promotion(candidate, baseline, thresholds_test)
    assert decision.status == REJECTED
    assert any("Accuracy" in r for r in decision.reasons)


def test_overconfidence_warning(thresholds_test):
    baseline = _report(_metrics(brier=0.65))
    candidate = _report(_metrics(brier=0.64, overconf=0.70))
    decision = evaluate_promotion(candidate, baseline, thresholds_test)
    assert any("overconfidence" in w for w in decision.warnings)


def test_decision_as_dict_json_serializable(thresholds_test):
    baseline = _report(_metrics())
    candidate = _report(_metrics(brier=0.64))
    decision = evaluate_promotion(candidate, baseline, thresholds_test)
    payload = decision_as_dict(decision)
    json.dumps(payload)
    json.loads(decision_to_json(decision))


def test_compare_metrics_sign():
    base = summarize_metrics(_metrics(brier=0.7))
    cand = summarize_metrics(_metrics(brier=0.65))
    deltas = compare_metrics(cand, base)
    assert deltas["brier_score"] < 0
