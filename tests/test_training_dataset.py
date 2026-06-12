"""Test build_training_samples."""

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.feature_groups import FEATURE_GROUPS
from src.training.dataset import build_training_samples


def test_build_training_samples_finished_only():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    assert len(samples) >= 10
    finished_ids = {m.id for m in dataset.matches if m.is_finished and m.actual_outcome}
    assert all(s.fixture_id in finished_ids for s in samples)


def test_training_sample_as_of_and_label():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="base")
    match_by_id = {m.id: m for m in dataset.matches}
    for sample in samples[:5]:
        match = match_by_id[sample.fixture_id]
        assert sample.as_of == match.starting_at.isoformat()
        assert sample.label in {"HOME", "DRAW", "AWAY"}
        assert sample.features


def test_base_profile_excludes_xg_features():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="base")
    assert samples
    all_keys = set()
    for s in samples:
        all_keys.update(s.features.keys())
    xg_keys = FEATURE_GROUPS["xg"]
    assert not any(k in all_keys for k in xg_keys)


def test_advanced_profile_includes_xg_features():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    samples = build_training_samples(dataset, settings, profile="advanced")
    assert samples
    all_keys = set()
    for s in samples:
        all_keys.update(s.features.keys())
    xg_keys = FEATURE_GROUPS["xg"]
    assert any(k in all_keys for k in xg_keys)
