"""Test mapper statistiche Sportmonks (Fase 3a)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.sportmonks.mappers.statistics_mapper import (
    extract_fixture_statistics,
    map_statistics_payload_to_companions,
    map_statistics_to_shots_companion,
    map_statistics_to_xg_companion,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"


@pytest.fixture
def stats_payload():
    return json.loads((FIXTURES / "fixture_statistics_sample.json").read_text(encoding="utf-8"))


def test_reads_existing_sportmonks_statistics_sample(stats_payload):
    stats = extract_fixture_statistics(stats_payload)
    assert stats["fixture_id"] == 1001
    assert stats["home"]["EXPECTED_GOALS"] == pytest.approx(1.21)
    assert stats["away"]["EXPECTED_GOALS"] == pytest.approx(1.05)


def test_produces_xg_companion(stats_payload):
    companion = map_statistics_to_xg_companion(stats_payload)
    entry = companion["match_history"]["1001"]
    assert entry["home_xg"] == pytest.approx(1.21)
    assert entry["away_xg"] == pytest.approx(1.05)
    assert entry["home_goals"] == 2
    assert entry["away_goals"] == 1


def test_produces_shots_companion(stats_payload):
    companion = map_statistics_to_shots_companion(stats_payload)
    entry = companion["match_history"]["1001"]
    assert entry["home_shots"] == 17
    assert entry["away_shots"] == 13
    assert entry["home_sot"] == 6
    assert "home_conversion_rate" in entry


def test_missing_statistics_no_crash():
    raw = {"data": {"id": 999, "participants": [], "statistics": []}}
    stats = extract_fixture_statistics(raw)
    assert stats["home"] == {}
    xg = map_statistics_to_xg_companion(raw)
    assert xg["match_history"] == {}


def test_numeric_string_values_converted():
    raw = {
        "data": {
            "id": 1001,
            "participants": [
                {"id": 8, "meta": {"location": "home"}},
                {"id": 4, "meta": {"location": "away"}},
            ],
            "statistics": [
                {
                    "type_id": 5304,
                    "participant_id": 8,
                    "location": "home",
                    "data": {"value": "1.21"},
                }
            ],
        }
    }
    stats = extract_fixture_statistics(raw)
    assert stats["home"]["EXPECTED_GOALS"] == pytest.approx(1.21)


def test_home_away_mapping(stats_payload):
    stats = extract_fixture_statistics(stats_payload)
    assert stats["home_team_id"] == 8
    assert stats["away_team_id"] == 4


def test_payload_to_companions(stats_payload):
    xg, shots = map_statistics_payload_to_companions(stats_payload)
    assert "1001" in xg["match_history"]
    assert "1001" in shots["match_history"]


def test_no_api_called(stats_payload):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        map_statistics_to_xg_companion(stats_payload)
        mock_get.assert_not_called()
