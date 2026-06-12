"""Test feature importance da pesi softmax."""

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.training.dataset import build_training_samples
from src.training.feature_importance import (
    compute_feature_importance,
    save_feature_importance,
    top_feature_importance,
)
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model


def test_importance_sorted_descending():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=40, min_samples=5),
    )
    rows = compute_feature_importance(artifact)
    assert len(rows) == len(artifact.feature_names)
    importances = [row["importance"] for row in rows]
    assert importances == sorted(importances, reverse=True)
    assert all("feature_name" in row for row in rows)


def test_top_feature_importance_length():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=20, min_samples=5),
    )
    top = top_feature_importance(artifact, n=5)
    assert len(top) == 5
    assert top[0]["importance"] >= top[-1]["importance"]


def test_save_importance_json(tmp_path, monkeypatch):
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=20, min_samples=5),
    )
    monkeypatch.setattr("src.training.feature_importance.MODELS_DIR", tmp_path)
    path = save_feature_importance(artifact)
    assert path.exists()
    assert path.name.endswith("_importance.json")
