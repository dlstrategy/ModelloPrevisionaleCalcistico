"""Test warning in-sample per backtest feature_trained."""

import io
import json
from contextlib import redirect_stdout

import pytest

from src.backtesting.backtest import IN_SAMPLE_ARTIFACT_WARNING, run_backtest, save_report
from src.cli_train import print_train
from src.config import load_settings
from src.data_pipeline.sync import sync_league_data
from src.models.registry import get_model_by_name


@pytest.fixture(scope="module")
def synced():
    settings = load_settings()
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


@pytest.fixture(scope="module")
def trained(synced, settings):
    print_train(settings, 384, model_name="feature_trained", profile="advanced")
    return synced


def test_backtest_feature_trained_in_sample_metadata(trained, settings):
    model = get_model_by_name("feature_trained", settings, trained)
    assert model.is_ready()
    result = run_backtest(trained, model, settings, max_matches=10)
    assert result.evaluation_mode == "in_sample_artifact"
    assert result.training_leakage_risk is True
    assert result.warning == IN_SAMPLE_ARTIFACT_WARNING


def test_backtest_json_includes_leakage_warning(trained, settings, tmp_path):
    model = get_model_by_name("feature_trained", settings, trained)
    result = run_backtest(trained, model, settings, max_matches=5)
    json_path, _ = save_report(result, tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["evaluation_mode"] == "in_sample_artifact"
    assert payload["training_leakage_risk"] is True
    assert "warning" in payload


def test_backtest_cli_prints_in_sample_warning(trained, settings):
    from src.cli import main

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["backtest", "--league", "384", "--model", "feature_trained", "--rounds", "5"])
    output = buf.getvalue()
    assert code == 0
    assert "Evaluation mode: in_sample_artifact" in output
    assert "WARNING:" in output
    assert "walk-forward refit" in output
