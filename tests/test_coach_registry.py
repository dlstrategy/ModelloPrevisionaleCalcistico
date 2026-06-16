"""Test registry mock profili allenatori."""

import pytest

from src.coaches.coach_registry import (
    COACH_PROFILES_PATH,
    CoachProfile,
    get_team_coach_profile,
    load_coach_profiles,
    unknown_coach_profile,
)


def test_fixture_exists():
    assert COACH_PROFILES_PATH.exists()


def test_load_coach_profiles():
    profiles = load_coach_profiles(league_id=384)
    assert len(profiles) >= 8
    assert all(isinstance(p, CoachProfile) for p in profiles.values())


def test_get_team_coach_by_team_id():
    profile = get_team_coach_profile(1, 384)
    assert profile.coach_id == 501
    assert profile.team_id == 1
    assert profile.source == "mock_coach_profiles"


def test_unknown_fallback_when_missing():
    profile = get_team_coach_profile(6, 384)
    assert profile.coach_id is None
    assert profile.source == "unknown_coach_fallback"
    assert profile.data_confidence == 0.10


def test_filter_league_id():
    profiles = load_coach_profiles(league_id=999)
    assert profiles == {}


def test_filter_season_id():
    profiles = load_coach_profiles(league_id=384, season_id=23614)
    assert 1 in profiles
    filtered = load_coach_profiles(league_id=384, season_id=99999)
    assert filtered == {}


def test_unknown_coach_profile_factory():
    profile = unknown_coach_profile(99, 384)
    assert profile.matches_in_charge == 0
    assert profile.career_matches == 0
    assert profile.data_confidence == 0.10
