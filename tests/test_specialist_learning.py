"""Test specialist learning offline."""

import pytest

from src.players.specialist_learning import (
    LEARNED_VERSION,
    TransferOutcomeObservation,
    aggregate_observations,
    compute_transfer_error,
    learn_pair_specialist_from_observations,
    load_transfer_outcomes,
)


def test_load_outcomes():
    obs = load_transfer_outcomes()
    assert len(obs) >= 6


def test_compute_transfer_error():
    obs = TransferOutcomeObservation(
        player_id=1,
        source_league_id=564,
        target_league_id=384,
        role="forward",
        predicted_rating=0.70,
        observed_rating_after_transfer=0.66,
        matches_observed=10,
        minutes_observed=800,
    )
    assert compute_transfer_error(obs) == pytest.approx(-0.04)


def test_ignores_insufficient_observations():
    obs = load_transfer_outcomes()
    buckets = aggregate_observations(obs)
    for group in buckets.values():
        for item in group:
            assert item.is_sufficient


def test_learn_pair_specialist():
    obs = load_transfer_outcomes()
    learned = learn_pair_specialist_from_observations(564, 384, "forward", obs)
    assert learned is not None
    assert learned.source_league_id == 564
    assert learned.target_league_id == 384
    assert learned.learned_version == LEARNED_VERSION
    assert 0.75 <= learned.rating_multiplier <= 1.15
    assert 0.0 <= learned.reliability <= 1.0


def test_learned_directional():
    obs = load_transfer_outcomes()
    forward = learn_pair_specialist_from_observations(564, 384, "forward", obs)
    reverse = learn_pair_specialist_from_observations(384, 564, "forward", obs)
    assert forward is not None
    assert reverse is None


def test_no_division_by_zero():
    obs = [
        TransferOutcomeObservation(
            player_id=1,
            source_league_id=1,
            target_league_id=2,
            role=None,
            predicted_rating=0.0,
            observed_rating_after_transfer=0.5,
            matches_observed=10,
            minutes_observed=900,
        )
    ]
    assert learn_pair_specialist_from_observations(1, 2, None, obs) is None


def test_insufficient_single_observation():
    obs = [
        TransferOutcomeObservation(
            player_id=1,
            source_league_id=564,
            target_league_id=384,
            role="forward",
            predicted_rating=0.7,
            observed_rating_after_transfer=0.65,
            matches_observed=2,
            minutes_observed=100,
        )
    ]
    assert learn_pair_specialist_from_observations(564, 384, "forward", obs) is None
