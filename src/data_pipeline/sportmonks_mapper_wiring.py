"""Wiring staging mapper Sportmonks → companion/registry (Fase 3b)."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.config import PROCESSED_DIR
from src.coaches.coach_registry import CoachProfile
from src.players.global_registry import PlayerCareer, PlayerLeagueSnapshot
from src.sportmonks.mappers._common import merge_nested_dicts, unwrap_entities
from src.sportmonks.mappers.coach_mapper import extract_current_fixture_coaches
from src.sportmonks.mappers.lineup_mapper import (
    map_lineups_to_player_companion,
    map_lineups_to_tactical_companion,
)
from src.sportmonks.mappers.player_mapper import map_players_payload_to_careers
from src.sportmonks.mappers.standings_mapper import map_standings_to_companion
from src.sportmonks.mappers.statistics_mapper import map_statistics_payload_to_companions

BASE_FIXTURE_INCLUDES = "participants;scores;state"
ADVANCED_FIXTURE_INCLUDES = (
    "participants;scores;state;statistics;lineups;formations;coaches"
)
STAGING_SOURCE = "sportmonks_mapper_staging"

COMPANION_FILENAMES = {
    "xg": "xg.json",
    "shots": "shots.json",
    "lineups": "lineups.json",
    "tactical": "tactical.json",
    "standings": "standings.json",
    "coach_profiles": "coach_profiles.json",
    "player_careers": "player_careers.json",
}


def build_fixture_includes(enable_advanced_mappers: bool) -> str:
    """Include string per fetch fixture — base di default."""
    if enable_advanced_mappers:
        return ADVANCED_FIXTURE_INCLUDES
    return BASE_FIXTURE_INCLUDES


def build_advanced_include_string(enable_advanced_mappers: bool) -> str:
    """Alias esplicito per include avanzati."""
    return build_fixture_includes(enable_advanced_mappers)


def companions_dir_for_league(league_id: int) -> Path:
    return PROCESSED_DIR / f"league_{league_id}_companions"


def _merge_fixture_entities(*payloads: dict[str, Any] | None) -> list[dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {}
    for payload in payloads:
        if not payload:
            continue
        for fixture in unwrap_entities(payload):
            fixture_id = fixture.get("id")
            if fixture_id is None:
                continue
            merged[int(fixture_id)] = fixture
    return list(merged.values())


def _coach_profile_to_dict(profile: CoachProfile) -> dict[str, Any]:
    data = asdict(profile)
    data["source"] = STAGING_SOURCE
    return data


def _snapshot_to_dict(snapshot: PlayerLeagueSnapshot) -> dict[str, Any]:
    return asdict(snapshot)


def _career_to_dict(career: PlayerCareer) -> dict[str, Any]:
    return {
        "player_id": career.player_id,
        "player_name": career.player_name,
        "snapshots": [_snapshot_to_dict(s) for s in career.snapshots],
    }


@dataclass
class SportmonksMappedArtifacts:
    league_id: int
    season_id: int | None
    xg_companion: dict[str, Any] = field(default_factory=dict)
    shots_companion: dict[str, Any] = field(default_factory=dict)
    lineup_companion: dict[str, Any] = field(default_factory=dict)
    tactical_companion: dict[str, Any] = field(default_factory=dict)
    standings_companion: dict[str, Any] = field(default_factory=dict)
    coach_registry: dict[int, CoachProfile] = field(default_factory=dict)
    player_careers: dict[int, PlayerCareer] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def build_companion_artifacts_from_payloads(
    *,
    league_id: int,
    season_id: int | None = None,
    fixture_payloads: list[dict[str, Any] | None] | None = None,
    standings_payload: dict[str, Any] | None = None,
    players_payloads: list[dict[str, Any] | None] | None = None,
) -> SportmonksMappedArtifacts:
    """Applica mapper 3a su payload già scaricati o sample — nessuna HTTP."""
    fixtures = _merge_fixture_entities(*(fixture_payloads or ()))
    warnings: list[str] = []

    xg_companion: dict[str, Any] = {"teams": {}, "match_history": {}, "_source": STAGING_SOURCE}
    shots_companion: dict[str, Any] = {"teams": {}, "match_history": {}, "_source": STAGING_SOURCE}
    lineup_companion: dict[str, Any] = {"fixtures": {}, "_source": STAGING_SOURCE}
    tactical_companion: dict[str, Any] = {"fixtures": {}, "_source": STAGING_SOURCE}
    coach_registry: dict[int, CoachProfile] = {}

    if fixtures:
        xg_part, shots_part = map_statistics_payload_to_companions({"data": fixtures})
        xg_companion = merge_nested_dicts(xg_companion, xg_part)
        shots_companion = merge_nested_dicts(shots_companion, shots_part)
        xg_companion["_source"] = STAGING_SOURCE
        shots_companion["_source"] = STAGING_SOURCE

        for fixture in fixtures:
            lineup_part = map_lineups_to_player_companion(fixture)
            tactical_part = map_lineups_to_tactical_companion(fixture)
            lineup_companion = merge_nested_dicts(lineup_companion, lineup_part)
            tactical_companion = merge_nested_dicts(tactical_companion, tactical_part)
            for team_id, profile in extract_current_fixture_coaches(fixture).items():
                coach_registry[team_id] = profile

        lineup_companion["_source"] = STAGING_SOURCE
        tactical_companion["_source"] = STAGING_SOURCE
    else:
        warnings.append("no_fixture_payloads")

    standings_companion: dict[str, Any] = {"teams": {}, "_source": STAGING_SOURCE}
    if standings_payload:
        standings_companion = map_standings_to_companion(standings_payload)
        standings_companion["_source"] = STAGING_SOURCE
    else:
        warnings.append("no_standings_payload")

    player_careers: dict[int, PlayerCareer] = {}
    if players_payloads:
        for payload in players_payloads:
            if not payload:
                continue
            player_careers.update(map_players_payload_to_careers(payload))
    else:
        warnings.append("no_players_payloads")

    sources = {
        "xg": STAGING_SOURCE,
        "shots": STAGING_SOURCE,
        "lineups": STAGING_SOURCE,
        "tactical": STAGING_SOURCE,
        "standings": STAGING_SOURCE if standings_payload else "missing",
        "coach_registry": STAGING_SOURCE,
        "player_careers": STAGING_SOURCE if player_careers else "missing",
    }

    return SportmonksMappedArtifacts(
        league_id=league_id,
        season_id=season_id,
        xg_companion=xg_companion,
        shots_companion=shots_companion,
        lineup_companion=lineup_companion,
        tactical_companion=tactical_companion,
        standings_companion=standings_companion,
        coach_registry=coach_registry,
        player_careers=player_careers,
        sources=sources,
        warnings=tuple(warnings),
    )


def map_advanced_sportmonks_payloads(
    *,
    league_id: int,
    season_id: int | None = None,
    past_fixtures_payload: dict[str, Any] | None = None,
    future_fixtures_payload: dict[str, Any] | None = None,
    standings_payload: dict[str, Any] | None = None,
    players_payloads: list[dict[str, Any] | None] | None = None,
) -> SportmonksMappedArtifacts:
    """Alias per apply_mappers_to_sync_payloads."""
    return build_companion_artifacts_from_payloads(
        league_id=league_id,
        season_id=season_id,
        fixture_payloads=[past_fixtures_payload, future_fixtures_payload],
        standings_payload=standings_payload,
        players_payloads=players_payloads,
    )


def apply_mappers_to_sync_payloads(
    *,
    league_id: int,
    season_id: int | None = None,
    past_fixtures_payload: dict[str, Any] | None = None,
    future_fixtures_payload: dict[str, Any] | None = None,
    standings_payload: dict[str, Any] | None = None,
    players_payloads: list[dict[str, Any] | None] | None = None,
) -> SportmonksMappedArtifacts:
    return map_advanced_sportmonks_payloads(
        league_id=league_id,
        season_id=season_id,
        past_fixtures_payload=past_fixtures_payload,
        future_fixtures_payload=future_fixtures_payload,
        standings_payload=standings_payload,
        players_payloads=players_payloads,
    )


def _contains_token(value: Any, token: str) -> bool:
    if not token:
        return False
    if isinstance(value, str):
        return token in value
    if isinstance(value, dict):
        return any(_contains_token(v, token) for v in value.values())
    if isinstance(value, list):
        return any(_contains_token(v, token) for v in value)
    return False


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _walk_numbers(value: Any) -> list[Any]:
    nums: list[Any] = []
    if isinstance(value, dict):
        for v in value.values():
            nums.extend(_walk_numbers(v))
    elif isinstance(value, list):
        for v in value:
            nums.extend(_walk_numbers(v))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        nums.append(value)
    return nums


def validate_mapped_artifacts(
    artifacts: SportmonksMappedArtifacts,
    *,
    api_token: str | None = None,
) -> list[str]:
    """Validazione non bloccante — ritorna warning."""
    warnings: list[str] = []

    if not artifacts.xg_companion.get("match_history") and not artifacts.shots_companion.get(
        "match_history"
    ):
        warnings.append("xg_and_shots_match_history_empty")

    if not artifacts.lineup_companion.get("fixtures"):
        warnings.append("lineup_companion_empty")
    if not artifacts.tactical_companion.get("fixtures"):
        warnings.append("tactical_companion_empty")

    if not artifacts.standings_companion.get("teams"):
        warnings.append("standings_companion_empty")
    if not artifacts.coach_registry:
        warnings.append("coach_registry_empty")
    if not artifacts.player_careers:
        warnings.append("player_careers_empty")

    if not artifacts.sources.get("xg"):
        warnings.append("missing_source_xg")

    payload = artifacts_to_serializable_dict(artifacts)
    if api_token and _contains_token(payload, api_token):
        warnings.append("token_leak_detected")

    for number in _walk_numbers(payload):
        if not _is_finite_number(number):
            warnings.append("non_finite_numeric_value")
            break

    warnings.extend(artifacts.warnings)
    return warnings


def artifacts_to_serializable_dict(artifacts: SportmonksMappedArtifacts) -> dict[str, Any]:
    return {
        "league_id": artifacts.league_id,
        "season_id": artifacts.season_id,
        "sources": dict(artifacts.sources),
        "warnings": list(artifacts.warnings),
        "xg_companion": artifacts.xg_companion,
        "shots_companion": artifacts.shots_companion,
        "lineup_companion": artifacts.lineup_companion,
        "tactical_companion": artifacts.tactical_companion,
        "standings_companion": artifacts.standings_companion,
        "coach_profiles": {
            "coaches": [_coach_profile_to_dict(p) for p in artifacts.coach_registry.values()]
        },
        "player_careers": {
            "players": [_career_to_dict(c) for c in artifacts.player_careers.values()]
        },
    }


def write_companion_artifacts(
    artifacts: SportmonksMappedArtifacts,
    output_dir: Path,
) -> list[Path]:
    """Scrive companion/registry su path esplicito (staging)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    serializable = artifacts_to_serializable_dict(artifacts)
    written: list[Path] = []

    mapping = {
        COMPANION_FILENAMES["xg"]: serializable["xg_companion"],
        COMPANION_FILENAMES["shots"]: serializable["shots_companion"],
        COMPANION_FILENAMES["lineups"]: serializable["lineup_companion"],
        COMPANION_FILENAMES["tactical"]: serializable["tactical_companion"],
        COMPANION_FILENAMES["standings"]: serializable["standings_companion"],
        COMPANION_FILENAMES["coach_profiles"]: serializable["coach_profiles"],
        COMPANION_FILENAMES["player_careers"]: serializable["player_careers"],
    }

    for filename, payload in mapping.items():
        path = output_dir / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written.append(path)

    manifest = {
        "league_id": artifacts.league_id,
        "season_id": artifacts.season_id,
        "sources": serializable["sources"],
        "warnings": serializable["warnings"],
        "files": [p.name for p in written],
        "_source": STAGING_SOURCE,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    written.append(manifest_path)
    return written
