"""Test isolamento artifact feature_trained per lega."""

import pytest

from src.config import load_settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_pipeline.sync import load_offline_dataset
from src.models.feature_trained import FeatureTrainedModel
from src.training.artifacts import (
    ArtifactLeagueMismatchError,
    artifact_league_mismatch_message,
    load_feature_trained_artifact,
    save_feature_trained_artifact,
)
from src.training.dataset import build_training_samples
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model


@pytest.fixture
def artifact_league_384(tmp_path, monkeypatch):
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    artifact = train_softmax_model(
        samples,
        league_id=384,
        data_profile="advanced",
        config=SoftmaxTrainingConfig(epochs=20, min_samples=5),
    )
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    save_feature_trained_artifact(artifact)
    return artifact


def test_load_artifact_validates_expected_league(tmp_path, monkeypatch, artifact_league_384):
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    with pytest.raises(ArtifactLeagueMismatchError, match="artifact league 384, dataset league 564"):
        load_feature_trained_artifact(384, expected_league_id=564)


def test_model_rejects_wrong_league_artifact(tmp_path, monkeypatch, artifact_league_384):
    import json
    from dataclasses import asdict

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    # Artifact Serie A salvato sotto path Liga (contaminazione simulata)
    wrong_path = tmp_path / "feature_trained_564.json"
    payload = asdict(artifact_league_384)
    wrong_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    settings = load_settings()
    base = load_offline_dataset(384)
    dataset = MatchDataset(league_id=564, season_id=base.season_id, matches=base.matches)
    model = FeatureTrainedModel(settings, dataset)
    assert model.is_ready() is False
    with pytest.raises(RuntimeError, match="artifact league 384, dataset league 564"):
        from src.features.match_context import build_match_context

        model.predict(
            build_match_context(dataset, dataset.matches[0], settings, profile="advanced")
        )


def test_from_artifact_rejects_mismatch(artifact_league_384):
    settings = load_settings()
    base = load_offline_dataset(384)
    dataset = MatchDataset(league_id=564, season_id=base.season_id, matches=base.matches)
    with pytest.raises(ArtifactLeagueMismatchError):
        FeatureTrainedModel.from_artifact(settings, dataset, artifact_league_384)


def test_correct_league_still_works(tmp_path, monkeypatch, artifact_league_384):
    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    settings = load_settings()
    dataset = load_offline_dataset(384)
    model = FeatureTrainedModel(settings, dataset)
    assert model.is_ready() is True


def test_feature_trained_not_in_all_models():
    from src.backtesting.backtest import run_backtest_all_models
    from src.config import load_settings
    from src.data_pipeline.sync import load_offline_dataset

    settings = load_settings()
    dataset = load_offline_dataset(384)
    results = run_backtest_all_models(dataset, settings, max_matches=3)
    names = {r.model_name for r in results}
    assert "feature_trained" not in names
    assert len(results) == 5
