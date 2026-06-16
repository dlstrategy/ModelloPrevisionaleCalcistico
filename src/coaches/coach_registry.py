"""Registry mock profili allenatori (offline)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import FIXTURES_DIR
from src.coaches.unknown_coach_policy import DEFAULT_COACH_POLICY

COACH_PROFILES_PATH = FIXTURES_DIR / "coaches" / "coach_profiles.json"


@dataclass(frozen=True)
class CoachProfile:
    coach_id: int | None
    coach_name: str
    team_id: int
    league_id: int
    country_code: str | None
    season_id: int | None
    appointed_at: str | None
    matches_in_charge: int
    career_matches: int
    career_ppg: float | None
    team_ppg_before: float | None
    team_ppg_under_coach: float | None
    goals_for_delta: float | None
    goals_against_delta: float | None
    xg_delta: float | None
    xga_delta: float | None
    formation_changes_last_10: int | None
    lineup_rotation_rate: float | None
    preferred_style: str | None
    pressing_intensity: float | None
    defensive_line_height: float | None
    prior_league_id: int | None
    prior_country_code: str | None
    prior_league_matches: int
    prior_foreign_league_matches: int
    same_country_experience_matches: int
    cross_country_experience_matches: int
    new_manager_bounce_matches: int
    data_confidence: float
    source: str


def _clamp01(value: float | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return max(0.0, min(float(value), 1.0))


def _profile_from_dict(data: dict) -> CoachProfile:
    return CoachProfile(
        coach_id=int(data["coach_id"]) if data.get("coach_id") is not None else None,
        coach_name=str(data.get("coach_name", "Unknown")),
        team_id=int(data["team_id"]),
        league_id=int(data["league_id"]),
        country_code=str(data["country_code"]) if data.get("country_code") else None,
        season_id=int(data["season_id"]) if data.get("season_id") is not None else None,
        appointed_at=str(data["appointed_at"]) if data.get("appointed_at") else None,
        matches_in_charge=int(data.get("matches_in_charge", 0)),
        career_matches=int(data.get("career_matches", 0)),
        career_ppg=float(data["career_ppg"]) if data.get("career_ppg") is not None else None,
        team_ppg_before=float(data["team_ppg_before"]) if data.get("team_ppg_before") is not None else None,
        team_ppg_under_coach=float(data["team_ppg_under_coach"]) if data.get("team_ppg_under_coach") is not None else None,
        goals_for_delta=float(data["goals_for_delta"]) if data.get("goals_for_delta") is not None else None,
        goals_against_delta=float(data["goals_against_delta"]) if data.get("goals_against_delta") is not None else None,
        xg_delta=float(data["xg_delta"]) if data.get("xg_delta") is not None else None,
        xga_delta=float(data["xga_delta"]) if data.get("xga_delta") is not None else None,
        formation_changes_last_10=int(data["formation_changes_last_10"]) if data.get("formation_changes_last_10") is not None else None,
        lineup_rotation_rate=_clamp01(data.get("lineup_rotation_rate")),
        preferred_style=str(data["preferred_style"]) if data.get("preferred_style") else None,
        pressing_intensity=_clamp01(data.get("pressing_intensity")),
        defensive_line_height=_clamp01(data.get("defensive_line_height")),
        prior_league_id=int(data["prior_league_id"]) if data.get("prior_league_id") is not None else None,
        prior_country_code=str(data["prior_country_code"]) if data.get("prior_country_code") else None,
        prior_league_matches=int(data.get("prior_league_matches", 0)),
        prior_foreign_league_matches=int(data.get("prior_foreign_league_matches", 0)),
        same_country_experience_matches=int(data.get("same_country_experience_matches", 0)),
        cross_country_experience_matches=int(data.get("cross_country_experience_matches", 0)),
        new_manager_bounce_matches=int(data.get("new_manager_bounce_matches", 0)),
        data_confidence=_clamp01(data.get("data_confidence"), DEFAULT_COACH_POLICY.default_confidence),
        source=str(data.get("source", "mock_coach_profiles")),
    )


def load_coach_profiles(
    league_id: int | None = None,
    season_id: int | None = None,
    *,
    path: Path | None = None,
) -> dict[int, CoachProfile]:
    """Carica profili coach mock keyed by team_id."""
    source = path or COACH_PROFILES_PATH
    if not source.exists():
        return {}
    payload = json.loads(source.read_text(encoding="utf-8"))
    profiles: dict[int, CoachProfile] = {}
    for item in payload.get("coaches", ()):
        profile = _profile_from_dict(item)
        if league_id is not None and profile.league_id != league_id:
            continue
        if season_id is not None and profile.season_id is not None and profile.season_id != season_id:
            continue
        profiles[profile.team_id] = profile
    return profiles


def unknown_coach_profile(
    team_id: int,
    league_id: int,
    season_id: int | None = None,
) -> CoachProfile:
    policy = DEFAULT_COACH_POLICY
    return CoachProfile(
        coach_id=None,
        coach_name="Unknown Coach",
        team_id=team_id,
        league_id=league_id,
        country_code=None,
        season_id=season_id,
        appointed_at=None,
        matches_in_charge=0,
        career_matches=0,
        career_ppg=None,
        team_ppg_before=None,
        team_ppg_under_coach=None,
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
        new_manager_bounce_matches=0,
        data_confidence=policy.default_confidence,
        source="unknown_coach_fallback",
    )


def get_team_coach_profile(
    team_id: int,
    league_id: int,
    season_id: int | None = None,
    *,
    profiles: dict[int, CoachProfile] | None = None,
) -> CoachProfile:
    registry = profiles if profiles is not None else load_coach_profiles(league_id, season_id)
    profile = registry.get(team_id)
    if profile is None:
        return unknown_coach_profile(team_id, league_id, season_id)
    return profile
