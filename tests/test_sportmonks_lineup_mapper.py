"""Test mapper lineups Sportmonks (Fase 3a)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.sportmonks.mappers.lineup_mapper import (
    extract_fixture_lineups,
    extract_starting_xi_player_ids,
    map_lineups_to_player_companion,
    map_lineups_to_tactical_companion,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"


@pytest.fixture
def lineup_payload():
    return json.loads((FIXTURES / "fixture_lineups_sample.json").read_text(encoding="utf-8"))


def test_reads_existing_lineup_sample(lineup_payload):
    extracted = extract_fixture_lineups(lineup_payload)
    assert extracted["fixture_id"] == 1001
    assert len(extracted["home_lineups"]) == 12


def test_extracts_home_away_xi(lineup_payload):
    xi = extract_starting_xi_player_ids(lineup_payload)
    assert len(xi["home"]) == 11
    assert len(xi["away"]) == 11
    assert 5012 not in xi["home"]


def test_extracts_player_ids(lineup_payload):
    xi = extract_starting_xi_player_ids(lineup_payload)
    assert xi["home"][0] == 5001
    assert xi["away"][0] == 6001


def test_extracts_formation(lineup_payload):
    extracted = extract_fixture_lineups(lineup_payload)
    assert extracted["home_formation"] == "4-3-3"
    assert extracted["away_formation"] == "4-4-2"


def test_missing_lineups_no_crash():
    raw = {"data": {"id": 1, "participants": [], "lineups": []}}
    extracted = extract_fixture_lineups(raw)
    assert extracted["home_lineups"] == []
    companion = map_lineups_to_player_companion(raw)
    entry = companion["fixtures"]["1"]
    assert entry["home_player"]["missing_starters_count"] == 11


def test_confirmed_lineup_availability(lineup_payload):
    extracted = extract_fixture_lineups(lineup_payload)
    assert extracted["data_availability"] == "confirmed_lineup"


def test_player_companion_compatible(lineup_payload):
    companion = map_lineups_to_player_companion(lineup_payload)
    entry = companion["fixtures"]["1001"]
    assert entry["home_id"] == 8
    assert entry["away_id"] == 4
    assert len(entry["home_player"]["starting_xi_player_ids"]) == 11
    assert entry["home_player"]["source"] == "sportmonks_sample_mapper"


def test_tactical_companion(lineup_payload):
    companion = map_lineups_to_tactical_companion(lineup_payload)
    entry = companion["fixtures"]["1001"]
    assert entry["home_formation"] == "4-3-3"
    assert entry["away_formation"] == "4-4-2"


def test_no_api_called(lineup_payload):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        map_lineups_to_player_companion(lineup_payload)
        mock_get.assert_not_called()
