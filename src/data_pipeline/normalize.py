"""Normalizzazione risposte Sportmonks in entità di dominio."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.domain.enums import ParticipantLocation
from src.domain.match import Match, MatchParticipant, Score


def _parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _extract_score(scores: list[dict[str, Any]] | None) -> Score | None:
    if not scores:
        return None
    home_goals: int | None = None
    away_goals: int | None = None
    for entry in scores:
        description = (entry.get("description") or "").upper()
        if description not in ("CURRENT", "FT", "FULLTIME", "2ND_HALF"):
            continue
        participant = entry.get("score", {}).get("participant")
        goals = entry.get("score", {}).get("goals")
        if goals is None:
            continue
        if participant == "home":
            home_goals = int(goals)
        elif participant == "away":
            away_goals = int(goals)
    if home_goals is not None and away_goals is not None:
        return Score(home=home_goals, away=away_goals)
    return None


def normalize_fixture(raw: dict[str, Any]) -> Match | None:
    participants_raw = raw.get("participants") or []
    if len(participants_raw) < 2:
        return None

    participants: list[MatchParticipant] = []
    for item in participants_raw:
        meta = item.get("meta") or {}
        location_raw = meta.get("location")
        if location_raw not in ("home", "away"):
            continue
        participants.append(
            MatchParticipant(
                team_id=int(item["id"]),
                team_name=str(item.get("name") or ""),
                location=ParticipantLocation(location_raw),
            )
        )

    if len(participants) < 2:
        return None

    starting_at = raw.get("starting_at")
    if not starting_at:
        return None

    return Match(
        id=int(raw["id"]),
        league_id=int(raw["league_id"]),
        season_id=int(raw["season_id"]),
        starting_at=_parse_datetime(str(starting_at)),
        participants=participants,
        round_id=int(raw["round_id"]) if raw.get("round_id") else None,
        state_id=int(raw["state_id"]) if raw.get("state_id") else None,
        score=_extract_score(raw.get("scores")),
    )


def normalize_fixtures_response(response: dict[str, Any]) -> list[Match]:
    matches: list[Match] = []
    for raw in response.get("data", []):
        match = normalize_fixture(raw)
        if match is not None:
            matches.append(match)
    return matches
