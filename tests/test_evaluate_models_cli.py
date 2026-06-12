"""Test CLI evaluate-models e report JSON."""

import json
from pathlib import Path

import pytest

from src.cli import main
from src.cli_evaluate import print_evaluate_models
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


def test_evaluate_models_exit_zero(synced, settings, tmp_path, monkeypatch):
    monkeypatch.setattr("src.backtesting.model_evaluation.BACKTESTS_DIR", tmp_path)
    code = print_evaluate_models(settings, 384, profile="advanced")
    assert code == 0
    reports = list(tmp_path.glob("model_evaluation_*.json"))
    assert len(reports) == 1
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["baseline"]["feature_policy"] == "full"
    assert payload["candidate"]["feature_policy"] == "compact"
    assert payload["promotion_decision"]["status"] in {"promoted", "rejected", "inconclusive"}


def test_evaluate_models_json_stdout(synced, settings, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("src.backtesting.model_evaluation.BACKTESTS_DIR", tmp_path)
    code = main(["evaluate-models", "--league", "384", "--profile", "advanced", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "promotion_decision" in payload
    assert "baseline" in payload
    assert "candidate" in payload


def test_evaluate_models_include_ensemble(synced, settings, tmp_path, monkeypatch):
    monkeypatch.setattr("src.backtesting.model_evaluation.BACKTESTS_DIR", tmp_path)
    code = print_evaluate_models(
        settings,
        384,
        profile="advanced",
        include_ensemble_baseline=True,
    )
    assert code == 0
    payload = json.loads(list(tmp_path.glob("model_evaluation_*.json"))[0].read_text())
    assert "ensemble" in payload["informational_baselines"]
    assert "not directly equivalent" in payload["informational_baselines"]["ensemble"]["note"]


def test_evaluate_models_does_not_change_artifact(synced, settings, tmp_path, monkeypatch):
    from src.cli_train import print_train

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    print_train(settings, 384, profile="advanced", feature_policy="full")
    before = (tmp_path / "feature_trained_384.json").read_text(encoding="utf-8")
    monkeypatch.setattr("src.backtesting.model_evaluation.BACKTESTS_DIR", tmp_path / "reports")
    print_evaluate_models(settings, 384, profile="advanced")
    after = (tmp_path / "feature_trained_384.json").read_text(encoding="utf-8")
    assert before == after


def test_predict_output_unchanged(synced, settings, tmp_path, monkeypatch):
    from src.cli_train import print_train

    monkeypatch.setattr("src.training.artifacts.MODELS_DIR", tmp_path)
    monkeypatch.setattr("src.config.MODELS_DIR", tmp_path)
    print_train(settings, 384, profile="advanced")
    model = get_model_by_name("feature_trained", settings, synced)
    upcoming = next(m for m in synced.matches if not m.is_finished)
    pred = predict_match(synced, upcoming, model, settings)
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}
    assert pred.pick.value in {"1", "X", "2"}


def test_feature_trained_not_in_all_models(settings, synced):
    from src.backtesting.backtest import run_backtest_all_models

    results = run_backtest_all_models(synced, settings, max_matches=5)
    assert "feature_trained" not in {r.model_name for r in results}
