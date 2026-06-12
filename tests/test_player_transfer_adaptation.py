"""Test adattamento rating giocatore tra leghe."""

import pytest

from src.players.global_registry import get_player_snapshot_for_league
from src.players.player_value import resolve_player_value_for_league
from src.players.transfer_adaptation import adapt_player_rating


def test_same_league_no_penalty():
    snap = get_player_snapshot_for_league(1001, 384)
    assert snap is not None
    adj = adapt_player_rating(snap, target_league_id=384)
    assert adj.transferred_rating == snap.rating
    assert adj.confidence == snap.sample_confidence
    assert adj.source == "same_league"


def test_liga_to_serie_a_coefficient():
    snap = get_player_snapshot_for_league(1002, 564)
    assert snap is not None
    adj = adapt_player_rating(snap, target_league_id=384, target_matches_played=0)
    assert adj.transferred_rating == pytest.approx(snap.rating * 0.95, rel=1e-4)
    assert adj.confidence < snap.sample_confidence
    assert adj.source == "league_coefficient_table"


def test_unknown_league_fallback():
    snap = get_player_snapshot_for_league(1003, 999)
    assert snap is not None
    adj = adapt_player_rating(snap, target_league_id=384, target_matches_played=0)
    assert adj.transferred_rating == pytest.approx(snap.rating * 0.85, rel=1e-4)
    assert adj.source == "unknown_league_transfer"
    assert "default_transfer_coefficient" in adj.notes


def test_confidence_grows_with_target_matches():
    snap = get_player_snapshot_for_league(1002, 564)
    assert snap is not None
    low = adapt_player_rating(snap, target_league_id=384, target_matches_played=0)
    high = adapt_player_rating(snap, target_league_id=384, target_matches_played=15)
    assert high.confidence > low.confidence


def test_rating_finite_and_bounded():
    snap = get_player_snapshot_for_league(1005, 384)
    assert snap is not None
    adj = adapt_player_rating(snap, target_league_id=564, target_matches_played=3)
    assert 0.0 <= adj.transferred_rating <= 10.0
    assert 0.0 <= adj.confidence <= 1.0


def test_resolve_player_value_unknown_player():
    value = resolve_player_value_for_league(99999, 384)
    assert value["source"] == "unknown_player"
    assert value["confidence"] <= 0.15


def test_resolve_player_value_no_betting_keys():
    value = resolve_player_value_for_league(1002, 384, target_matches_played=5)
    forbidden = {"over_under", "odds", "handicap", "correct_score", "btts"}
    assert forbidden.isdisjoint(value.keys())
