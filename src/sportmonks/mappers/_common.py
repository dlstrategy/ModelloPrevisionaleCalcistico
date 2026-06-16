"""Utility condivise per mapper Sportmonks (funzioni pure, no I/O)."""

from __future__ import annotations

from typing import Any

# Fixture statistic type IDs — docs/sportmonks-football-v3-docs.md + doc 28.
FIXTURE_STAT_TYPE_IDS: dict[int, str] = {
    42: "SHOTS_TOTAL",
    86: "SHOTS_ON_TARGET",
    52: "GOALS",
    5304: "EXPECTED_GOALS",
    9687: "EXPECTED_GOALS_AGAINST",
    44: "DANGEROUS_ATTACKS",
}

COACH_STAT_TYPE_IDS: dict[int, str] = {
    188: "MATCHES",
    214: "WIN",
    215: "DRAW",
    216: "LOST",
    9676: "AVERAGE_POINTS_PER_GAME",
    59: "SUBSTITUTIONS",
}

PLAYER_STAT_TYPE_IDS: dict[int, str] = {
    52: "GOALS",
    79: "ASSISTS",
    118: "RATING",
    119: "MINUTES",
    5304: "EXPECTED_GOALS",
}

LINEUP_STARTER_TYPE_ID = 11
LINEUP_BENCH_TYPE_ID = 12


def unwrap_entity(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if isinstance(data, list):
        return data[0] if data else {}
    return data if isinstance(data, dict) else {}


def unwrap_entities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def parse_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("value", "total", "average", "expected", "actual", "count"):
            if key in value:
                parsed = parse_numeric(value[key])
                if parsed is not None:
                    return parsed
        return None
    return None


def stat_developer_name(entry: dict[str, Any]) -> str | None:
    type_info = entry.get("type")
    if isinstance(type_info, dict):
        name = type_info.get("developer_name") or type_info.get("code")
        if name:
            return str(name).upper().replace("-", "_")
    type_id = entry.get("type_id")
    if type_id is not None:
        return FIXTURE_STAT_TYPE_IDS.get(int(type_id))
    return None


def extract_participant_ids(fixture: dict[str, Any]) -> tuple[int | None, int | None]:
    home_id: int | None = None
    away_id: int | None = None
    for participant in fixture.get("participants") or ():
        if not isinstance(participant, dict):
            continue
        pid = participant.get("id") or participant.get("participant_id")
        if pid is None:
            continue
        meta = participant.get("meta") or {}
        location = str(meta.get("location", "")).lower()
        if location == "home":
            home_id = int(pid)
        elif location == "away":
            away_id = int(pid)
    return home_id, away_id


def extract_goals_from_scores(fixture: dict[str, Any]) -> tuple[int | None, int | None]:
    home_goals: int | None = None
    away_goals: int | None = None
    for score in fixture.get("scores") or ():
        if not isinstance(score, dict):
            continue
        if str(score.get("description", "")).upper() != "CURRENT":
            continue
        block = score.get("score") or {}
        participant = str(block.get("participant", "")).lower()
        goals = block.get("goals")
        if goals is None:
            continue
        if participant == "home":
            home_goals = int(goals)
        elif participant == "away":
            away_goals = int(goals)
    return home_goals, away_goals


def merge_nested_dicts(base: dict, extra: dict) -> dict:
    result = dict(base)
    for key, value in extra.items():
        if key.startswith("_"):
            result[key] = value
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_nested_dicts(result[key], value)
        else:
            result[key] = value
    return result
