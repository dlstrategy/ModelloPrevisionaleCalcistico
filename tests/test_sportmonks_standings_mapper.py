"""Test mapper standings Sportmonks (Fase 3a)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.sportmonks.mappers.standings_mapper import map_standings_payload, map_standings_to_companion

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"


@pytest.fixture
def standings_payload():
    return json.loads((FIXTURES / "standings_season_sample.json").read_text(encoding="utf-8"))


def test_reads_standings_sample(standings_payload):
    mapped = map_standings_payload(standings_payload)
    assert mapped[8]["position"] == 1
    assert mapped[8]["points"] == 12
    assert mapped[4]["position"] == 8


def test_team_id_keys(standings_payload):
    mapped = map_standings_payload(standings_payload)
    assert mapped[8]["team_name"] == "Lazio"
    assert mapped[8]["played"] == 5


def test_missing_fields_fallback():
    raw = {"data": [{"participant": {"id": 1, "name": "X"}, "position": 3}]}
    mapped = map_standings_payload(raw)
    assert mapped[1]["position"] == 3
    assert mapped[1]["points"] is None


def test_companion_format(standings_payload):
    companion = map_standings_to_companion(standings_payload)
    assert companion["teams"]["8"]["points"] == 12
    assert companion["_source"] == "sportmonks_sample_mapper"


def test_motivation_can_use_points(standings_payload):
    mapped = map_standings_payload(standings_payload)
    assert mapped[8]["points"] > mapped[4]["points"]


def test_no_api_called(standings_payload):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        map_standings_payload(standings_payload)
        mock_get.assert_not_called()
