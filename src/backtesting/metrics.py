"""Metriche backtesting, calibrazione e skill score."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from src.domain.enums import MatchOutcome
from src.domain.models import OutcomeProbabilities, Prediction


@dataclass(frozen=True)
class BacktestMetrics:
    samples: int
    accuracy: float
    brier_score: float
    log_loss: float
    brier_skill_score: float
    overconfidence_rate: float
    underconfidence_rate: float
    calibration_bins: list[dict[str, float]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "samples": self.samples,
            "accuracy": self.accuracy,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "brier_skill_score": self.brier_skill_score,
            "overconfidence_rate": self.overconfidence_rate,
            "underconfidence_rate": self.underconfidence_rate,
            "calibration_bins": self.calibration_bins,
        }


def _one_hot(outcome: MatchOutcome) -> tuple[float, float, float]:
    return (
        1.0 if outcome == MatchOutcome.HOME else 0.0,
        1.0 if outcome == MatchOutcome.DRAW else 0.0,
        1.0 if outcome == MatchOutcome.AWAY else 0.0,
    )


def _brier_for_pair(probs: OutcomeProbabilities, actual: MatchOutcome) -> float:
    y1, yx, y2 = _one_hot(actual)
    return (probs.home - y1) ** 2 + (probs.draw - yx) ** 2 + (probs.away - y2) ** 2


def compute_baseline_brier(actuals: list[MatchOutcome]) -> float:
    if not actuals:
        return 0.0
    counts = {MatchOutcome.HOME: 0, MatchOutcome.DRAW: 0, MatchOutcome.AWAY: 0}
    for outcome in actuals:
        counts[outcome] += 1
    n = len(actuals)
    baseline_probs = OutcomeProbabilities.normalize(
        counts[MatchOutcome.HOME] / n,
        counts[MatchOutcome.DRAW] / n,
        counts[MatchOutcome.AWAY] / n,
    )
    return sum(_brier_for_pair(baseline_probs, a) for a in actuals) / n


def compute_calibration_bins(
    predictions: list[Prediction],
    actuals: list[MatchOutcome],
    n_bins: int = 5,
) -> list[dict[str, float]]:
    if not predictions:
        return []

    pairs = [(p.confidence, 1.0 if p.pick == a else 0.0) for p, a in zip(predictions, actuals)]
    pairs.sort(key=lambda x: x[0])
    size = max(len(pairs) // n_bins, 1)
    bins: list[dict[str, float]] = []

    for i in range(0, len(pairs), size):
        chunk = pairs[i : i + size]
        if not chunk:
            continue
        avg_conf = sum(c for c, _ in chunk) / len(chunk)
        hit_rate = sum(h for _, h in chunk) / len(chunk)
        bins.append(
            {
                "avg_confidence": round(avg_conf, 4),
                "hit_rate": round(hit_rate, 4),
                "count": float(len(chunk)),
                "gap": round(abs(avg_conf - hit_rate), 4),
            }
        )
    return bins


def compute_confidence_rates(
    predictions: list[Prediction],
    actuals: list[MatchOutcome],
) -> tuple[float, float]:
    if not predictions:
        return 0.0, 0.0
    over = under = 0
    for pred, actual in zip(predictions, actuals):
        hit = 1.0 if pred.pick == actual else 0.0
        if pred.confidence > hit + 0.05:
            over += 1
        elif pred.confidence < hit - 0.05:
            under += 1
    n = len(predictions)
    return over / n, under / n


def compute_metrics(predictions: list[Prediction], actuals: list[MatchOutcome]) -> BacktestMetrics:
    if not predictions:
        return BacktestMetrics(
            samples=0,
            accuracy=0.0,
            brier_score=0.0,
            log_loss=0.0,
            brier_skill_score=0.0,
            overconfidence_rate=0.0,
            underconfidence_rate=0.0,
        )

    correct = 0
    brier = 0.0
    log_loss = 0.0
    eps = 1e-15

    for pred, actual in zip(predictions, actuals):
        if pred.pick == actual:
            correct += 1
        brier += _brier_for_pair(pred.probabilities, actual)
        actual_prob = {
            MatchOutcome.HOME: pred.probabilities.home,
            MatchOutcome.DRAW: pred.probabilities.draw,
            MatchOutcome.AWAY: pred.probabilities.away,
        }[actual]
        log_loss -= math.log(max(actual_prob, eps))

    n = len(predictions)
    brier_score = brier / n
    baseline_brier = compute_baseline_brier(actuals)
    if baseline_brier > 0:
        brier_skill = 1.0 - (brier_score / baseline_brier)
    else:
        brier_skill = 0.0

    over, under = compute_confidence_rates(predictions, actuals)

    return BacktestMetrics(
        samples=n,
        accuracy=correct / n,
        brier_score=brier_score,
        log_loss=log_loss / n,
        brier_skill_score=brier_skill,
        overconfidence_rate=over,
        underconfidence_rate=under,
        calibration_bins=compute_calibration_bins(predictions, actuals),
    )
