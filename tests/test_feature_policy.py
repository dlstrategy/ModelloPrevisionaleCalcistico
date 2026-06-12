"""Test feature policy full vs compact."""

import pytest

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.transfer_lineup_features import TRANSFER_LINEUP_FEATURE_KEYS
from src.training.dataset import build_training_samples
from src.training.feature_policy import (
    COMPACT_TRANSFER_DIFF,
    apply_feature_policy_to_sample,
    available_feature_policies,
    collect_feature_names,
    parse_feature_policy,
    select_features_for_policy,
)


@pytest.fixture
def advanced_samples():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    return build_training_samples(dataset, settings, profile="advanced")


def test_parse_policy_full_and_compact():
    assert parse_feature_policy("full").name == "full"
    assert parse_feature_policy("compact").name == "compact"
    assert parse_feature_policy(None).name == "full"


def test_parse_invalid_policy_raises():
    with pytest.raises(ValueError, match="Feature policy non valida"):
        parse_feature_policy("invalid")


def test_available_policies():
    policies = available_feature_policies()
    assert set(policies) == {"full", "compact"}


def test_full_keeps_all_features(advanced_samples):
    policy = parse_feature_policy("full")
    original = collect_feature_names(advanced_samples)
    selected, warnings = select_features_for_policy(advanced_samples, policy)
    assert selected == original
    assert warnings == []


def test_compact_selects_fewer_than_full(advanced_samples):
    full = select_features_for_policy(advanced_samples, parse_feature_policy("full"))[0]
    compact = select_features_for_policy(advanced_samples, parse_feature_policy("compact"))[0]
    assert len(compact) < len(full)
    assert len(compact) >= 20


def test_compact_includes_robust_groups(advanced_samples):
    compact, _ = select_features_for_policy(advanced_samples, parse_feature_policy("compact"))
    assert "home_attack" in compact
    assert "home_xg_for_avg" in compact
    assert "home_shots_for_avg" in compact
    assert "days_rest_home" in compact
    assert "home_relegation_pressure" in compact


def test_compact_excludes_per_side_transfer_features(advanced_samples):
    compact, warnings = select_features_for_policy(advanced_samples, parse_feature_policy("compact"))
    assert "home_lineup_transfer_avg_rating" not in compact
    assert "away_lineup_unknown_player_share" not in compact
    assert "home_lineup_pair_specialist_share" not in compact
    transfer_in_compact = [n for n in compact if n in TRANSFER_LINEUP_FEATURE_KEYS]
    for name in transfer_in_compact:
        assert name in COMPACT_TRANSFER_DIFF


def test_compact_includes_transfer_diff_when_informative():
    from src.training.dataset import TrainingSample

    samples = [
        TrainingSample(
            i,
            f"2025-01-{i:02d}",
            "HOME",
            {
                "home_attack": float(i),
                "lineup_transfer_rating_diff": float(i) * 0.01,
                "lineup_transfer_confidence_diff": float(i) * 0.02,
                "lineup_unknown_player_share_diff": float(i) * 0.03,
            },
        )
        for i in range(1, 21)
    ]
    compact, _ = select_features_for_policy(samples, parse_feature_policy("compact"))
    assert "lineup_transfer_rating_diff" in compact
    assert "lineup_transfer_confidence_diff" in compact


def test_apply_feature_policy_to_sample(advanced_samples):
    compact, _ = select_features_for_policy(advanced_samples, parse_feature_policy("compact"))
    sample = advanced_samples[0]
    filtered = apply_feature_policy_to_sample(sample, compact)
    assert set(filtered.features.keys()) == set(compact)
    assert "home_attack" in filtered.features
