from src.backtesting.backtest import run_backtest_all_models
from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset


def test_backtest_all_models_runs():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    results = run_backtest_all_models(dataset, settings, max_matches=5)
    assert len(results) == 5
    for r in results:
        assert r.metrics.samples == 5
