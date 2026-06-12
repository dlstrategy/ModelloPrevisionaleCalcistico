"""Test composable transfer resolver."""

import json

from src.players.composable_transfer import resolve_composable_transfer_estimate


def test_same_league_player():
    est = resolve_composable_transfer_estimate(1001, 384)
    assert est.adapter_type == "same_league"
    assert est.source_league_id == 384
    assert 0.0 <= est.rating <= 1.0


def test_liga_to_serie_a_uses_pair_specialist():
    est = resolve_composable_transfer_estimate(1006, 384, role="forward")
    assert est.adapter_type == "pair_specialist"
    assert est.source_league_id == 564
    assert est.target_league_id == 384
    assert est.specialist_key == "564->384:forward"


def test_role_fw_uses_forward_specialist():
    est = resolve_composable_transfer_estimate(1006, 384, role="FW")
    assert est.adapter_type == "pair_specialist"
    assert est.specialist_key == "564->384:forward"


def test_role_st_uses_forward_specialist():
    est = resolve_composable_transfer_estimate(1006, 384, role="ST")
    assert est.specialist_key == "564->384:forward"


def test_role_cb_uses_defender_specialist_when_available():
    from src.players.pair_specialists import find_best_specialist

    spec = find_best_specialist(82, 8, "CB")
    assert spec is not None
    assert spec.role == "defender"


def test_role_forward_normalized_still_works():
    est = resolve_composable_transfer_estimate(1006, 384, role="forward")
    assert est.specialist_key == "564->384:forward"


def test_unknown_role_does_not_crash():
    est = resolve_composable_transfer_estimate(1006, 384, role="WINGBACK")
    assert est.adapter_type in {"pair_specialist", "general_adapter"}
    assert "unknown_role" in est.notes
    assert 0.0 <= est.rating <= 1.0


def test_uncovered_pair_uses_general_adapter():
    est = resolve_composable_transfer_estimate(1003, 384)
    assert est.adapter_type == "general_adapter"
    assert est.source_league_id == 999
    assert "fallback_league_profile" in est.notes
    assert est.confidence <= 0.30


def test_unknown_player_fallback():
    est = resolve_composable_transfer_estimate(99999, 384)
    assert est.adapter_type == "unknown_player"
    assert est.confidence <= 0.15
    assert est.rating == 0.50
    assert "neutral_rating_low_confidence" in est.notes


def test_low_minutes_player_has_reduced_confidence():
    high = resolve_composable_transfer_estimate(1001, 384)
    low = resolve_composable_transfer_estimate(1005, 384)
    assert low.confidence < high.confidence
    assert "low_sample_minutes" in low.notes


def test_cross_league_note():
    est = resolve_composable_transfer_estimate(1006, 384, role="forward")
    assert "known_player_unknown_target_league" in est.notes


def test_confidence_grows_with_target_matches():
    low = resolve_composable_transfer_estimate(1006, 384, target_matches_played=0)
    high = resolve_composable_transfer_estimate(1006, 384, target_matches_played=15)
    assert high.confidence >= low.confidence


def test_output_stable_and_bounded():
    est = resolve_composable_transfer_estimate(1006, 384, role="forward")
    assert est.rating == est.rating
    assert 0.0 <= est.rating <= 1.0
    assert 0.0 <= est.confidence <= 1.0


def test_cli_transfer_estimate_fw_role():
    from src.cli import main

    code = main(
        ["transfer-estimate", "--player-id", "1006", "--target-league", "384", "--role", "FW", "--json"]
    )
    assert code == 0


def test_cli_unknown_player_json(capsys):
    from src.cli import main

    code = main(
        ["transfer-estimate", "--player-id", "99999", "--target-league", "384", "--json"]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"] == "unknown_player"
    assert payload["rating"] == 0.50
    assert payload["confidence"] <= 0.15
    assert "unknown_player" in payload["notes"]
