"""Test composable transfer resolver."""

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


def test_uncovered_pair_uses_general_adapter():
    est = resolve_composable_transfer_estimate(1003, 384)
    assert est.adapter_type == "general_adapter"
    assert est.source_league_id == 999


def test_unknown_player_fallback():
    est = resolve_composable_transfer_estimate(99999, 384)
    assert est.adapter_type == "unknown_player"
    assert est.confidence <= 0.15
    assert est.rating == 0.50


def test_confidence_grows_with_target_matches():
    low = resolve_composable_transfer_estimate(1006, 384, target_matches_played=0)
    high = resolve_composable_transfer_estimate(1006, 384, target_matches_played=15)
    assert high.confidence >= low.confidence


def test_output_stable_and_bounded():
    est = resolve_composable_transfer_estimate(1006, 384, role="forward")
    assert est.rating == est.rating
    assert 0.0 <= est.rating <= 1.0
    assert 0.0 <= est.confidence <= 1.0
