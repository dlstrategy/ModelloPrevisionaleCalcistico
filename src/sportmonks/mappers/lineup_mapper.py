"""Mapper lineups Sportmonks → companion player_lineup/tactical."""

from __future__ import annotations

from typing import Any

from src.sportmonks.mappers._common import (
    LINEUP_BENCH_TYPE_ID,
    LINEUP_STARTER_TYPE_ID,
    extract_participant_ids,
    unwrap_entity,
)

SOURCE_TAG = "sportmonks_sample_mapper"


def _formation_for_team(fixture: dict[str, Any], team_id: int | None, location: str) -> str | None:
    for formation in fixture.get("formations") or ():
        if not isinstance(formation, dict):
            continue
        if team_id is not None and formation.get("participant_id") == team_id:
            return formation.get("formation") or formation.get("name")
        if str(formation.get("location", "")).lower() == location:
            return formation.get("formation") or formation.get("name")
    metadata = fixture.get("metadata") or {}
    key = f"{location}_formation"
    if key in metadata:
        return str(metadata[key])
    return None


def _lineup_confirmed(fixture: dict[str, Any]) -> bool:
    for flag in ("lineups_confirmed", "confirmed", "is_confirmed"):
        if flag in fixture:
            return bool(fixture[flag])
    meta = fixture.get("metadata") or {}
    if "lineups_confirmed" in meta:
        return bool(meta["lineups_confirmed"])
    lineups = fixture.get("lineups") or []
    return bool(lineups)


def extract_fixture_lineups(raw_fixture: dict[str, Any]) -> dict[str, Any]:
    fixture = unwrap_entity(raw_fixture)
    home_id, away_id = extract_participant_ids(fixture)
    confirmed = _lineup_confirmed(fixture)
    availability = "confirmed_lineup" if confirmed else "expected_lineup"

    def side_lineups(team_id: int | None, location: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in fixture.get("lineups") or ():
            if not isinstance(row, dict):
                continue
            row_team = row.get("team_id")
            if team_id is not None and row_team == team_id:
                rows.append(row)
        return rows

    return {
        "fixture_id": fixture.get("id"),
        "home_team_id": home_id,
        "away_team_id": away_id,
        "data_availability": availability,
        "home_lineups": side_lineups(home_id, "home"),
        "away_lineups": side_lineups(away_id, "away"),
        "home_formation": _formation_for_team(fixture, home_id, "home"),
        "away_formation": _formation_for_team(fixture, away_id, "away"),
        "source": SOURCE_TAG,
    }


def extract_starting_xi_player_ids(raw_fixture: dict[str, Any]) -> dict[str, list[int]]:
    extracted = extract_fixture_lineups(raw_fixture)

    def starters(rows: list[dict[str, Any]]) -> list[int]:
        ids: list[int] = []
        for row in rows:
            type_id = row.get("type_id")
            if type_id is not None and int(type_id) == LINEUP_BENCH_TYPE_ID:
                continue
            if type_id is not None and int(type_id) != LINEUP_STARTER_TYPE_ID:
                continue
            player_id = row.get("player_id")
            if player_id is not None:
                ids.append(int(player_id))
        return ids

    return {
        "home": starters(extracted["home_lineups"]),
        "away": starters(extracted["away_lineups"]),
    }


def map_lineups_to_player_companion(raw_fixture: dict[str, Any]) -> dict[str, Any]:
    extracted = extract_fixture_lineups(raw_fixture)
    fixture_id = extracted.get("fixture_id")
    if fixture_id is None:
        return {"fixtures": {}, "_source": SOURCE_TAG}

    xi = extract_starting_xi_player_ids(raw_fixture)

    def side_block(side: str, rows: list[dict]) -> dict[str, Any]:
        block: dict[str, Any] = {
            "starting_xi_player_ids": xi[side],
            "source": SOURCE_TAG,
        }
        if not xi[side]:
            block["missing_starters_count"] = 11
        else:
            block["missing_starters_count"] = max(0, 11 - len(xi[side]))
        return block

    entry = {
        "fixture_id": fixture_id,
        "home_id": extracted["home_team_id"],
        "away_id": extracted["away_team_id"],
        "data_availability": extracted["data_availability"],
        "home_formation": extracted["home_formation"],
        "away_formation": extracted["away_formation"],
        "home_player": side_block("home", extracted["home_lineups"]),
        "away_player": side_block("away", extracted["away_lineups"]),
        "_source": SOURCE_TAG,
    }
    return {"fixtures": {str(fixture_id): entry}, "_source": SOURCE_TAG}


def map_lineups_to_tactical_companion(raw_fixture: dict[str, Any]) -> dict[str, Any]:
    extracted = extract_fixture_lineups(raw_fixture)
    fixture_id = extracted.get("fixture_id")
    if fixture_id is None:
        return {"fixtures": {}, "_source": SOURCE_TAG}

    entry = {
        "fixture_id": fixture_id,
        "home_id": extracted["home_team_id"],
        "away_id": extracted["away_team_id"],
        "data_availability": extracted["data_availability"],
        "home_formation": extracted["home_formation"] or "4-4-2",
        "away_formation": extracted["away_formation"] or "4-4-2",
        "_source": SOURCE_TAG,
    }
    return {"fixtures": {str(fixture_id): entry}, "_source": SOURCE_TAG}
