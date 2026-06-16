"""Mapper player statistics Sportmonks → PlayerCareer / PlayerSkillVector."""

from __future__ import annotations

from typing import Any

from src.players.global_registry import PlayerCareer, PlayerLeagueSnapshot
from src.players.player_skill import PlayerSkillVector, normalize_role, skill_from_snapshot
from src.sportmonks.mappers._common import PLAYER_STAT_TYPE_IDS, parse_numeric, unwrap_entities

SOURCE_TAG = "sportmonks_sample_mapper"
LOW_SAMPLE_MINUTES = 450


def _extract_player_stat_details(raw_player: dict[str, Any]) -> dict[str, float | int | None]:
    stats: dict[str, float | int | None] = {}
    statistics = raw_player.get("statistics") or []
    if statistics and isinstance(statistics[0], dict):
        details = statistics[0].get("details") or statistics
    else:
        details = statistics

    for detail in details or ():
        if not isinstance(detail, dict):
            continue
        if "details" in detail and isinstance(detail.get("details"), list):
            nested = _extract_player_stat_details({"statistics": [detail]})
            stats.update({k: v for k, v in nested.items() if v is not None})
            continue
        type_id = detail.get("type_id")
        name = PLAYER_STAT_TYPE_IDS.get(int(type_id)) if type_id is not None else None
        type_info = detail.get("type")
        if not name and isinstance(type_info, dict):
            dev = type_info.get("developer_name")
            if dev:
                name = str(dev).upper()
        if not name:
            continue
        value = detail.get("value") or detail.get("data") or {}
        if name == "RATING":
            parsed = parse_numeric(value.get("average")) or parse_numeric(value)
        else:
            parsed = parse_numeric(value.get("total")) or parse_numeric(value)
        if parsed is not None:
            stats[name] = int(parsed) if name in {"GOALS", "ASSISTS", "MINUTES"} else float(parsed)
    return stats


def map_player_statistics_to_snapshot(
    raw_player: dict[str, Any],
    *,
    league_id: int,
    season_id: int | None = None,
) -> PlayerLeagueSnapshot:
    player_id = int(raw_player["id"])
    name = raw_player.get("display_name") or raw_player.get("name") or f"Player {player_id}"
    statistics = raw_player.get("statistics") or []
    team_id = None
    if statistics and isinstance(statistics[0], dict):
        team_id = statistics[0].get("team_id")
    position = raw_player.get("position") or {}
    if isinstance(position, dict):
        position_code = position.get("developer_name") or position.get("name")
    else:
        position_code = raw_player.get("detailed_position_id") or raw_player.get("position_id")

    stats = _extract_player_stat_details(raw_player)
    minutes = int(stats.get("MINUTES") or 0)
    rating_raw = stats.get("RATING")
    rating = float(rating_raw) if rating_raw is not None else 5.5
    sample_confidence = 0.35 if minutes < LOW_SAMPLE_MINUTES else min(0.95, 0.45 + minutes / 3000.0)
    if rating_raw is None:
        sample_confidence = min(sample_confidence, 0.45)

    return PlayerLeagueSnapshot(
        player_id=player_id,
        player_name=str(name),
        league_id=league_id,
        season_id=season_id,
        team_id=int(team_id) if team_id is not None else None,
        position=str(position_code) if position_code is not None else None,
        minutes=minutes,
        rating=rating,
        rating_percentile=min(0.99, max(0.01, rating / 10.0)),
        sample_confidence=round(sample_confidence, 3),
    )


def map_players_payload_to_careers(payload: dict[str, Any]) -> dict[int, PlayerCareer]:
    careers: dict[int, PlayerCareer] = {}
    for raw_player in unwrap_entities(payload):
        player_id = raw_player.get("id")
        if player_id is None:
            continue
        league_id = raw_player.get("league_id")
        season_id = raw_player.get("season_id")
        if league_id is None:
            statistics = raw_player.get("statistics") or []
            if statistics and isinstance(statistics[0], dict):
                league_id = statistics[0].get("league_id") or league_id
                season_id = season_id or statistics[0].get("season_id")
        if league_id is None:
            continue
        snapshot = map_player_statistics_to_snapshot(
            raw_player,
            league_id=int(league_id),
            season_id=int(season_id) if season_id is not None else None,
        )
        existing = careers.get(int(player_id))
        if existing:
            careers[int(player_id)] = PlayerCareer(
                player_id=existing.player_id,
                player_name=existing.player_name,
                snapshots=existing.snapshots + (snapshot,),
            )
        else:
            careers[int(player_id)] = PlayerCareer(
                player_id=int(player_id),
                player_name=snapshot.player_name,
                snapshots=(snapshot,),
            )
    return careers


def extract_player_skill_vector(raw_player: dict[str, Any]) -> PlayerSkillVector | None:
    league_id = raw_player.get("league_id")
    if league_id is None:
        statistics = raw_player.get("statistics") or []
        if statistics and isinstance(statistics[0], dict):
            league_id = statistics[0].get("league_id")
    if league_id is None:
        return None
    snapshot = map_player_statistics_to_snapshot(raw_player, league_id=int(league_id))
    role = normalize_role(snapshot.position)
    if snapshot.minutes < LOW_SAMPLE_MINUTES and snapshot.rating == 5.5:
        return PlayerSkillVector(
            player_id=snapshot.player_id,
            role=role,
            overall=0.5,
            sample_confidence=snapshot.sample_confidence,
        ).sanitized()
    return skill_from_snapshot(snapshot)
