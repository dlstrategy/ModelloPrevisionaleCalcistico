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
    future = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, future, settings)
    sources = build_data_sources(ctx, settings)
    assert sources["xg"] == "mock_fixture_historical"
    assert sources["shots"] == "mock_fixture_historical"
    assert sources["calendar"] == "historical+mock_fixture"
    assert sources["base"] == "historical"


def test_api_mode_companion_not_marked_as_api(settings, dataset):
    api_settings = replace(
        settings,
        api_token="test-token",
        enable_sportmonks_sync=True,
    )
    assert api_settings.can_sync_api

    future = next(m for m in dataset.matches if not m.is_finished)
    ctx = build_match_context(dataset, future, api_settings)
    sources = build_data_sources(ctx, api_settings)

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
    sources = build_data_sources(ctx, api_settings)

    assert sources["player_lineup"] == "mock_fixture_not_api"
    assert sources["tactical"] == "mock_fixture_not_api"
    assert sources["player_lineup"] != "api"
    assert sources["tactical"] != "api"
