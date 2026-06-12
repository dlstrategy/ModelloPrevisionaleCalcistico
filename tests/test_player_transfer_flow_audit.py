"""Audit test — flow completo giocatori/trasferimenti (Fase 2i-audit)."""

import json
import math

import pytest

from src.cli import main
from src.players.composable_transfer import resolve_composable_transfer_estimate
from src.players.player_value import resolve_player_value_for_league


def _resolve(player_id: int, target_league: int = 384, **kwargs):
    return resolve_composable_transfer_estimate(player_id, target_league, **kwargs)


def test_unknown_player():
    est = _resolve(99999)
    assert est.adapter_type == "unknown_player"
    assert est.rating == 0.50
    assert est.confidence <= 0.15
    assert "unknown_player" in est.notes


def test_same_league():
    est = _resolve(1001)
    assert est.adapter_type == "same_league"
    assert est.source_league_id == 384
    assert est.target_league_id == 384


def test_liga_to_serie_a_pair_specialist():
    est = _resolve(1006, role="forward")
    assert est.adapter_type == "pair_specialist"
    assert est.specialist_key == "564->384:forward"
    assert est.source_league_id == 564


def test_role_alias_fw_finds_forward_specialist():
    est = _resolve(1006, role="FW")
    assert est.adapter_type == "pair_specialist"
    assert est.specialist_key == "564->384:forward"


def test_unknown_source_league_general_adapter():
    est = _resolve(1003)
    assert est.adapter_type == "general_adapter"
    assert "fallback_league_profile" in est.notes
    assert "unknown_source_league" in est.notes
    assert est.confidence <= 0.30


def test_low_sample_minutes_in_notes():
    est = _resolve(1005)
    assert est.adapter_type == "same_league"
    assert "low_sample_minutes" in est.notes
    assert est.confidence <= 0.30


def test_output_bounded_with_notes():
    est = _resolve(1006, role="FW")
    assert 0.0 <= est.rating <= 1.0
    assert 0.0 <= est.confidence <= 1.0
    assert math.isfinite(est.rating)
    assert math.isfinite(est.confidence)
    assert len(est.notes) > 0


def test_cli_transfer_estimate_json(capsys):
    code = main(
        ["transfer-estimate", "--player-id", "1006", "--target-league", "384", "--role", "FW", "--json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "pair_specialist"
    assert payload["specialist_key"] == "564->384:forward"


def test_cli_unknown_player_json(capsys):
    code = main(
        ["transfer-estimate", "--player-id", "99999", "--target-league", "384", "--json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "unknown_player"


def test_player_value_api_matches_composable():
    value = resolve_player_value_for_league(1006, 384, role="FW")
    est = _resolve(1006, role="FW")
    assert value["source"] == est.adapter_type
    assert value["rating"] == est.rating
    assert value["confidence"] == est.confidence
