"""Modello su feature ingegnerizzate (softmax lineare, senza dipendenze ML esterne)."""

from __future__ import annotations

import math

from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext
from src.models.base import BaseModel

# Pesi iniziali — calibrabili in futuro con training su backtest
WEIGHTS = {
    "home": {
        "home_attack": 1.4,
        "away_defense": 1.1,
        "home_form_gf": 0.8,
        "points_gap": 0.04,
        "position_gap": 0.03,
        "home_xg_for": 0.9,
        "home_lineup_attack": 0.6,
        "tactical_edge": 0.5,
        "home_rest_days": -0.02,
        "home_congestion": -0.05,
        "bias": 0.15,
    },
    "draw": {
        "home_defense": 0.4,
        "away_defense": 0.4,
        "home_form_ga": 0.2,
        "away_form_ga": 0.2,
        "position_gap": -0.02,
        "home_rest_days": 0.01,
        "away_rest_days": 0.01,
        "bias": -0.1,
    },
    "away": {
        "away_attack": 1.4,
        "home_defense": 1.1,
        "away_form_gf": 0.8,
        "points_gap": -0.04,
        "position_gap": -0.03,
        "away_xg_for": 0.9,
        "away_lineup_attack": 0.6,
        "tactical_edge": -0.5,
        "away_rest_days": -0.02,
        "away_congestion": -0.05,
        "bias": -0.05,
    },
}


def _dot(features: dict[str, float], weights: dict[str, float]) -> float:
    total = weights.get("bias", 0.0)
    for key, weight in weights.items():
        if key == "bias":
            continue
        total += weight * features.get(key, 0.0)
    return total


def _softmax(a: float, b: float, c: float) -> OutcomeProbabilities:
    m = max(a, b, c)
    ea, eb, ec = math.exp(a - m), math.exp(b - m), math.exp(c - m)
    return OutcomeProbabilities.normalize(ea, eb, ec)


class FeatureModel(BaseModel):
    name = "feature"

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        f = context.feature_vector
        logits_home = _dot(f, WEIGHTS["home"])
        logits_draw = _dot(f, WEIGHTS["draw"])
        logits_away = _dot(f, WEIGHTS["away"])
        return _softmax(logits_home, logits_draw, logits_away)
