from src.backtesting.ablation import run_ablation_study
from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.feature_groups import ABLATION_VARIANTS, keys_for_groups
from src.features.match_context import build_match_context


def test_feature_vector_has_all_groups_when_full():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    match = dataset.matches[0]
    ctx = build_match_context(dataset, match, settings)
    full_keys = keys_for_groups(ABLATION_VARIANTS["full"])
    assert len(ctx.feature_vector) >= len(full_keys) * 0.9


def test_ablation_variants_run():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    results = run_ablation_study(dataset, settings, max_matches=10)
    assert len(results) == len(ABLATION_VARIANTS)
    for result in results:
        assert result.metrics.samples == 10
        assert result.feature_count > 0


def test_ablation_full_has_more_features_than_base():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    results = {r.variant: r for r in run_ablation_study(dataset, settings, max_matches=5)}
    assert results["full"].feature_count > results["base"].feature_count
