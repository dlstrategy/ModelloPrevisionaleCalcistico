from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.advanced_strength import compute_advanced_strength
from src.features.match_context import build_match_context
from src.features.shots_features import get_team_shots_profile
from src.features.xg_features import get_team_xg_profile
from src.prediction.explain import explain_prediction
from src.prediction.predict_match import predict_match
from src.models.feature_model import FeatureModel


def test_advanced_strength_fields():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.is_finished)
    strength = compute_advanced_strength(dataset, match.home.team_id, match.starting_at, settings)
    assert strength.attack_rating > 0
    assert strength.rolling_5_strength is not None


def test_xg_profile_rolling():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.is_finished)
    profile = get_team_xg_profile(dataset, match.home.team_id, match.starting_at, 384)
    assert profile.xg_for_avg > 0
    assert profile.rolling_xg_diff_5 is not None


def test_shots_profile():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if m.is_finished)
    profile = get_team_shots_profile(dataset, match.home.team_id, match.starting_at, 384)
    assert profile.shots_for_avg > 0
    assert profile.xg_per_shot > 0


def test_explain_includes_edges():
    from dataclasses import replace

    settings = replace(load_settings(), data_profile="advanced")
    dataset = load_offline_dataset(384)
    upcoming = next(m for m in dataset.matches if not m.is_finished)
    model = FeatureModel()
    pred = predict_match(dataset, upcoming, model, settings)
    ctx = build_match_context(dataset, upcoming, settings)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=settings)
    assert "edges" in explanation
    assert "xg" in explanation["edges"]
    assert "model_contributions" in explanation
    assert "probabilities" in explanation
    assert "data_sources" in explanation
    assert "data_profile" in explanation
    assert "data_completeness" in explanation
    assert explanation["data_profile"] == "advanced"
    assert explanation["data_sources"]["player_lineup"] == "mock_fixture"
    assert explanation["data_sources"]["tactical"] == "mock_fixture"
    assert explanation["data_sources"]["xg"] == "mock_fixture_historical"
    assert explanation["data_sources"]["shots"] == "mock_fixture_historical"
