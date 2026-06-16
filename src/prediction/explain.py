"""Spiegazione predizione — breakdown feature, modelli e edge."""

from __future__ import annotations

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.models import Prediction
from src.features.data_sources import build_data_sources
from src.features.feature_groups import FEATURE_GROUPS
from src.features.match_context import MatchContext
from src.models.registry import build_base_models

_EDGE_HIDDEN_WARNINGS = {
    "xg": "xG edge nascosto perché il gruppo xG è disabilitato dal profilo dati corrente.",
    "lineup": (
        "Lineup edge nascosto perché il gruppo player_lineup è disabilitato "
        "dal profilo dati corrente."
    ),
    "tactical": (
        "Tactical edge nascosto perché il gruppo tactical è disabilitato "
        "dal profilo dati corrente."
    ),
    "fatigue": (
        "Fatigue edge nascosto perché il gruppo calendar è disabilitato "
        "dal profilo dati corrente."
    ),
}


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


def _group_active(context: MatchContext, group: str) -> bool:
    return group in context.enabled_feature_groups


def _build_edges(context: MatchContext) -> tuple[dict[str, float | None], dict[str, str]]:
    edges: dict[str, float | None] = {}
    edge_status: dict[str, str] = {}

    if _group_active(context, "xg"):
        edges["xg"] = round(
            _edge(context.home_xg_profile.xg_diff_avg, context.away_xg_profile.xg_diff_avg),
            4,
        )
        edge_status["xg"] = "active"
    else:
        edges["xg"] = None
        edge_status["xg"] = "disabled_by_profile"

    strength_active = _group_active(context, "base") or _group_active(context, "advanced_strength")
    if strength_active:
        edges["team_strength"] = round(
            _edge(context.home_advanced.season_strength, context.away_advanced.season_strength),
            4,
        )
        edge_status["team_strength"] = "active"
    else:
        edges["team_strength"] = None
        edge_status["team_strength"] = "disabled_by_profile"

    if _group_active(context, "player_lineup") and context.player_lineup:
        edges["lineup"] = round(
            _edge(
                context.player_lineup.home_starting_xi_attack_rating,
                context.player_lineup.away_starting_xi_attack_rating,
            ),
            4,
        )
        edge_status["lineup"] = "active"
    elif _group_active(context, "player_lineup"):
        edges["lineup"] = 0.0
        edge_status["lineup"] = "active"
    else:
        edges["lineup"] = None
        edge_status["lineup"] = "disabled_by_profile"

    if _group_active(context, "tactical"):
        edges["tactical"] = round(
            context.tactical.formation_matchup_score + context.tactical.wing_advantage,
            4,
        )
        edge_status["tactical"] = "active"
    else:
        edges["tactical"] = None
        edge_status["tactical"] = "disabled_by_profile"

    if _group_active(context, "calendar"):
        edges["fatigue"] = round(
            _edge(
                context.away_fatigue.fatigue_score,
                context.home_fatigue.fatigue_score,
            ),
            4,
        )
        edge_status["fatigue"] = "active"
    else:
        edges["fatigue"] = None
        edge_status["fatigue"] = "disabled_by_profile"

    return edges, edge_status


def _append_edge_hidden_warnings(
    warnings: list[str],
    edge_status: dict[str, str],
) -> None:
    capability_xg = any("xG non disponibile" in w for w in warnings)
    for edge_key, status in edge_status.items():
        if status != "disabled_by_profile":
            continue
        message = _EDGE_HIDDEN_WARNINGS.get(edge_key)
        if not message or message in warnings:
            continue
        if edge_key == "xg" and capability_xg:
            continue
        if edge_key == "lineup" and any("lineup" in w.lower() or "Expected lineups" in w for w in warnings):
            continue
        if edge_key == "tactical" and any("Tactical data" in w or "Tactical matchup" in w for w in warnings):
            continue
        warnings.append(message)


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

    edges, edge_status = _build_edges(context)

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
        "edges": edges,
        "edge_status": edge_status,
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

        cap = resolve_capabilities(
            settings, context.match.league_id, dataset, profile=context.data_profile
        )
        for warning in cap.explain_warnings():
            if warning not in explanation["warnings"]:
                explanation["warnings"].append(warning)

    _append_edge_hidden_warnings(explanation["warnings"], edge_status)

    if low_confidence:
        explanation["warnings"].append(
            f"Confidenza bassa ({prediction.confidence:.1%}) — pick incerto"
        )
    xg_val = edges.get("xg")
    strength_val = edges.get("team_strength")
    if (
        xg_val is not None
        and strength_val is not None
        and abs(xg_val) < 0.05
        and abs(strength_val) < 0.05
    ):
        explanation["warnings"].append("Squadre equilibrate su xG e strength — alta incertezza")
    if _group_active(context, "player_lineup"):
        from src.features.transfer_lineup_features import build_transfer_lineup_summary

        explanation["transfer_lineup_summary"] = build_transfer_lineup_summary(context.match)

    if _group_active(context, "player_lineup") and context.lineup_source == "default_fallback":
        explanation["warnings"].append(
            "Lineup/player impact usa default fallback — dati pre-match non disponibili"
        )
    if _group_active(context, "tactical") and context.tactical_source == "default_fallback":
        explanation["warnings"].append(
            "Tactical matchup usa default fallback — dati pre-match non disponibili"
        )
    elif _group_active(context, "player_lineup") and context.player_lineup and (
        context.player_lineup.home_missing_starters_count >= 2
        or context.player_lineup.away_missing_starters_count >= 2
    ):
        explanation["warnings"].append("Assenze significative in formazione")

    if _group_active(context, "coach"):
        from src.features.coach_features import (
            build_coach_summary,
            coach_side_style_fit_insufficient,
        )

        explanation["coach_summary"] = build_coach_summary(context.match, tactical=context.tactical)
        coach_src = data_sources.get("coach", "missing")
        explanation["coach_summary"]["source"] = coach_src

        home_c = explanation["coach_summary"]["home"]
        away_c = explanation["coach_summary"]["away"]
        style_fit_warning = (
            "Coach style fit insufficient data — compatibilità stile/rosa non certa"
        )
        if home_c.get("unknown_coach") or away_c.get("unknown_coach"):
            explanation["warnings"].append(
                "Coach data fallback — allenatore sconosciuto per una squadra"
            )
        if home_c.get("recent_change") or away_c.get("recent_change"):
            explanation["warnings"].append(
                "Recent coach change — possibile instabilità/new manager bounce"
            )
        if (
            home_c.get("integration_progress", 1.0) < 0.5
            or away_c.get("integration_progress", 1.0) < 0.5
        ):
            explanation["warnings"].append(
                "Coach adaptation risk — allenatore in fase di inserimento"
            )
        if home_c.get("cross_country") or away_c.get("cross_country"):
            explanation["warnings"].append(
                "Cross-country coach adaptation — trasferimento tecnico tra paesi/campionati"
            )
        if (
            home_c.get("data_confidence", 1.0) < 0.35
            or away_c.get("data_confidence", 1.0) < 0.35
        ):
            explanation["warnings"].append(
                "Coach impact low confidence — pochi match o dati mock"
            )
        if coach_side_style_fit_insufficient(home_c) or coach_side_style_fit_insufficient(away_c):
            if style_fit_warning not in explanation["warnings"]:
                explanation["warnings"].append(style_fit_warning)

    return explanation
