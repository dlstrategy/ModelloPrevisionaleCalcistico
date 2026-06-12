"""Modello su feature ingegnerizzate (softmax lineare, senza dipendenze ML esterne)."""

from __future__ import annotations

import math

from src.domain.models import OutcomeProbabilities
from src.features.feature_groups import ALL_GROUPS
from src.features.match_context import MatchContext
from src.models.base import BaseModel

# Pesi estesi — calibrabili con training su backtest/ablation
WEIGHTS = {
    "home": {
        "bias": 0.15,
        "home_attack": 1.2,
        "away_defense": 1.0,
        "home_form_gf": 0.7,
        "points_gap": 0.04,
        "position_gap": 0.03,
        "home_attack_rating": 0.9,
        "home_rolling_5_strength": 0.6,
        "home_xg_diff_avg": 1.1,
        "home_rolling_xg_diff_5": 0.8,
        "home_shots_on_target_for_avg": 0.4,
        "home_xg_per_shot": 0.5,
        "home_starting_xi_attack_rating": 0.7,
        "home_missing_xg_share": -0.6,
        "formation_matchup_score": 0.4,
        "wing_advantage": 0.3,
        "rest_difference": 0.05,
        "fatigue_score_away": 0.15,
        "home_end_season_motivation_score": 0.25,
        "home_points_vs_expected_last_5": 0.2,
    },
    "draw": {
        "bias": -0.1,
        "home_defense": 0.35,
        "away_defense": 0.35,
        "home_form_ga": 0.2,
        "away_form_ga": 0.2,
        "position_gap": -0.02,
        "rest_difference": -0.02,
        "pressing_mismatch": 0.15,
        "defensive_line_risk": 0.1,
        "home_mid_table_low_motivation": 0.12,
        "away_mid_table_low_motivation": 0.12,
    },
    "away": {
        "bias": -0.05,
        "away_attack": 1.2,
        "home_defense": 1.0,
        "away_form_gf": 0.7,
        "points_gap": -0.04,
        "position_gap": -0.03,
        "away_attack_rating": 0.9,
        "away_rolling_5_strength": 0.6,
        "away_xg_diff_avg": 1.1,
        "away_rolling_xg_diff_5": 0.8,
        "away_shots_on_target_for_avg": 0.4,
        "away_xg_per_shot": 0.5,
        "away_starting_xi_attack_rating": 0.7,
        "away_missing_xg_share": -0.6,
        "formation_matchup_score": -0.4,
        "wing_advantage": -0.3,
        "rest_difference": -0.05,
        "fatigue_score_home": 0.15,
        "away_end_season_motivation_score": 0.25,
        "away_points_vs_expected_last_5": 0.2,
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

    def __init__(self, enabled_groups: frozenset[str] | None = None) -> None:
        self.enabled_groups = enabled_groups or ALL_GROUPS

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        f = context.feature_vector
        logits_home = _dot(f, WEIGHTS["home"])
        logits_draw = _dot(f, WEIGHTS["draw"])
        logits_away = _dot(f, WEIGHTS["away"])
        return _softmax(logits_home, logits_draw, logits_away)
