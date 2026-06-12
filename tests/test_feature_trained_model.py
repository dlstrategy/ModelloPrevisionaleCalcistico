"""Test FeatureTrainedModel e artifact."""

import pytest

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.match_context import build_match_context
from src.models.feature_trained import FeatureTrainedModel
from src.training.artifacts import (
    load_feature_trained_artifact,
    model_artifact_path,
    save_feature_trained_artifact,
)
from src.training.dataset import build_training_samples
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model


@pytest.fixture
def trained_artifact(tmp_path, monkeypatch):
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=30, min_samples=5),
    )
    from src.config import MODELS_DIR

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    save_feature_trained_artifact(artifact)
    return artifact


def test_artifact_path():
    path = model_artifact_path(384)
    assert path.name == "feature_trained_384.json"


def test_save_load_roundtrip(trained_artifact, tmp_path, monkeypatch):
    from src.config import MODELS_DIR

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    loaded = load_feature_trained_artifact(384)
    assert loaded.feature_names == trained_artifact.feature_names
    assert loaded.weights == trained_artifact.weights
    assert loaded.bias == trained_artifact.bias
    assert loaded.data_profile == "advanced"


def test_model_not_ready_without_artifact(tmp_path, monkeypatch):
    from src.config import MODELS_DIR

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    settings = load_settings()
    dataset = load_offline_dataset(384)
    model = FeatureTrainedModel(settings, dataset)
    assert model.is_ready() is False
    with pytest.raises(RuntimeError, match="feature_trained non trovato"):
        model.predict(
            build_match_context(dataset, dataset.matches[0], settings, profile="advanced")
        )


def test_model_predict_normalized(trained_artifact, tmp_path, monkeypatch):
    from src.config import MODELS_DIR

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    settings = load_settings()
    dataset = load_offline_dataset(384)
    model = FeatureTrainedModel(settings, dataset)
    assert model.is_ready()
    upcoming = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, upcoming, settings, profile="advanced")
    probs = model.predict(ctx)
    total = probs.home + probs.draw + probs.away
    assert abs(total - 1.0) < 1e-6


def test_missing_features_do_not_crash(trained_artifact, tmp_path, monkeypatch):
    from src.config import MODELS_DIR

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    settings = load_settings()
    dataset = load_offline_dataset(384)
    model = FeatureTrainedModel(settings, dataset)
    upcoming = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, upcoming, settings, profile="advanced")
    sparse = {k: v for k, v in ctx.feature_vector.items() if not k.startswith("home_xg")}
    from dataclasses import replace

    sparse_ctx = replace(ctx, feature_vector=sparse)
    probs = model.predict(sparse_ctx)
    assert probs.home >= 0
