"""Tracciamento origine dati per gruppi feature (explain / status)."""

from __future__ import annotations

from src.config import Settings
from src.features.match_context import MatchContext


def _companion_source_in_api_mode(source: str) -> str:
    """Etichetta esplicita quando API sync è attiva ma i companion restano mock."""
    if source == "mock_fixture":
        return "mock_fixture_not_api"
    if source == "default_fallback":
        return "default_fallback"
    return source


def build_data_sources(
    context: MatchContext,
    settings: Settings,
) -> dict[str, str]:
    """Mappa ogni gruppo feature alla sua fonte dati effettiva (non aspirazionale)."""
    api = settings.can_sync_api
    sources: dict[str, str] = {
        "base": "api_base" if api else "historical",
        "advanced_strength": "api_base" if api else "historical",
        "strength_of_schedule": "api_base" if api else "historical",
        "motivation": "api_base" if api else "historical",
        "xg": "api_not_connected_yet" if api else "mock_fixture_historical",
        "shots": "api_not_connected_yet" if api else "mock_fixture_historical",
        "calendar": "api_not_connected_yet" if api else "historical+mock_fixture",
        "player_lineup": (
            _companion_source_in_api_mode(context.lineup_source)
            if api
            else context.lineup_source
        ),
        "tactical": (
            _companion_source_in_api_mode(context.tactical_source)
            if api
            else context.tactical_source
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
