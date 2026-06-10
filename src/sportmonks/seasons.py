"""Operazioni stagioni."""

from __future__ import annotations

from typing import Any

from src.sportmonks import endpoints
from src.sportmonks.client import SportmonksClient


def fetch_season(client: SportmonksClient, season_id: int, *, ttl: int) -> dict[str, Any]:
    return client.get(endpoints.seasons_by_id(season_id), ttl_seconds=ttl)
