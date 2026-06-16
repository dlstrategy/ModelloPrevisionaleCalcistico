"""Test feature coach."""

import math
from dataclasses import replace

import pytest

from src.config import load_settings
from src.coaches.coach_registry import get_team_coach_profile
from src.data_pipeline.sync import load_offline_dataset
from src.features.coach_features import (
    COACH_FEATURE_KEYS,
    build_coach_features,
    build_coach_summary,
)
from src.features.feature_groups import FEATURE_GROUPS, filter_feature_vector
from src.features.match_context import build_match_context
from src.models.registry import get_model_by_name
from src.prediction.explain import explain_prediction
from src.prediction.predict_match import predict_match
from src.training.feature_policy import COMPACT_COACH_DIFF, select_features_for_policy, parse_feature_policy
from src.training.dataset import build_training_samples


def _match(dataset, match_id: int = 1001):
    return next(m for m in dataset.matches if m.id == match_id)


def test_features_finite():
    dataset = load_offline_dataset(384)
    match = _match(dataset)
    features = build_coach_features(match)
    assert set(features.keys()) == COACH_FEATURE_KEYS
    for value in features.values():
        assert math.isfinite(value)


def test_unknown_coach_neutral():
    dataset = load_offline_dataset(384)
    match = _match(dataset, 1006)
    features = build_coach_features(match)
    assert features["home_unknown_coach"] == 1.0 or features["away_unknown_coach"] == 1.0
    unknown_side = "home" if features["home_unknown_coach"] == 1.0 else "away"
    assert features[f"{unknown_side}_coach_potential_signal"] == 0.5
    assert features[f"{unknown_side}_coach_data_confidence"] <= 0.15


def test_recent_coach_change():
    coach = get_team_coach_profile(2, 384)
    assert coach.matches_in_charge < 5
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.home.team_id == 2 or m.away.team_id == 2)
    features = build_coach_features(match)
    side = "home" if match.home.team_id == 2 else "away"
    assert features[f"{side}_recent_coach_change"] == 1.0
    assert features[f"{side}_new_manager_bounce_signal"] > 0
    assert features[f"{side}_new_manager_bounce_signal"] <= 0.20


def test_low_sample_coach():
    coach = get_team_coach_profile(7, 384)
    assert coach.matches_in_charge < 10 or coach.career_matches < 30
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.home.team_id == 7 or m.away.team_id == 7)
    features = build_coach_features(match)
    side = "home" if match.home.team_id == 7 else "away"
    assert features[f"{side}_low_sample_coach"] == 1.0
    assert features[f"{side}_coach_data_confidence"] <= 0.30


def test_defense_orientation():
    coach = get_team_coach_profile(9, 384)
    assert coach.goals_against_delta is not None and coach.goals_against_delta < 0
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.home.team_id == 9 or m.away.team_id == 9)
    features = build_coach_features(match)
    side = "home" if match.home.team_id == 9 else "away"
    assert features[f"{side}_coach_defense_delta"] > 0
    assert features[f"{side}_coach_xga_delta"] > 0


def test_tactical_stability_low_when_many_changes():
    coach = get_team_coach_profile(8, 384)
    assert coach.formation_changes_last_10 is not None and coach.formation_changes_last_10 >= 8
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.home.team_id == 8 or m.away.team_id == 8)
    features = build_coach_features(match)
    side = "home" if match.home.team_id == 8 else "away"
    assert features[f"{side}_coach_tactical_stability"] < 0.25


def test_style_fit_insufficient_data_neutral():
    dataset = load_offline_dataset(384)
    match = _match(dataset)
    features = build_coach_features(match)
    assert 0.0 <= features["home_coach_style_fit"] <= 1.0
    assert features["home_coach_style_fit_confidence"] <= 0.70


def test_potential_signal_positive_for_stable_coach():
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.home.team_id == 1 or m.away.team_id == 1)
    features = build_coach_features(match)
    side = "home" if match.home.team_id == 1 else "away"
    assert features[f"{side}_coach_potential_signal"] > 0.5


def test_feature_group_disabled():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    match = _match(dataset)
    ctx = build_match_context(dataset, match, settings, profile="base")
    coach_keys = FEATURE_GROUPS["coach"]
    assert not any(k in ctx.feature_vector for k in coach_keys)


def test_feature_group_enabled_advanced():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    match = _match(dataset)
    ctx = build_match_context(dataset, match, settings, profile="advanced")
    coach_keys = FEATURE_GROUPS["coach"]
    present = sum(1 for k in coach_keys if k in ctx.feature_vector)
    assert present == len(coach_keys)


def test_compact_policy_coach_diff_only():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    compact, _ = select_features_for_policy(samples, parse_feature_policy("compact"))
    coach_in_compact = [n for n in compact if n.startswith("coach_") or n.startswith("unknown_coach") or n.startswith("low_sample_coach")]
    for name in coach_in_compact:
        assert name in COMPACT_COACH_DIFF
    assert "home_coach_ppg_delta" not in compact
    assert "away_coach_tenure_norm" not in compact


def test_explain_coach_summary():
    settings = replace(load_settings(), data_profile="advanced")
    dataset = load_offline_dataset(384)
    match = _match(dataset)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, settings)
    ctx = build_match_context(dataset, match, settings)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=settings)
    assert "coach_summary" in explanation
    assert "home" in explanation["coach_summary"]
    assert "away" in explanation["coach_summary"]
    for side in ("home", "away"):
        assert "style_fit_confidence" in explanation["coach_summary"][side]
        assert "style_fit_notes" in explanation["coach_summary"][side]
        assert "adaptation_notes" in explanation["coach_summary"][side]
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}


def test_prediction_output_invariant():
    settings = replace(load_settings(), data_profile="advanced")
    dataset = load_offline_dataset(384)
    match = _match(dataset)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, settings)
    assert hasattr(pred, "pick")
    assert hasattr(pred, "confidence")
    probs = pred.probabilities.as_dict()
    assert abs(sum(probs.values()) - 1.0) < 1e-6
