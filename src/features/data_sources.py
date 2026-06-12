"""Tracciamento origine dati per gruppi feature (explain / status)."""

from __future__ import annotations

from src.config import Settings
from src.domain.match import Match
from src.features.match_context import MatchContext


def build_data_sources(
    context: MatchContext,
    settings: Settings,
) -> dict[str, str]:
    """Mappa ogni gruppo feature alla sua fonte dati."""
    api = settings.can_sync_api
    sources: dict[str, str] = {
        "base": "api" if api else "historical",
        "advanced_strength": "api" if api else "historical",
        "strength_of_schedule": "api" if api else "historical",
        "motivation": "api" if api else "historical",
        "calendar": "api" if api else "historical+mock_fixture",
        "xg": "api" if api else "mock_fixture_historical",
        "shots": "api" if api else "mock_fixture_historical",
        "player_lineup": context.lineup_source,
        "tactical": context.tactical_source,
    }
    return sources


def companion_fixture_status(league_id: int) -> dict[str, bool]:
    from src.config import FIXTURES_DIR

    names = ("xg", "shots", "lineups", "tactical", "calendar")
    return {
        name: (FIXTURES_DIR / f"league_{league_id}_{name}.json").exists()
        for name in names
    }
