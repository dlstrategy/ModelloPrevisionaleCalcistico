"""Mapper coach Sportmonks → CoachProfile."""

from __future__ import annotations

from typing import Any

from src.coaches.coach_registry import CoachProfile
from src.coaches.unknown_coach_policy import DEFAULT_COACH_POLICY
from src.sportmonks.mappers._common import (
    COACH_STAT_TYPE_IDS,
    extract_participant_ids,
    parse_numeric,
    unwrap_entity,
    unwrap_entities,
)

SOURCE_TAG = "sportmonks_sample_mapper"


def extract_coach_statistics(raw_coach: dict[str, Any]) -> dict[str, float | int | None]:
    stats: dict[str, float | int | None] = {}
    for block in raw_coach.get("statistics") or ():
        if not isinstance(block, dict):
            continue
        for detail in block.get("details") or ():
            if not isinstance(detail, dict):
                continue
            type_id = detail.get("type_id")
            name = None
            if type_id is not None:
                name = COACH_STAT_TYPE_IDS.get(int(type_id))
            type_info = detail.get("type")
            if not name and isinstance(type_info, dict):
                dev = type_info.get("developer_name")
                if dev:
                    name = str(dev).upper()
            if not name:
                continue
            value = detail.get("value") or {}
            if name == "RATING":
                parsed = parse_numeric(value.get("average")) or parse_numeric(value)
            elif name in {"MATCHES", "WIN", "DRAW", "LOST", "SUBSTITUTIONS"}:
                parsed = parse_numeric(value.get("total")) or parse_numeric(value)
            else:
                parsed = parse_numeric(value.get("average")) or parse_numeric(value.get("total"))
                if parsed is None:
                    parsed = parse_numeric(value)
            if parsed is not None:
                stats[name] = int(parsed) if name in {"MATCHES", "WIN", "DRAW", "LOST", "SUBSTITUTIONS"} else float(parsed)
    return stats


def _confidence_from_stats(stats: dict[str, float | int | None], has_id: bool) -> float:
    if not has_id:
        return DEFAULT_COACH_POLICY.default_confidence
    matches = stats.get("MATCHES")
    ppg = stats.get("AVERAGE_POINTS_PER_GAME")
    if matches and int(matches) >= 20 and ppg is not None:
        return 0.72
    if matches and int(matches) >= 5:
        return 0.55
    return 0.40


def map_coach_to_profile(
    raw_coach: dict[str, Any],
    *,
    team_id: int,
    league_id: int,
    season_id: int | None = None,
) -> CoachProfile:
    coach_id = raw_coach.get("id")
    name = (
        raw_coach.get("display_name")
        or raw_coach.get("name")
        or raw_coach.get("common_name")
        or "Unknown Coach"
    )
    country = raw_coach.get("country") or {}
    country_code = None
    if isinstance(country, dict):
        country_code = country.get("iso2") or country.get("fifa_name")
    elif raw_coach.get("country_id"):
        country_code = str(raw_coach.get("country_id"))

    stats = extract_coach_statistics(raw_coach)
    matches = int(stats.get("MATCHES") or 0)
    career_ppg = stats.get("AVERAGE_POINTS_PER_GAME")
    if career_ppg is not None:
        career_ppg = float(career_ppg)

    confidence = _confidence_from_stats(stats, coach_id is not None)

    return CoachProfile(
        coach_id=int(coach_id) if coach_id is not None else None,
        coach_name=str(name),
        team_id=team_id,
        league_id=league_id,
        country_code=str(country_code) if country_code else None,
        season_id=season_id,
        appointed_at=raw_coach.get("start") or raw_coach.get("appointed_at"),
        matches_in_charge=matches,
        career_matches=matches,
        career_ppg=career_ppg,
        team_ppg_before=None,
        team_ppg_under_coach=career_ppg,
        goals_for_delta=None,
        goals_against_delta=None,
        xg_delta=None,
        xga_delta=None,
        formation_changes_last_10=None,
        lineup_rotation_rate=None,
        preferred_style=None,
        pressing_intensity=None,
        defensive_line_height=None,
        prior_league_id=None,
        prior_country_code=None,
        prior_league_matches=0,
        prior_foreign_league_matches=0,
        same_country_experience_matches=0,
        cross_country_experience_matches=0,
        new_manager_bounce_matches=min(matches, 8) if matches else 0,
        data_confidence=confidence,
        source=SOURCE_TAG,
    )


def extract_current_fixture_coaches(raw_fixture: dict[str, Any]) -> dict[int, CoachProfile]:
    fixture = unwrap_entity(raw_fixture)
    home_id, away_id = extract_participant_ids(fixture)
    league_id = int(fixture.get("league_id") or 0)
    season_id = fixture.get("season_id")
    season_id = int(season_id) if season_id is not None else None

    profiles: dict[int, CoachProfile] = {}
    for coach_row in fixture.get("coaches") or ():
        if not isinstance(coach_row, dict):
            continue
        meta = coach_row.get("meta") or {}
        team_id = coach_row.get("team_id") or meta.get("participant_id")
        location = str(meta.get("location", "")).lower()
        if team_id is None:
            if location == "home" and home_id is not None:
                team_id = home_id
            elif location == "away" and away_id is not None:
                team_id = away_id
        if team_id is None:
            continue
        coach_data = coach_row.get("coach") if isinstance(coach_row.get("coach"), dict) else coach_row
        profile = map_coach_to_profile(
            coach_data,
            team_id=int(team_id),
            league_id=league_id,
            season_id=season_id,
        )
        profiles[int(team_id)] = profile
    return profiles


def map_coaches_payload_to_registry(payload: dict[str, Any]) -> dict[int, CoachProfile]:
    registry: dict[int, CoachProfile] = {}
    for coach in unwrap_entities(payload):
        team_id = coach.get("team_id")
        league_id = coach.get("league_id")
        if team_id is None or league_id is None:
            continue
        profile = map_coach_to_profile(
            coach,
            team_id=int(team_id),
            league_id=int(league_id),
            season_id=int(coach["season_id"]) if coach.get("season_id") is not None else None,
        )
        registry[profile.team_id] = profile
    return registry
