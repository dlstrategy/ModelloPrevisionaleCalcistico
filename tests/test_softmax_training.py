"""Test scaler e softmax training."""

import math

import pytest

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.training.dataset import TrainingSample, build_training_samples
from src.training.softmax import (
    CLASSES,
    SoftmaxTrainingConfig,
    fit_scaler,
    predict_proba_from_artifact,
    train_softmax_model,
    transform_features,
)


def test_scaler_zero_std_becomes_one():
    samples = [
        TrainingSample(1, "2025-01-01", "HOME", {"a": 1.0, "b": 2.0}),
        TrainingSample(2, "2025-01-02", "AWAY", {"a": 1.0, "b": 4.0}),
    ]
    scaler = fit_scaler(samples, ["a", "b"])
    assert scaler.stds["a"] == 1.0
    vec = transform_features({"a": 1.0, "b": 3.0}, ["a", "b"], scaler)
    assert len(vec) == 2
    assert all(math.isfinite(v) for v in vec)


def test_softmax_probs_sum_to_one():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=50, min_samples=5),
    )
    sample = samples[0]
    home, draw, away = predict_proba_from_artifact(artifact, sample.features)
    total = home + draw + away
    assert abs(total - 1.0) < 1e-6


def test_training_produces_artifact_structure():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=30, min_samples=5),
    )
    assert artifact.feature_names
    assert set(artifact.weights.keys()) == set(CLASSES)
    assert set(artifact.bias.keys()) == set(CLASSES)
    assert len(artifact.weights["HOME"]) == len(artifact.feature_names)
    assert artifact.training_matches == len(samples)


def test_training_warns_on_small_dataset():
    samples = [
        TrainingSample(i, f"2025-01-{i:02d}", label, {"f": float(i)})
        for i, label in enumerate(["HOME", "DRAW", "AWAY", "HOME", "AWAY"], start=1)
    ]
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="base",
        config=SoftmaxTrainingConfig(min_samples=20, epochs=10),
    )
    assert any("dataset piccolo" in w for w in artifact.warnings)


def test_training_fails_single_class():
    samples = [
        TrainingSample(1, "2025-01-01", "HOME", {"f": 1.0}),
        TrainingSample(2, "2025-01-02", "HOME", {"f": 2.0}),
        TrainingSample(3, "2025-01-03", "HOME", {"f": 3.0}),
    ]
    with pytest.raises(ValueError, match="2 classi"):
        train_softmax_model(samples, league_id=384, data_profile="base")
