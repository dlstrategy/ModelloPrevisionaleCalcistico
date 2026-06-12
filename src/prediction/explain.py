"""Spiegazione predizione — breakdown feature, modelli e edge."""

from __future__ import annotations

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.models import Prediction
from src.features.data_sources import build_data_sources
from src.features.feature_groups import FEATURE_GROUPS
from src.features.match_context import MatchContext
from src.models.registry import build_base_models


def _edge(home_val: float, away_val: float, *, higher_is_home: bool = True) -> float:
    diff = home_val - away_val
    return diff if higher_is_home else -diff


def _top_factors(feature_vector: dict[str, float], n: int = 8) -> dict[str, list[dict]]:
    positive: list[tuple[str, float]] = []
    negative: list[tuple[str, float]] = []
    for key, value in feature_vector.items():
        if value > 0.05:
            positive.append((key, value))
        elif value < -0.05:
            negative.append((key, value))
    positive.sort(key=lambda x: abs(x[1]), reverse=True)
    negative.sort(key=lambda x: abs(x[1]), reverse=True)
    return {
        "positive": [{"feature": k, "value": round(v, 4)} for k, v in positive[:n]],
        "negative": [{"feature": k, "value": round(v, 4)} for k, v in negative[:n]],
    }


def _model_contributions(
    context: MatchContext,
    dataset: MatchDataset,
    settings: Settings,
) -> dict[str, dict[str, float]]:
    contributions: dict[str, dict[str, float]] = {}
    for model in build_base_models(settings, dataset):
        if not model.is_ready():
            continue
        probs = model.predict(context)
        contributions[model.name] = probs.as_dict()
    return contributions


def explain_prediction(
    context: MatchContext,
    prediction: Prediction,
    *,
    dataset: MatchDataset | None = None,
    settings: Settings | None = None,
) -> dict:
    probs = prediction.probabilities
    threshold = settings.min_confidence_threshold if settings else 0.38
    low_confidence = prediction.confidence < threshold

    xg_edge = _edge(
        context.home_xg_profile.xg_diff_avg,
        context.away_xg_profile.xg_diff_avg,
    )
    strength_edge = _edge(
        context.home_advanced.season_strength,
        context.away_advanced.season_strength,
    )

    lineup_edge = 0.0
    if context.player_lineup:
        lineup_edge = _edge(
            context.player_lineup.home_starting_xi_attack_rating,
            context.player_lineup.away_starting_xi_attack_rating,
        )

    tactical_edge = context.tactical.formation_matchup_score + context.tactical.wing_advantage
    fatigue_edge = _edge(
        context.away_fatigue.fatigue_score,
        context.home_fatigue.fatigue_score,
    )

    group_counts = {
        group: sum(1 for key in keys if key in context.feature_vector)
        for group, keys in FEATURE_GROUPS.items()
    }

    data_sources = build_data_sources(context, settings, dataset) if settings else {}

    explanation = {
        "fixture_id": prediction.fixture_id,
        "match": f"{prediction.home_team} vs {prediction.away_team}",
        "model": prediction.model_name,
        "probabilities": probs.as_dict(),
        "pick": prediction.pick.value,
        "confidence": round(prediction.confidence, 4),
        "model_contributions": {},
        "edges": {
            "xg": round(xg_edge, 4),
            "team_strength": round(strength_edge, 4),
            "lineup": round(lineup_edge, 4),
            "tactical": round(tactical_edge, 4),
            "fatigue": round(fatigue_edge, 4),
        },
        "top_factors": _top_factors(context.feature_vector),
        "feature_groups_active": group_counts,
        "enabled_groups": sorted(context.enabled_feature_groups),
        "data_profile": context.data_profile,
        "data_completeness": context.data_completeness,
        "data_sources": data_sources,
        "warnings": [],
    }

    if dataset is not None and settings is not None:
        explanation["model_contributions"] = _model_contributions(context, dataset, settings)
        from src.data_capabilities.resolver import resolve_capabilities

        cap = resolve_capabilities(settings, context.match.league_id, dataset, profile=context.data_profile)
        for warning in cap.explain_warnings():
            if warning not in explanation["warnings"]:
                explanation["warnings"].append(warning)

    if low_confidence:
        explanation["warnings"].append(
            f"Confidenza bassa ({prediction.confidence:.1%}) — pick incerto"
        )
    if abs(xg_edge) < 0.05 and abs(strength_edge) < 0.05:
        explanation["warnings"].append("Squadre equilibrate su xG e strength — alta incertezza")
    if context.lineup_source == "default_fallback":
        explanation["warnings"].append(
            "Lineup/player impact usa default fallback — dati pre-match non disponibili"
        )
    if context.tactical_source == "default_fallback":
        explanation["warnings"].append(
            "Tactical matchup usa default fallback — dati pre-match non disponibili"
        )
    elif context.player_lineup and (
        context.player_lineup.home_missing_starters_count >= 2
        or context.player_lineup.away_missing_starters_count >= 2
    ):
        explanation["warnings"].append("Assenze significative in formazione")

    return explanation
