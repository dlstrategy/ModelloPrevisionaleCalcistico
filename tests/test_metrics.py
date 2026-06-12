from src.backtesting.metrics import (
    compute_calibration_bins,
    compute_mean_calibration_gap,
    compute_metrics,
)
from src.domain.enums import MatchOutcome
from src.domain.models import OutcomeProbabilities, Prediction


def _pred(home: float, draw: float, away: float) -> Prediction:
    probs = OutcomeProbabilities.normalize(home, draw, away)
    return Prediction(
        fixture_id=1,
        home_team="Home",
        away_team="Away",
        probabilities=probs,
        model_name="test",
    )


def test_mean_calibration_gap_from_bins():
    predictions = [
        _pred(0.7, 0.2, 0.1),
        _pred(0.6, 0.25, 0.15),
        _pred(0.35, 0.3, 0.35),
        _pred(0.3, 0.3, 0.4),
    ]
    actuals = [
        MatchOutcome.HOME,
        MatchOutcome.AWAY,
        MatchOutcome.AWAY,
        MatchOutcome.DRAW,
    ]
    bins = compute_calibration_bins(predictions, actuals, n_bins=2)
    gap = compute_mean_calibration_gap(bins)
    assert gap >= 0.0
    assert all("gap" in b for b in bins)


def test_metrics_includes_pick_confidence_and_calibration_gap():
    predictions = [_pred(0.5, 0.25, 0.25)] * 4
    actuals = [MatchOutcome.HOME, MatchOutcome.DRAW, MatchOutcome.AWAY, MatchOutcome.HOME]
    metrics = compute_metrics(predictions, actuals)
    assert metrics.pick_overconfidence_rate >= 0.0
    assert metrics.pick_underconfidence_rate >= 0.0
    assert metrics.mean_calibration_gap >= 0.0
    assert metrics.overconfidence_rate == metrics.pick_overconfidence_rate
