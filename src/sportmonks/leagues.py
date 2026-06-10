"""Operazioni leghe."""

from __future__ import annotations

import logging
from typing import Any

from src.sportmonks import endpoints
from src.sportmonks.client import SportmonksClient

logger = logging.getLogger(__name__)


def fetch_league(client: SportmonksClient, league_id: int, *, ttl: int) -> dict[str, Any]:
    return client.get(
        endpoints.league_by_id(league_id),
        params={"include": "currentSeason"},
        ttl_seconds=ttl,
    )
