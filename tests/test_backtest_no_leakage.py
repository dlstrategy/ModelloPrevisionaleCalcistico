from datetime import datetime

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.recent_form import compute_team_form
from src.models.poisson import PoissonModel
from src.backtesting.backtest import run_backtest


def test_team_history_excludes_current_and_future_matches():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    inter_finished = [
        m for m in dataset.matches
        if m.is_finished and any(p.team_id == 1 for p in m.participants)
    ]
    inter_finished.sort(key=lambda m: m.starting_at)
    target = inter_finished[2]
    as_of = target.starting_at

    inter_form = compute_team_form(dataset, team_id=1, as_of=as_of, settings=settings)
    assert inter_form.matches_played > 0
    assert inter_form.matches_played <= settings.form_window_matches


def test_backtest_runs_offline():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    model = PoissonModel(settings)
    result = run_backtest(dataset, model, settings, max_matches=3)
    assert result.metrics.samples == 3
    assert 0.0 <= result.metrics.accuracy <= 1.0
