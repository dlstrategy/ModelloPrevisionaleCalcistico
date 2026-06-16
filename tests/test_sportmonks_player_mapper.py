"""Test mapper player Sportmonks (Fase 3a)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.players.global_registry import PlayerCareer
from src.players.player_skill import PlayerSkillVector, skill_from_snapshot
from src.sportmonks.mappers.player_mapper import (
    extract_player_skill_vector,
    map_player_statistics_to_snapshot,
    map_players_payload_to_careers,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"


@pytest.fixture
def player_payload():
    return json.loads((FIXTURES / "player_statistics_sample.json").read_text(encoding="utf-8"))


def test_reads_player_sample(player_payload):
    snapshot = map_player_statistics_to_snapshot(player_payload["data"], league_id=384, season_id=25000)
    assert snapshot.player_id == 1001
    assert snapshot.minutes == 2800
    assert snapshot.rating == pytest.approx(7.4)


def test_produces_player_career(player_payload):
    careers = map_players_payload_to_careers(player_payload)
    assert 1001 in careers
    career = careers[1001]
    assert isinstance(career, PlayerCareer)
    assert career.snapshots[0].league_id == 384


def test_role_normalization(player_payload):
    skill = extract_player_skill_vector(player_payload["data"])
    assert isinstance(skill, PlayerSkillVector)
    assert skill.role == "forward"


def test_low_sample_handling():
    raw = {
        "id": 2002,
        "display_name": "Low Sample",
        "league_id": 384,
        "statistics": [{"details": [{"type_id": 119, "value": {"total": 120}}]}],
    }
    snapshot = map_player_statistics_to_snapshot(raw, league_id=384)
    assert snapshot.minutes == 120
    assert snapshot.sample_confidence < 0.5


def test_missing_stats_no_crash():
    raw = {"id": 3003, "display_name": "Empty", "league_id": 384, "statistics": []}
    snapshot = map_player_statistics_to_snapshot(raw, league_id=384)
    assert snapshot.rating == 5.5
    assert snapshot.minutes == 0


def test_skill_vector_from_mapped_snapshot(player_payload):
    snapshot = map_player_statistics_to_snapshot(player_payload["data"], league_id=384)
    skill = skill_from_snapshot(snapshot)
    assert isinstance(skill, PlayerSkillVector)
    assert skill.overall > 0.5


def test_no_api_called(player_payload):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        map_players_payload_to_careers(player_payload)
        mock_get.assert_not_called()
