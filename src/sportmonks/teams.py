"""Operazioni squadre — predisposto per statistiche avanzate."""

from __future__ import annotations

from typing import Any

from src.sportmonks import endpoints
from src.sportmonks.client import SportmonksClient


def fetch_team(
    client: SportmonksClient,
    team_id: int,
    *,
    includes: str | None = None,
    ttl: int,
) -> dict[str, Any]:
    params = {"include": includes} if includes else None
    return client.get(endpoints.team_by_id(team_id), params=params, ttl_seconds=ttl)
