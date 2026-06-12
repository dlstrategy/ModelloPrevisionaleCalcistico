"""Test CLI train e predict feature_trained."""

import io
from contextlib import redirect_stdout

import pytest

from src.cli import main
from src.cli_train import print_train
from src.config import MODELS_DIR, load_settings
from src.data_pipeline.sync import sync_league_data
from src.models.registry import get_model_by_name
from src.prediction.predict_match import predict_match


@pytest.fixture(scope="module")
def synced():
    settings = load_settings()
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def test_train_cli_exit_zero(synced, settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_train(settings, 384, model_name="feature_trained", profile="advanced")
    output = buf.getvalue()
    assert code == 0
    assert "Training feature_trained" in output
    assert "Profile: advanced" in output
    assert "Saved:" in output
    assert (MODELS_DIR / "feature_trained_384.json").exists()


def test_train_module_entrypoint(synced):
    code = main(
        ["train", "--league", "384", "--model", "feature_trained", "--profile", "advanced"]
    )
    assert code == 0


def test_train_invalid_model(settings, synced):
    code = print_train(settings, 384, model_name="poisson")
    assert code == 1


def test_predict_after_train(synced, settings):
    print_train(settings, 384, model_name="feature_trained", profile="advanced")
    dataset = synced
    model = get_model_by_name("feature_trained", settings, dataset)
    assert model.is_ready()
    upcoming = next(m for m in dataset.matches if not m.is_finished)
    pred = predict_match(dataset, upcoming, model, settings)
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}
    assert pred.pick.value in {"1", "X", "2"}
    assert 0 < pred.confidence <= 1
