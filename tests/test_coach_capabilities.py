"""Test capability layer per gruppo coach."""

from dataclasses import replace

import pytest

from src.config import load_settings
from src.data_capabilities.capabilities import DataCapability
from src.data_capabilities.resolver import detect_available_capabilities, resolve_capabilities
from src.data_pipeline.sync import load_offline_dataset
from src.features.data_sources import build_data_sources
from src.features.match_context import build_match_context


@pytest.fixture
def dataset():
    return load_offline_dataset(384)


@pytest.fixture
def settings():
    return load_settings()


def test_coach_profiles_detected(dataset):
    caps = detect_available_capabilities(384, dataset)
    assert DataCapability.COACH_PROFILES in caps


def test_base_profile_disables_coach(settings, dataset):
    resolution = resolve_capabilities(settings, 384, dataset, profile="base")
    assert "coach" in resolution.disabled_feature_groups
    assert "coach" not in resolution.enabled_feature_groups


def test_advanced_profile_enables_coach(settings, dataset):
    resolution = resolve_capabilities(settings, 384, dataset, profile="advanced")
    assert "coach" in resolution.enabled_feature_groups


def test_all_in_enables_coach(settings, dataset):
    resolution = resolve_capabilities(settings, 384, dataset, profile="all_in_no_predictions")
    assert "coach" in resolution.enabled_feature_groups


def test_data_sources_coach_mock(settings, dataset):
    advanced = replace(settings, data_profile="advanced")
    match = next(m for m in dataset.matches if m.id == 1001)
    ctx = build_match_context(dataset, match, advanced)
    sources = build_data_sources(ctx, advanced, dataset)
    assert sources["coach"] in {"mock_coach_profiles", "fallback"}


def test_data_sources_coach_disabled_base(settings, dataset):
    match = next(m for m in dataset.matches if m.id == 1001)
    ctx = build_match_context(dataset, match, settings)
    sources = build_data_sources(ctx, settings, dataset)
    assert sources["coach"] == "disabled"
