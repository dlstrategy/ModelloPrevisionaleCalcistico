"""Tracciamento origine dati per gruppi feature (explain / status)."""

from __future__ import annotations

from src.config import Settings
from src.data_capabilities.resolver import resolve_capabilities
from src.features.match_context import MatchContext


def _coach_source(context: MatchContext, resolution) -> str:
    if "coach" in resolution.disabled_feature_groups:
        return "disabled"
    from src.coaches.coach_registry import COACH_PROFILES_PATH, get_team_coach_profile

    if not COACH_PROFILES_PATH.exists():
        return "missing"
    home = get_team_coach_profile(context.match.home.team_id, context.match.league_id)
    away = get_team_coach_profile(context.match.away.team_id, context.match.league_id)
    if home.source == "unknown_coach_fallback" or away.source == "unknown_coach_fallback":
        return "fallback"
    return "mock_coach_profiles"


def build_data_sources(
    context: MatchContext,
    settings: Settings,
    dataset=None,
) -> dict[str, str]:
    """Mappa ogni gruppo feature alla sua fonte dati effettiva (non aspirazionale)."""
    api = settings.can_sync_api
    resolution = resolve_capabilities(
        settings,
        context.match.league_id,
        dataset,
        profile=context.data_profile,
    )
    disabled = resolution.disabled_feature_groups

    def historical_source() -> str:
        return "api_base" if api else "historical"

    def companion_source(group: str, context_source: str) -> str:
        if group in disabled:
            req_fb = next(
                (fb for fb in resolution.fallbacks if fb.startswith(f"{group}_")),
                f"{group}_disabled",
            )
            return req_fb.replace(f"{group}_", "disabled_or_") if "disabled" in req_fb else req_fb
        if api and context_source == "mock_fixture":
            return "mock_fixture_not_api"
        if api and context_source == "default_fallback":
            return "default_fallback"
        if group == "xg" or group == "shots":
            return "api_not_connected_yet" if api else "mock_fixture_historical"
        return context_source

    sources: dict[str, str] = {
        "base": historical_source(),
        "advanced_strength": historical_source(),
        "strength_of_schedule": historical_source(),
        "motivation": historical_source(),
        "calendar": (
            "api_not_connected_yet"
            if api and "calendar" in disabled
            else ("historical+mock_fixture" if not api else "api_not_connected_yet")
        ),
        "xg": companion_source("xg", "mock_fixture_historical"),
        "shots": companion_source("shots", "mock_fixture_historical"),
        "player_lineup": companion_source("player_lineup", context.lineup_source),
        "tactical": companion_source("tactical", context.tactical_source),
        "coach": _coach_source(context, resolution),
        "player_transfer": (
            "disabled"
            if "player_lineup" in disabled
            else "mock_player_career_registry"
        ),
    }
    return sources


def companion_fixture_status(league_id: int) -> dict[str, bool]:
    from src.config import FIXTURES_DIR

    names = ("xg", "shots", "lineups", "tactical", "calendar")
    return {
        name: (FIXTURES_DIR / f"league_{league_id}_{name}.json").exists()
        for name in names
    }
