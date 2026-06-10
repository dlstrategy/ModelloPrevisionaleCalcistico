"""Classifiche."""

from __future__ import annotations

from typing import Any

from src.sportmonks import endpoints
from src.sportmonks.client import SportmonksClient


def fetch_standings_by_season(
    client: SportmonksClient,
    season_id: int,
    *,
    includes: str = "participant",
    ttl: int,
) -> dict[str, Any]:
    return client.get(
        endpoints.standings_by_season(season_id),
        params={"include": includes},
        ttl_seconds=ttl,
    )
