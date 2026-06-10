"""Costanti endpoint Sportmonks Football API v3.

Verificare sempre in docs/sportmonks-football-v3-docs.md prima di aggiungere endpoint.
"""

from __future__ import annotations


def league_by_id(league_id: int) -> str:
    return f"/leagues/{league_id}"


def fixtures_by_date(date_str: str) -> str:
    return f"/fixtures/date/{date_str}"


def fixtures_between(start: str, end: str) -> str:
    return f"/fixtures/between/{start}/{end}"


def fixture_by_id(fixture_id: int) -> str:
    return f"/fixtures/{fixture_id}"


def standings_by_season(season_id: int) -> str:
    return f"/standings/seasons/{season_id}"


def team_by_id(team_id: int) -> str:
    return f"/teams/{team_id}"


def seasons_by_id(season_id: int) -> str:
    return f"/seasons/{season_id}"
