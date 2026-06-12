"""Test transfer-aware lineup features."""

import math

import pytest

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.domain.enums import ParticipantLocation
from src.domain.match import Match, MatchParticipant
from src.features.feature_groups import FEATURE_GROUPS, filter_feature_vector
from src.features.lineup_features import get_fixture_lineup_row
from src.features.match_context import build_match_context
from src.features.transfer_lineup_features import (
    TRANSFER_LINEUP_FEATURE_KEYS,
    build_transfer_lineup_features,
    build_transfer_lineup_summary,
    extract_lineup_player_ids,
)
from src.prediction.predict_match import predict_match
from src.models.registry import get_model_by_name


def _finished_match(dataset, match_id: int = 1001) -> Match:
    return next(m for m in dataset.matches if m.id == match_id)


def test_features_are_finite():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)
    features = build_transfer_lineup_features(match)
    assert set(features.keys()) == TRANSFER_LINEUP_FEATURE_KEYS
    for value in features.values():
        assert math.isfinite(value)


def test_unknown_player_lowers_confidence():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)

    def resolve(pid, league, **kwargs):
        if pid == 99999:
            return {
                "player_id": pid,
                "rating": 0.50,
                "confidence": 0.10,
                "source": "unknown_player",
                "source_league_id": None,
                "target_league_id": league,
                "specialist_key": None,
                "notes": ["unknown_player"],
            }
        from src.players.player_value import resolve_player_value_for_league

        return resolve_player_value_for_league(pid, league)

    features = build_transfer_lineup_features(
        match,
        away_player_ids=[1001, 99999],
        resolve=resolve,
    )
    pure = build_transfer_lineup_features(match, away_player_ids=[1001], resolve=resolve)
    assert features["away_lineup_unknown_player_share"] > 0
    assert features["away_lineup_transfer_avg_confidence"] < pure["away_lineup_transfer_avg_confidence"]


def test_low_sample_increases_share():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)
    low = build_transfer_lineup_features(match, home_player_ids=[1005])
    high = build_transfer_lineup_features(match, home_player_ids=[1001])
    assert low["home_lineup_low_sample_player_share"] > high["home_lineup_low_sample_player_share"]
    assert low["home_lineup_transfer_avg_confidence"] <= 0.30


def test_cross_league_and_pair_specialist_shares():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)
    features = build_transfer_lineup_features(match, home_player_ids=[1006])
    assert features["home_lineup_cross_league_player_share"] > 0
    assert features["home_lineup_pair_specialist_share"] > 0


def test_general_adapter_when_no_specialist():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)
    features = build_transfer_lineup_features(match, home_player_ids=[1003])
    assert features["home_lineup_cross_league_player_share"] > 0
    assert features["home_lineup_general_adapter_share"] > 0
    assert features["home_lineup_pair_specialist_share"] == 0.0


def test_missing_lineup_neutral():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset, match_id=1001)
    features = build_transfer_lineup_features(match, home_player_ids=[], away_player_ids=[])
    assert features["home_lineup_transfer_avg_rating"] == 0.50
    assert features["home_lineup_transfer_avg_confidence"] <= 0.15
    assert features["home_lineup_transfer_missing_player_share"] == 1.0


def test_diff_in_range():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)
    features = build_transfer_lineup_features(
        match,
        home_player_ids=[1001, 1006],
        away_player_ids=[1002, 99999],
    )
    for key in (
        "lineup_transfer_rating_diff",
        "lineup_transfer_confidence_diff",
        "lineup_unknown_player_share_diff",
    ):
        assert -1.0 <= features[key] <= 1.0


def test_feature_group_filtering():
    from src.features.feature_groups import ALL_GROUPS

    dataset = load_offline_dataset(384)
    settings = load_settings()
    match = _finished_match(dataset)
    without_lineup = ALL_GROUPS - frozenset({"player_lineup"})
    disabled_ctx = build_match_context(
        dataset, match, settings, enabled_feature_groups=without_lineup
    )
    adv_ctx = build_match_context(dataset, match, settings, profile="advanced")
    disabled_keys = set(disabled_ctx.feature_vector.keys()) & TRANSFER_LINEUP_FEATURE_KEYS
    adv_keys = set(adv_ctx.feature_vector.keys()) & TRANSFER_LINEUP_FEATURE_KEYS
    assert len(disabled_keys) == 0
    assert len(adv_keys) == len(TRANSFER_LINEUP_FEATURE_KEYS)


def test_fixture_player_ids_extracted():
    row = get_fixture_lineup_row(384, 1001)
    assert row is not None
    home_ids = extract_lineup_player_ids(row, "home")
    assert 1006 in home_ids
    assert 1005 in home_ids


def test_predict_output_unchanged():
    dataset = load_offline_dataset(384)
    settings = load_settings()
    match = next(m for m in dataset.matches if not m.is_finished)
    model = get_model_by_name("poisson", settings, dataset)
    pred = predict_match(dataset, match, model, settings)
    assert hasattr(pred.probabilities, "home")
    assert pred.pick.value in {"1", "X", "2"}
    assert 0.0 <= pred.confidence <= 1.0
    payload = {
        "home": pred.probabilities.home,
        "draw": pred.probabilities.draw,
        "away": pred.probabilities.away,
        "pick": pred.pick.value,
        "confidence": pred.confidence,
    }
    assert set(payload.keys()) == {"home", "draw", "away", "pick", "confidence"}


def test_summary_for_explain():
    dataset = load_offline_dataset(384)
    match = _finished_match(dataset)
    summary = build_transfer_lineup_summary(match)
    assert "home" in summary
    assert "away" in summary
    assert summary["source"] == "mock_player_career_registry"
