"""Mapper statistiche fixture Sportmonks → companion xG/shots."""

from __future__ import annotations

from typing import Any

from src.sportmonks.mappers._common import (
    FIXTURE_STAT_TYPE_IDS,
    extract_goals_from_scores,
    extract_participant_ids,
    merge_nested_dicts,
    parse_numeric,
    stat_developer_name,
    unwrap_entities,
)

SOURCE_TAG = "sportmonks_sample_mapper"


def _stats_index(fixture: dict[str, Any]) -> dict[tuple[int | str, str], float]:
    indexed: dict[tuple[int | str, str], float] = {}
    for entry in fixture.get("statistics") or ():
        if not isinstance(entry, dict):
            continue
        name = stat_developer_name(entry)
        if not name:
            type_id = entry.get("type_id")
            if type_id is not None:
                name = FIXTURE_STAT_TYPE_IDS.get(int(type_id))
        if not name:
            continue
        value = parse_numeric(entry.get("data")) or parse_numeric(entry.get("value"))
        if value is None:
            continue
        participant_id = entry.get("participant_id")
        location = entry.get("location")
        if participant_id is not None:
            indexed[(int(participant_id), name)] = value
        if location:
            indexed[(str(location).lower(), name)] = value
    return indexed


def extract_fixture_statistics(raw_fixture: dict[str, Any]) -> dict[str, Any]:
    """Estrae statistiche fixture per participant/location."""
    fixture = raw_fixture.get("data", raw_fixture)
    if isinstance(fixture, list):
        fixture = fixture[0] if fixture else {}
    fixture_id = fixture.get("id")
    home_id, away_id = extract_participant_ids(fixture)
    indexed = _stats_index(fixture)

    def side_stats(team_id: int | None, location: str) -> dict[str, float]:
        stats: dict[str, float] = {}
        for name in set(FIXTURE_STAT_TYPE_IDS.values()):
            if team_id is not None and (team_id, name) in indexed:
                stats[name] = indexed[(team_id, name)]
            elif (location, name) in indexed:
                stats[name] = indexed[(location, name)]
        return stats

    home_stats = side_stats(home_id, "home")
    away_stats = side_stats(away_id, "away")
    return {
        "fixture_id": fixture_id,
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home": home_stats,
        "away": away_stats,
        "source": SOURCE_TAG,
    }


def map_statistics_to_xg_companion(raw_fixture: dict[str, Any]) -> dict[str, Any]:
    """Produce frammento companion xG per una fixture."""
    fixture = raw_fixture.get("data", raw_fixture)
    if isinstance(fixture, list):
        fixture = fixture[0] if fixture else {}
    stats = extract_fixture_statistics(raw_fixture)
    fixture_id = stats.get("fixture_id")
    if fixture_id is None:
        return {"match_history": {}, "_source": SOURCE_TAG}

    home_xg = stats["home"].get("EXPECTED_GOALS")
    away_xg = stats["away"].get("EXPECTED_GOALS")
    home_goals, away_goals = extract_goals_from_scores(fixture)

    entry: dict[str, Any] = {"_source": SOURCE_TAG}
    if home_xg is not None:
        entry["home_xg"] = round(home_xg, 4)
    if away_xg is not None:
        entry["away_xg"] = round(away_xg, 4)
    if away_xg is not None:
        entry["home_xga"] = round(away_xg, 4)
    if home_xg is not None:
        entry["away_xga"] = round(home_xg, 4)
    if home_goals is not None:
        entry["home_goals"] = home_goals
        entry["away_goals_against"] = home_goals
    if away_goals is not None:
        entry["away_goals"] = away_goals
        entry["home_goals_against"] = away_goals

    if len(entry) <= 1:
        return {"match_history": {}, "_source": SOURCE_TAG}

    return {
        "match_history": {str(fixture_id): entry},
        "_source": SOURCE_TAG,
    }


def map_statistics_to_shots_companion(raw_fixture: dict[str, Any]) -> dict[str, Any]:
    """Produce frammento companion shots per una fixture."""
    stats = extract_fixture_statistics(raw_fixture)
    fixture_id = stats.get("fixture_id")
    if fixture_id is None:
        return {"match_history": {}, "_source": SOURCE_TAG}

    home = stats["home"]
    away = stats["away"]
    entry: dict[str, Any] = {"_source": SOURCE_TAG}

    if "SHOTS_TOTAL" in home:
        entry["home_shots"] = int(home["SHOTS_TOTAL"])
    if "SHOTS_TOTAL" in away:
        entry["away_shots"] = int(away["SHOTS_TOTAL"])
    if "SHOTS_ON_TARGET" in home:
        entry["home_sot"] = int(home["SHOTS_ON_TARGET"])
    if "SHOTS_ON_TARGET" in away:
        entry["away_sot"] = int(away["SHOTS_ON_TARGET"])
    if "DANGEROUS_ATTACKS" in home:
        entry["home_big_chances"] = int(home["DANGEROUS_ATTACKS"])
    if "DANGEROUS_ATTACKS" in away:
        entry["away_big_chances"] = int(away["DANGEROUS_ATTACKS"])

    home_xg = home.get("EXPECTED_GOALS")
    away_xg = away.get("EXPECTED_GOALS")
    if home_xg is not None and "SHOTS_TOTAL" in home and home["SHOTS_TOTAL"] > 0:
        entry["home_xg_per_shot"] = round(home_xg / home["SHOTS_TOTAL"], 4)
    if away_xg is not None and "SHOTS_TOTAL" in away and away["SHOTS_TOTAL"] > 0:
        entry["away_xg_per_shot"] = round(away_xg / away["SHOTS_TOTAL"], 4)
    if "GOALS" in home and "SHOTS_TOTAL" in home and home["SHOTS_TOTAL"] > 0:
        entry["home_conversion_rate"] = round(home["GOALS"] / home["SHOTS_TOTAL"], 4)
    if "GOALS" in away and "SHOTS_TOTAL" in away and away["SHOTS_TOTAL"] > 0:
        entry["away_conversion_rate"] = round(away["GOALS"] / away["SHOTS_TOTAL"], 4)

    return {
        "match_history": {str(fixture_id): entry},
        "_source": SOURCE_TAG,
    }


def _aggregate_team_xg(match_history: dict[str, dict]) -> dict[str, dict]:
    accum: dict[str, dict[str, list[float]]] = {}
    for entry in match_history.values():
        home_xg = entry.get("home_xg")
        away_xg = entry.get("away_xg")
        home_xga = entry.get("home_xga")
        away_xga = entry.get("away_xga")
        # team ids not in match_history entries — skip team aggregate here
        _ = (home_xg, away_xg, home_xga, away_xga)
    return {}


def map_statistics_payload_to_companions(payload: dict[str, Any]) -> tuple[dict, dict]:
    """Aggrega payload Sportmonks (lista fixture) in companion xG e shots."""
    xg_companion: dict[str, Any] = {"teams": {}, "match_history": {}, "_source": SOURCE_TAG}
    shots_companion: dict[str, Any] = {"teams": {}, "match_history": {}, "_source": SOURCE_TAG}

    for fixture in unwrap_entities(payload):
        xg_part = map_statistics_to_xg_companion(fixture)
        shots_part = map_statistics_to_shots_companion(fixture)
        xg_companion = merge_nested_dicts(xg_companion, xg_part)
        shots_companion = merge_nested_dicts(shots_companion, shots_part)

    return xg_companion, shots_companion
