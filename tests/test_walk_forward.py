import json
from pathlib import Path

import pytest

from src.backtesting.walk_forward import run_walk_forward, save_walk_forward_report
from src.config import BACKTESTS_DIR, load_settings
from src.data_pipeline.sync import load_offline_dataset, sync_league_data
from src.features.match_context import build_match_context
from src.models.registry import get_model_by_name


@pytest.fixture(scope="module")
def settings():
    return load_settings()


@pytest.fixture(scope="module")
def dataset(settings):
    sync_league_data(settings, 384)
    return load_offline_dataset(384)


def test_walk_forward_generates_windows(dataset, settings):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(dataset, model, settings)
    assert len(report.windows) >= 1
    assert report.total_tested_matches > 0


def test_walk_forward_default_params_match_spec(dataset, settings):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(
        dataset,
        model,
        settings,
        min_train_matches=10,
        test_window_size=5,
        step_size=5,
    )
    assert len(report.windows) == 6
    assert report.total_tested_matches == 30


def test_walk_forward_uses_kickoff_as_as_of(dataset, settings):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(dataset, model, settings, min_train_matches=10, test_window_size=1, step_size=5)
    window = report.windows[0]
    match = next(m for m in dataset.matches if m.id == window.predictions[0].fixture_id)
    ctx = build_match_context(dataset, match, settings, as_of=match.starting_at)
    assert ctx.as_of == match.starting_at


def test_walk_forward_no_future_in_history(dataset, settings):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(dataset, model, settings)
    for window in report.windows:
        for pred in window.predictions:
            match = next(m for m in dataset.matches if m.id == pred.fixture_id)
            history = dataset.team_history(match.home.team_id, match.starting_at)
            assert all(m.starting_at < match.starting_at for m in history)
            assert all(m.id != match.id for m in history)


def test_walk_forward_aggregate_metrics_present(dataset, settings):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(dataset, model, settings)
    m = report.aggregate_metrics
    assert m.samples == report.total_tested_matches
    assert 0.0 <= m.accuracy <= 1.0
    assert m.brier_score >= 0.0
    assert hasattr(m, "mean_calibration_gap")


def test_walk_forward_probabilities_sum_to_one(dataset, settings):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(dataset, model, settings)
    for window in report.windows:
        for pred in window.predictions:
            total = pred.probabilities.home + pred.probabilities.draw + pred.probabilities.away
            assert abs(total - 1.0) < 1e-4


def test_walk_forward_saves_json_and_csv(dataset, settings, tmp_path):
    model = get_model_by_name("ensemble", settings, dataset)
    report = run_walk_forward(dataset, model, settings)
    json_path, csv_path = save_walk_forward_report(report, tmp_path)
    assert json_path.exists()
    assert csv_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["aggregate_metrics"]["samples"] == report.total_tested_matches
    assert "windows" in payload
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert "window_index" in header
    assert "p_home" in header


def test_walk_forward_cli_entrypoint(dataset):
    from src.cli import main

    code = main(["walk-forward", "--league", "384", "--model", "ensemble"])
    assert code == 0
    json_path = BACKTESTS_DIR / "walk_forward_ensemble_384.json"
    assert json_path.exists()
