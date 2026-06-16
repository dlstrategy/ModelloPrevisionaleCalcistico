"""Mapper standings Sportmonks → strutture interne."""

from __future__ import annotations

from typing import Any

from src.sportmonks.mappers._common import parse_numeric, unwrap_entities

SOURCE_TAG = "sportmonks_sample_mapper"


def _detail_value(details: list, *type_codes: str) -> float | int | None:
    wanted = {code.upper() for code in type_codes}
    for detail in details or ():
        if not isinstance(detail, dict):
            continue
        type_info = detail.get("type") or {}
        code = str(type_info.get("developer_name") or type_info.get("code") or "").upper()
        if code not in wanted and str(detail.get("type_id")) not in wanted:
            continue
        value = detail.get("value") or {}
        parsed = parse_numeric(value.get("total")) or parse_numeric(value)
        if parsed is not None:
            return int(parsed) if parsed == int(parsed) and code in {"MATCHES", "WON", "DRAW", "LOST"} else float(parsed)
    return None


def map_standings_payload(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Mappa standings season → dict team_id → record."""
    rows: dict[int, dict[str, Any]] = {}
    for entry in unwrap_entities(payload):
        participant = entry.get("participant") or {}
        team_id = participant.get("id") or entry.get("participant_id")
        if team_id is None:
            continue
        details = entry.get("details") or []
        record = {
            "team_id": int(team_id),
            "team_name": participant.get("name") or participant.get("short_code"),
            "position": entry.get("position"),
            "points": entry.get("points"),
            "played": _detail_value(details, "OVERALL_MATCHES", "MATCHES") or entry.get("played"),
            "wins": _detail_value(details, "OVERALL_WON", "WON"),
            "draws": _detail_value(details, "OVERALL_DRAW", "DRAW"),
            "losses": _detail_value(details, "OVERALL_LOST", "LOST"),
            "goals_for": _detail_value(details, "OVERALL_GOALS_FOR", "GOALS_FOR"),
            "goals_against": _detail_value(details, "OVERALL_GOALS_AGAINST", "GOALS_AGAINST"),
            "form": entry.get("form"),
            "source": SOURCE_TAG,
        }
        if record["position"] is not None:
            record["position"] = int(record["position"])
        if record["points"] is not None:
            record["points"] = int(record["points"])
        rows[int(team_id)] = record
    return rows


def map_standings_to_companion(payload: dict[str, Any]) -> dict[str, Any]:
    """Companion standings per team_id (string keys)."""
    mapped = map_standings_payload(payload)
    return {
        "teams": {str(team_id): record for team_id, record in mapped.items()},
        "_source": SOURCE_TAG,
    }
