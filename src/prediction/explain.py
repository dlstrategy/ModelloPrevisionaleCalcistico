"""Spiegazione predizione — breakdown feature e modelli."""

from __future__ import annotations

from src.domain.models import Prediction
from src.features.match_context import MatchContext


def explain_prediction(context: MatchContext, prediction: Prediction) -> dict:
    return {
        "fixture_id": prediction.fixture_id,
        "model": prediction.model_name,
        "pick": prediction.pick.value,
        "confidence": prediction.confidence,
        "probabilities": prediction.probabilities.as_dict(),
        "key_features": {
            k: round(v, 4)
            for k, v in sorted(
                context.feature_vector.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )[:10]
        },
        "standings": {
            "home_position": context.home_standings.position,
            "away_position": context.away_standings.position,
            "home_points": context.home_standings.points,
            "away_points": context.away_standings.points,
        },
        "schedule": {
            "home_rest_days": context.home_schedule.days_since_last_match,
            "away_rest_days": context.away_schedule.days_since_last_match,
        },
        "lineup_available": context.lineup_impact is not None,
        "xg_available": context.home_xg is not None and context.away_xg is not None,
    }
