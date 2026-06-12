"""Test Data Capability Layer — profili, resolver, completeness."""

from dataclasses import replace

import pytest

from src.config import load_settings
from src.data_capabilities.capabilities import (
    POLICY_DISABLED_CAPABILITIES,
    DataCapability,
)
from src.data_capabilities.profiles import profile_capabilities
from src.data_capabilities.resolver import parse_data_profile, resolve_capabilities
from src.data_pipeline.sync import load_offline_dataset


def test_base_profile_capabilities():
    caps = profile_capabilities("base")
    assert DataCapability.CORE_FIXTURES in caps
    assert DataCapability.STANDINGS in caps
    assert DataCapability.TEAM_STATS in caps
    assert DataCapability.PLAYER_STATS in caps
    assert DataCapability.CALENDAR in caps
    assert DataCapability.XG not in caps
    assert DataCapability.PRESSURE_INDEX not in caps
    assert DataCapability.EXPECTED_LINEUPS not in caps
    assert DataCapability.TACTICAL_DATA not in caps
    assert DataCapability.NEWS not in caps


def test_advanced_profile_includes_xg_and_shots():
    caps = profile_capabilities("advanced")
    assert DataCapability.XG in caps
    assert DataCapability.SHOTS in caps
    assert DataCapability.TACTICAL_DATA in caps
    assert DataCapability.PRESSURE_INDEX not in caps


def test_all_in_no_predictions_excludes_predictions_and_odds():
    caps = profile_capabilities("all_in_no_predictions")
    assert DataCapability.PRESSURE_INDEX in caps
    assert DataCapability.EXPECTED_LINEUPS in caps
    assert DataCapability.NEWS in caps
    assert DataCapability.PREDICTIONS not in caps
    assert DataCapability.ODDS not in caps


def test_invalid_profile_raises():
    with pytest.raises(ValueError, match="DATA_PROFILE non valido"):
        parse_data_profile("invalid_profile")


def test_resolver_base_disables_xg_and_shots():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    resolution = resolve_capabilities(settings, 384, dataset, profile="base")

    assert "xg" in resolution.disabled_feature_groups
    assert "shots" in resolution.disabled_feature_groups
    assert "base" in resolution.enabled_feature_groups
    assert "calendar" in resolution.enabled_feature_groups
    assert set(resolution.policy_disabled_capabilities) == {
        DataCapability.PREDICTIONS.value,
        DataCapability.ODDS.value,
    }


def test_resolver_advanced_enables_xg():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    resolution = resolve_capabilities(settings, 384, dataset, profile="advanced")

    assert "xg" in resolution.enabled_feature_groups
    assert "shots" in resolution.enabled_feature_groups


def test_completeness_score_in_range():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    for profile in ("base", "advanced", "all_in_no_predictions"):
        resolution = resolve_capabilities(settings, 384, dataset, profile=profile)
        score = resolution.completeness.score
        assert 0.0 <= score <= 1.0


def test_base_profile_not_penalized_for_missing_xg():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    base = resolve_capabilities(settings, 384, dataset, profile="base")
    assert "XG" not in base.missing_capabilities
    assert base.completeness.score >= 0.85


def test_fallback_lineup_tactical_registered():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    resolution = resolve_capabilities(settings, 384, dataset, profile="base")
    fallback_text = " ".join(resolution.fallbacks)
    assert "player_lineup" in fallback_text or "tactical" in fallback_text or resolution.fallbacks


def test_policy_disabled_never_in_available():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    resolution = resolve_capabilities(settings, 384, dataset, profile="all_in_no_predictions")
    for cap in POLICY_DISABLED_CAPABILITIES:
        assert cap.value not in resolution.completeness.available_capabilities
