from dataclasses import replace

import pytest

from src.config import Settings, load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.data_sources import build_data_sources
from src.features.match_context import build_match_context


@pytest.fixture(scope="module")
def settings():
    return load_settings()


@pytest.fixture(scope="module")
def dataset():
    return load_offline_dataset(384)


def test_offline_xg_and_shots_sources(settings, dataset):
    from dataclasses import replace

    advanced = replace(settings, data_profile="advanced")
    future = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, future, advanced)
    sources = build_data_sources(ctx, advanced, dataset)
    assert sources["xg"] == "mock_fixture_historical"
    assert sources["shots"] == "mock_fixture_historical"
    assert sources["calendar"] == "historical+mock_fixture"
    assert sources["base"] == "historical"


def test_base_profile_disables_xg_shots_sources(settings, dataset):
    future = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, future, settings)
    sources = build_data_sources(ctx, settings, dataset)
    assert "disabled" in sources["xg"]
    assert "disabled" in sources["shots"]


def test_api_mode_companion_not_marked_as_api(settings, dataset):
    from dataclasses import replace

    api_settings = replace(
        settings,
        api_token="test-token",
        enable_sportmonks_sync=True,
        data_profile="advanced",
    )
    assert api_settings.can_sync_api

    future = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, future, api_settings)
    sources = build_data_sources(ctx, api_settings, dataset)

    assert sources["base"] == "api_base"
    assert sources["xg"] == "api_not_connected_yet"
    assert sources["shots"] == "api_not_connected_yet"
    assert sources["calendar"] == "api_not_connected_yet"
    assert sources["xg"] != "api"
    assert sources["shots"] != "api"


def test_api_mode_mock_lineup_tactical_explicit(settings, dataset):
    api_settings = replace(
        settings,
        api_token="test-token",
        enable_sportmonks_sync=True,
    )
    future = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, future, api_settings)
    sources = build_data_sources(ctx, api_settings, dataset)

    assert sources["player_lineup"] == "mock_fixture_not_api"
    assert sources["tactical"] == "mock_fixture_not_api"
    assert sources["player_lineup"] != "api"
    assert sources["tactical"] != "api"
