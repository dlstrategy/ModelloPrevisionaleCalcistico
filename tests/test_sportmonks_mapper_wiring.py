"""Test wiring staging mapper Sportmonks (Fase 3b)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.data_pipeline.sportmonks_mapper_wiring import (
    ADVANCED_FIXTURE_INCLUDES,
    BASE_FIXTURE_INCLUDES,
    STAGING_SOURCE,
    SportmonksMappedArtifacts,
    apply_mappers_to_sync_payloads,
    artifacts_to_serializable_dict,
    build_companion_artifacts_from_payloads,
    build_fixture_includes,
    validate_mapped_artifacts,
    write_companion_artifacts,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"
FAKE_TOKEN = "super-secret-wiring-test-token"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _combined_fixture_payload() -> dict:
    """Unisce sample offline per fixture 1001 (statistics + lineups + coaches)."""
    stats = _load("fixture_statistics_sample.json")
    lineups = _load("fixture_lineups_sample.json")
    coaches = _load("fixture_coaches_sample.json")
    fixture = dict(stats["data"])
    for key in ("lineups", "lineups_confirmed", "formations"):
        if key in lineups["data"]:
            fixture[key] = lineups["data"][key]
    if "coaches" in coaches["data"]:
        fixture["coaches"] = coaches["data"]["coaches"]
    return {"data": [fixture]}


@pytest.fixture
def combined_payload():
    return _combined_fixture_payload()


@pytest.fixture
def standings_payload():
    return _load("standings_season_sample.json")


@pytest.fixture
def player_payload():
    return _load("player_statistics_sample.json")


def test_build_fixture_includes_false_returns_base():
    assert build_fixture_includes(False) == BASE_FIXTURE_INCLUDES
    assert BASE_FIXTURE_INCLUDES == "participants;scores;state"


def test_build_fixture_includes_true_returns_advanced():
    includes = build_fixture_includes(True)
    assert includes == ADVANCED_FIXTURE_INCLUDES
    assert "statistics" in includes
    assert "lineups" in includes
    assert "coaches" in includes
    assert "formations" in includes


def test_build_companion_artifacts_from_samples(
    combined_payload, standings_payload, player_payload
):
    artifacts = build_companion_artifacts_from_payloads(
        league_id=384,
        season_id=25000,
        fixture_payloads=[combined_payload],
        standings_payload=standings_payload,
        players_payloads=[player_payload],
    )
    assert artifacts.xg_companion.get("match_history")
    assert artifacts.shots_companion.get("match_history")
    assert artifacts.lineup_companion.get("fixtures")
    assert artifacts.tactical_companion.get("fixtures")
    assert artifacts.standings_companion.get("teams")
    assert artifacts.coach_registry
    assert artifacts.player_careers
    assert artifacts.sources["xg"] == STAGING_SOURCE


def test_missing_payloads_no_crash():
    artifacts = build_companion_artifacts_from_payloads(league_id=384)
    assert isinstance(artifacts, SportmonksMappedArtifacts)
    assert "no_fixture_payloads" in artifacts.warnings


def test_validate_mapped_artifacts_on_samples(combined_payload, standings_payload):
    artifacts = build_companion_artifacts_from_payloads(
        league_id=384,
        fixture_payloads=[combined_payload],
        standings_payload=standings_payload,
    )
    warnings = validate_mapped_artifacts(artifacts, api_token=FAKE_TOKEN)
    assert "token_leak_detected" not in warnings
    assert "non_finite_numeric_value" not in warnings


def test_artifacts_json_serializable(combined_payload, standings_payload, player_payload):
    artifacts = build_companion_artifacts_from_payloads(
        league_id=384,
        fixture_payloads=[combined_payload],
        standings_payload=standings_payload,
        players_payloads=[player_payload],
    )
    payload = artifacts_to_serializable_dict(artifacts)
    text = json.dumps(payload)
    parsed = json.loads(text)
    assert parsed["league_id"] == 384
    assert FAKE_TOKEN not in text


def test_write_companion_artifacts_to_tmp_path(
    tmp_path, combined_payload, standings_payload, player_payload
):
    artifacts = build_companion_artifacts_from_payloads(
        league_id=384,
        fixture_payloads=[combined_payload],
        standings_payload=standings_payload,
        players_payloads=[player_payload],
    )
    out_dir = tmp_path / "league_384_companions"
    paths = write_companion_artifacts(artifacts, out_dir)
    assert len(paths) >= 7
    assert (out_dir / "xg.json").exists()
    assert (out_dir / "manifest.json").exists()
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["_source"] == STAGING_SOURCE


def test_apply_mappers_alias(combined_payload):
    artifacts = apply_mappers_to_sync_payloads(
        league_id=384,
        past_fixtures_payload=combined_payload,
    )
    assert artifacts.xg_companion.get("_source") == STAGING_SOURCE


def test_no_api_called(combined_payload):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        build_companion_artifacts_from_payloads(
            league_id=384,
            fixture_payloads=[combined_payload],
        )
        mock_get.assert_not_called()


def test_token_not_in_artifact_output(combined_payload):
    artifacts = build_companion_artifacts_from_payloads(
        league_id=384,
        fixture_payloads=[combined_payload],
    )
    text = json.dumps(artifacts_to_serializable_dict(artifacts))
    assert FAKE_TOKEN not in text
