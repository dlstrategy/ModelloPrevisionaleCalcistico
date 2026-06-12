"""Test walk-forward refit per feature_trained."""

import json

import pytest

from src.backtesting.walk_forward import save_walk_forward_report
from src.backtesting.walk_forward_trained import TRAINING_MODE_REFIT, run_walk_forward_refit
from src.config import load_settings
from src.data_pipeline.sync import sync_league_data


@pytest.fixture(scope="module")
def synced():
    settings = load_settings()
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def test_walk_forward_refit_training_mode(synced, settings):
    report = run_walk_forward_refit(
        synced,
        settings,
        profile="advanced",
        min_train_matches=10,
        test_window_size=5,
        step_size=5,
    )
    assert report.training_mode == TRAINING_MODE_REFIT
    assert report.model_name == "feature_trained"
    assert report.data_profile == "advanced"
    assert len(report.windows) >= 1


def test_walk_forward_refit_test_not_in_train_samples(synced, settings):
    report = run_walk_forward_refit(
        synced,
        settings,
        profile="advanced",
        min_train_matches=10,
        test_window_size=5,
        step_size=5,
    )
    finished = sorted(
        [m for m in synced.matches if m.is_finished and m.actual_outcome],
        key=lambda m: m.starting_at,
    )
    window = report.windows[0]
    train_ids = {m.id for m in finished[: window.train_matches]}
    test_ids = {p.fixture_id for p in window.predictions}
    assert train_ids.isdisjoint(test_ids)


def test_walk_forward_refit_window_metadata(synced, settings, tmp_path):
    report = run_walk_forward_refit(synced, settings, profile="advanced")
    window = report.windows[0]
    assert window.train_from is not None
    assert window.training_features is not None
    assert window.training_features > 0
    assert window.training_warnings is not None

    json_path, _ = save_walk_forward_report(report, tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["training_mode"] == "walk_forward_refit"
    assert payload["data_profile"] == "advanced"
    assert "training_features" in payload["windows"][0]


def test_walk_forward_refit_probabilities_normalized(synced, settings):
    report = run_walk_forward_refit(synced, settings, profile="advanced")
    for window in report.windows:
        for pred in window.predictions:
            total = pred.probabilities.home + pred.probabilities.draw + pred.probabilities.away
            assert abs(total - 1.0) < 1e-4


def test_walk_forward_cli_feature_trained(synced):
    from src.cli import main

    code = main(
        ["walk-forward", "--league", "384", "--model", "feature_trained", "--profile", "advanced"]
    )
    assert code == 0
