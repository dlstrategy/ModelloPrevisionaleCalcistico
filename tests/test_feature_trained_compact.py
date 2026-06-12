"""Test feature_trained compact training, artifact metadata, walk-forward."""

import json

import pytest

from src.backtesting.walk_forward_trained import run_walk_forward_refit
from src.cli import main
from src.cli_train import print_train
from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset, sync_league_data
from src.features.match_context import build_match_context
from src.models.feature_trained import FeatureTrainedModel
from src.models.registry import get_model_by_name
from src.prediction.predict_match import predict_match
from src.training.artifacts import (
    load_feature_trained_artifact,
    load_feature_trained_artifact_from_dict,
    save_feature_trained_artifact,
)
from src.training.dataset import build_training_samples
from src.training.feature_policy import count_features_for_policy
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model


@pytest.fixture(scope="module")
def synced():
    settings = load_settings()
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def test_full_vs_compact_feature_counts(settings):
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    full_count, original = count_features_for_policy(samples, "full")
    compact_count, _ = count_features_for_policy(samples, "compact")
    assert full_count == original
    assert compact_count < full_count


def test_compact_artifact_metadata(tmp_path, monkeypatch, settings):
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    from src.training.feature_policy import (
        apply_feature_policy_to_sample,
        parse_feature_policy,
        select_features_for_policy,
    )

    policy = parse_feature_policy("compact")
    selected, sel_warnings = select_features_for_policy(samples, policy)
    filtered = [apply_feature_policy_to_sample(s, selected) for s in samples]
    artifact = train_softmax_model(
        filtered,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=20, min_samples=5, l2=0.005, clip_value=5.0),
        feature_names=selected,
        feature_policy="compact",
        original_feature_count=len(selected) + 10,
        feature_selection_warnings=tuple(sel_warnings),
    )
    save_feature_trained_artifact(artifact)
    loaded = load_feature_trained_artifact(384)
    assert loaded.feature_policy == "compact"
    assert loaded.selected_feature_count == len(selected)
    assert loaded.clip_value == 5.0


def test_legacy_artifact_loads_without_policy_fields():
    payload = {
        "model_name": "feature_trained",
        "model_version": "2g.1",
        "league_id": 384,
        "data_profile": "advanced",
        "feature_names": ["home_attack", "away_attack"],
        "scaler_means": {"home_attack": 1.0, "away_attack": 1.0},
        "scaler_stds": {"home_attack": 1.0, "away_attack": 1.0},
        "weights": {"HOME": [0.1, 0.0], "DRAW": [0.0, 0.0], "AWAY": [0.0, 0.1]},
        "bias": {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0},
        "training_matches": 10,
        "created_at": "2025-01-01T00:00:00+00:00",
        "training_config": {"learning_rate": 0.05, "epochs": 10, "l2": 0.001, "min_samples": 5},
        "warnings": [],
        "training_algorithm": "softmax_regression_python",
    }
    artifact = load_feature_trained_artifact_from_dict(payload)
    assert artifact.feature_policy == "full"
    assert artifact.selected_feature_count == 2
    assert artifact.original_feature_count == 2
    assert artifact.clip_value is None


def test_legacy_artifact_predicts(settings):
    payload = {
        "model_name": "feature_trained",
        "model_version": "2g.1",
        "league_id": 384,
        "data_profile": "advanced",
        "feature_names": ["home_attack", "away_attack"],
        "scaler_means": {"home_attack": 1.0, "away_attack": 1.0},
        "scaler_stds": {"home_attack": 1.0, "away_attack": 1.0},
        "weights": {"HOME": [0.5, -0.2], "DRAW": [0.0, 0.0], "AWAY": [-0.5, 0.2]},
        "bias": {"HOME": 0.1, "DRAW": 0.0, "AWAY": -0.1},
        "training_matches": 10,
        "created_at": "2025-01-01T00:00:00+00:00",
        "training_config": {"learning_rate": 0.05, "epochs": 10, "l2": 0.001, "min_samples": 5},
    }
    artifact = load_feature_trained_artifact_from_dict(payload)
    dataset = load_offline_dataset(384)
    model = FeatureTrainedModel.from_artifact(settings, dataset, artifact)
    ctx = build_match_context(dataset, dataset.matches[0], settings, profile="advanced")
    probs = model.predict(ctx)
    total = probs.home + probs.draw + probs.away
    assert abs(total - 1.0) < 1e-6


def test_train_cli_compact(tmp_path, monkeypatch, synced, settings):
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    code = print_train(
        settings,
        384,
        profile="advanced",
        feature_policy="compact",
    )
    assert code == 0
    loaded = load_feature_trained_artifact(384)
    assert loaded.feature_policy == "compact"
    assert loaded.selected_feature_count < loaded.original_feature_count


def test_walk_forward_compact_metadata(synced, settings):
    report = run_walk_forward_refit(
        synced,
        settings,
        profile="advanced",
        feature_policy="compact",
        min_train_matches=10,
        test_window_size=5,
        step_size=5,
    )
    assert len(report.windows) >= 1
    window = report.windows[0]
    assert window.feature_policy == "compact"
    assert window.original_feature_count is not None
    assert window.training_features is not None
    assert window.training_features <= window.original_feature_count
    assert window.training_l2 == 0.005
    assert window.clip_value == 5.0


def test_walk_forward_train_test_disjoint_raises(settings):
    from src.backtesting.walk_forward_trained import _ensure_disjoint_train_test

    with pytest.raises(ValueError, match="leakage"):
        _ensure_disjoint_train_test(frozenset({1, 2}), frozenset({2, 3}))


def test_compact_predict_output_unchanged(tmp_path, monkeypatch, synced, settings):
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    print_train(settings, 384, profile="advanced", feature_policy="compact")
    model = get_model_by_name("feature_trained", settings, synced)
    upcoming = next(m for m in synced.matches if not m.is_finished)
    pred = predict_match(synced, upcoming, model, settings)
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}
    assert pred.pick.value in {"1", "X", "2"}


def test_feature_trained_not_in_all_models_backtest(settings, synced):
    from src.backtesting.backtest import run_backtest_all_models

    results = run_backtest_all_models(synced, settings, max_matches=5)
    names = {r.model_name for r in results}
    assert "feature_trained" not in names


def test_train_module_compact_flag(synced, tmp_path, monkeypatch):
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    code = main(
        [
            "train",
            "--league",
            "384",
            "--model",
            "feature_trained",
            "--profile",
            "advanced",
            "--feature-policy",
            "compact",
        ]
    )
    assert code == 0
    payload = json.loads((tmp_path / "feature_trained_384.json").read_text(encoding="utf-8"))
    assert payload["feature_policy"] == "compact"
