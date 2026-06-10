"""Metriche backtesting e calibrazione."""

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
    calibration_bins: list[dict[str, float]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "samples": self.samples,
            "accuracy": self.accuracy,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "calibration_bins": self.calibration_bins,
        }


def _one_hot(outcome: MatchOutcome) -> tuple[float, float, float]:
    return (
        1.0 if outcome == MatchOutcome.HOME else 0.0,
        1.0 if outcome == MatchOutcome.DRAW else 0.0,
        1.0 if outcome == MatchOutcome.AWAY else 0.0,
    )


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


def compute_metrics(predictions: list[Prediction], actuals: list[MatchOutcome]) -> BacktestMetrics:
    if not predictions:
        return BacktestMetrics(samples=0, accuracy=0.0, brier_score=0.0, log_loss=0.0)

    correct = 0
    brier = 0.0
    log_loss = 0.0
    eps = 1e-15

    for pred, actual in zip(predictions, actuals):
        if pred.pick == actual:
            correct += 1
        y1, yx, y2 = _one_hot(actual)
        p = pred.probabilities
        brier += (p.home - y1) ** 2 + (p.draw - yx) ** 2 + (p.away - y2) ** 2
        actual_prob = {
            MatchOutcome.HOME: p.home,
            MatchOutcome.DRAW: p.draw,
            MatchOutcome.AWAY: p.away,
        }[actual]
        log_loss -= math.log(max(actual_prob, eps))

    n = len(predictions)
    return BacktestMetrics(
        samples=n,
        accuracy=correct / n,
        brier_score=brier / n,
        log_loss=log_loss / n,
        calibration_bins=compute_calibration_bins(predictions, actuals),
    )
