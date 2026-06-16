"""Test mapper coach Sportmonks (Fase 3a)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.coaches.coach_adaptation import estimate_coach_adaptation
from src.coaches.coach_registry import CoachProfile
from src.sportmonks.mappers.coach_mapper import (
    extract_coach_statistics,
    extract_current_fixture_coaches,
    map_coach_to_profile,
    map_coaches_payload_to_registry,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"


@pytest.fixture
def coach_payload():
    return json.loads((FIXTURES / "coach_sample.json").read_text(encoding="utf-8"))


@pytest.fixture
def fixture_coaches_payload():
    return json.loads((FIXTURES / "fixture_coaches_sample.json").read_text(encoding="utf-8"))


def test_reads_coach_sample(coach_payload):
    coach = coach_payload["data"]
    profile = map_coach_to_profile(coach, team_id=8, league_id=384, season_id=25000)
    assert isinstance(profile, CoachProfile)
    assert profile.coach_id == 90001
    assert profile.coach_name == "Sample Coach Alpha"


def test_statistics_matches_ppg_mapped(coach_payload):
    stats = extract_coach_statistics(coach_payload["data"])
    assert stats["MATCHES"] == 24
    assert stats["AVERAGE_POINTS_PER_GAME"] == pytest.approx(1.75)


def test_profile_without_statistics_lower_confidence():
    raw = {"id": 1, "display_name": "No Stats Coach"}
    profile = map_coach_to_profile(raw, team_id=1, league_id=384)
    assert profile.data_confidence <= 0.45
    assert profile.matches_in_charge == 0


def test_fixture_include_coaches(fixture_coaches_payload):
    profiles = extract_current_fixture_coaches(fixture_coaches_payload)
    assert 8 in profiles
    assert 4 in profiles
    assert profiles[8].career_ppg == pytest.approx(1.75)
    assert profiles[4].data_confidence <= 0.45


def test_unknown_coach_no_crash():
    profile = map_coach_to_profile({}, team_id=99, league_id=384)
    assert profile.coach_name == "Unknown Coach"
    assert profile.source == "sportmonks_sample_mapper"


def test_adaptation_on_mapped_profile(coach_payload):
    profile = map_coach_to_profile(coach_payload["data"], team_id=8, league_id=384)
    estimate = estimate_coach_adaptation(profile, target_league_id=384, target_country_code="IT")
    assert estimate.adaptation_score > 0


def test_registry_payload(coach_payload):
    registry = map_coaches_payload_to_registry(coach_payload)
    assert 8 in registry


def test_no_api_called(coach_payload):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        map_coach_to_profile(coach_payload["data"], team_id=8, league_id=384)
        mock_get.assert_not_called()
