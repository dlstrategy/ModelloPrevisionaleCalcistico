"""Operazioni fixtures."""

from __future__ import annotations

from typing import Any

from src.sportmonks import endpoints
from src.sportmonks.client import SportmonksClient


def fetch_fixtures_by_date(
    client: SportmonksClient,
    date_str: str,
    *,
    league_id: int | None = None,
    includes: str = "participants;scores;state",
    ttl: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"include": includes}
    if league_id is not None:
        params["filters"] = f"fixtureLeagues:{league_id}"
    return client.get(endpoints.fixtures_by_date(date_str), params=params, ttl_seconds=ttl)


def fetch_fixtures_between(
    client: SportmonksClient,
    start: str,
    end: str,
    *,
    league_id: int | None = None,
    includes: str = "participants;scores;state",
    ttl: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"include": includes}
    if league_id is not None:
        params["filters"] = f"fixtureLeagues:{league_id}"
    return client.get(endpoints.fixtures_between(start, end), params=params, ttl_seconds=ttl)
