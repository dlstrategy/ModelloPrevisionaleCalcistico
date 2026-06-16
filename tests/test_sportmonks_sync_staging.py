"""Test sync staging con mapper avanzati (Fase 3b)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings
from src.data_pipeline.sportmonks_mapper_wiring import (
    BASE_FIXTURE_INCLUDES,
    build_fixture_includes,
)
from src.data_pipeline.sync import _sync_from_api, load_offline_dataset
from src.models.registry import build_base_models, build_ensemble
from src.prediction.predict_match import predict_match

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sportmonks"
FAKE_TOKEN = "staging-sync-test-token-not-real"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _combined_fixture_list_payload() -> dict:
    stats = _load("fixture_statistics_sample.json")
    lineups = _load("fixture_lineups_sample.json")
    coaches = _load("fixture_coaches_sample.json")
    fixture = dict(stats["data"])
    for key in ("lineups", "lineups_confirmed", "formations"):
        if key in lineups["data"]:
            fixture[key] = lineups["data"][key]
    if "coaches" in coaches["data"]:
        fixture["coaches"] = coaches["data"]["coaches"]
    return {"data": [fixture]}


def _offline_settings(**overrides) -> Settings:
    base = Settings(
        api_token=None,
        base_url="https://api.sportmonks.com/v3/football",
        default_league_id=384,
        enable_sportmonks_sync=False,
        enable_sportmonks_advanced_mappers=False,
        cache_ttl_fixtures=3600,
        cache_ttl_standings=86400,
        cache_ttl_teams=86400,
        form_window_matches=5,
        form_weight=0.7,
        season_weight=0.3,
        home_advantage=1.12,
        poisson_max_goals=5,
        dixon_coles_rho=-0.13,
        elo_k_factor=20.0,
        elo_home_advantage=65.0,
        elo_initial_rating=1500.0,
        min_confidence_threshold=0.38,
        calibration_temperature=1.0,
        ensemble_weight_poisson=0.35,
        ensemble_weight_dixon_coles=0.30,
        ensemble_weight_elo=0.20,
        ensemble_weight_feature=0.15,
        log_level="INFO",
        offline_mode="auto",
        data_profile="base",
    )
    return replace(base, **overrides)


def _api_settings(advanced: bool = False) -> Settings:
    return _offline_settings(
        api_token=FAKE_TOKEN,
        enable_sportmonks_sync=True,
        enable_sportmonks_advanced_mappers=advanced,
    )


def test_advanced_flag_false_uses_base_includes():
    settings = _offline_settings()
    assert settings.can_use_advanced_mappers is False
    assert build_fixture_includes(settings.can_use_advanced_mappers) == BASE_FIXTURE_INCLUDES


def test_advanced_flag_false_mappers_not_called():
    settings = _api_settings(advanced=False)
    combined = _combined_fixture_list_payload()

    with (
        patch("src.data_pipeline.sync.leagues_api.fetch_league") as mock_league,
        patch("src.data_pipeline.sync.fixtures_api.fetch_fixtures_between") as mock_fixtures,
        patch("src.data_pipeline.sync.apply_mappers_to_sync_payloads") as mock_map,
        patch("src.data_pipeline.sync.write_companion_artifacts") as mock_write,
        patch("src.sportmonks.client.SportmonksClient.get") as mock_get,
    ):
        mock_league.return_value = {"data": {"currentseason": {"id": 25000}}}
        mock_fixtures.return_value = combined
        dataset = _sync_from_api(settings, 384)

        assert mock_fixtures.call_count == 2
        for call in mock_fixtures.call_args_list:
            assert call.kwargs.get("includes") == BASE_FIXTURE_INCLUDES
        mock_map.assert_not_called()
        mock_write.assert_not_called()
        mock_get.assert_not_called()
    assert dataset.league_id == 384
    assert len(dataset.matches) >= 1


def test_advanced_flag_true_uses_advanced_includes():
    settings = _api_settings(advanced=True)
    combined = _combined_fixture_list_payload()
    standings = _load("standings_season_sample.json")

    with (
        patch("src.data_pipeline.sync.leagues_api.fetch_league") as mock_league,
        patch("src.data_pipeline.sync.fixtures_api.fetch_fixtures_between") as mock_fixtures,
        patch("src.data_pipeline.sync.standings_api.fetch_standings_by_season") as mock_standings,
        patch("src.data_pipeline.sync.apply_mappers_to_sync_payloads") as mock_map,
        patch("src.data_pipeline.sync.write_companion_artifacts") as mock_write,
        patch("src.sportmonks.client.SportmonksClient.get"),
    ):
        mock_league.return_value = {"data": {"currentseason": {"id": 25000}}}
        mock_fixtures.return_value = combined
        mock_standings.return_value = standings
        mock_map.return_value = MagicMock(warnings=())
        mock_write.return_value = []

        _sync_from_api(settings, 384)

        for call in mock_fixtures.call_args_list:
            includes = call.kwargs.get("includes")
            assert "statistics" in includes
            assert "lineups" in includes
        mock_map.assert_called_once()
        mock_write.assert_called_once()


def test_mapper_failure_does_not_break_base_dataset(tmp_path):
    settings = _api_settings(advanced=True)
    combined = _combined_fixture_list_payload()

    with (
        patch("src.data_pipeline.sync.leagues_api.fetch_league") as mock_league,
        patch("src.data_pipeline.sync.fixtures_api.fetch_fixtures_between") as mock_fixtures,
        patch("src.data_pipeline.sync.apply_mappers_to_sync_payloads") as mock_map,
        patch("src.data_pipeline.sync.companions_dir_for_league", return_value=tmp_path),
        patch("src.sportmonks.client.SportmonksClient.get"),
    ):
        mock_league.return_value = {"data": {"currentseason": {"id": 25000}}}
        mock_fixtures.return_value = combined
        mock_map.side_effect = RuntimeError("mapper exploded")

        dataset = _sync_from_api(settings, 384)

    assert dataset.matches
    assert FAKE_TOKEN not in str(dataset)


def test_no_real_api_in_sync_staging_tests():
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        settings = _api_settings(advanced=True)
        combined = _combined_fixture_list_payload()
        with (
            patch("src.data_pipeline.sync.leagues_api.fetch_league") as mock_league,
            patch("src.data_pipeline.sync.fixtures_api.fetch_fixtures_between") as mock_fixtures,
            patch("src.data_pipeline.sync.standings_api.fetch_standings_by_season") as mock_standings,
            patch("src.data_pipeline.sync.apply_mappers_to_sync_payloads") as mock_map,
            patch("src.data_pipeline.sync.write_companion_artifacts") as mock_write,
        ):
            mock_league.return_value = {"data": {"currentseason": {"id": 25000}}}
            mock_fixtures.return_value = combined
            mock_standings.return_value = _load("standings_season_sample.json")
            mock_map.return_value = MagicMock(warnings=())
            mock_write.return_value = []
            _sync_from_api(settings, 384)
        mock_get.assert_not_called()


def test_offline_dataset_prediction_unchanged():
    settings = _offline_settings()
    dataset = load_offline_dataset(384)
    match = next(m for m in dataset.matches if not m.is_finished)
    from src.models.registry import get_model_by_name

    model = get_model_by_name("ensemble", settings, dataset)
    pred = predict_match(dataset, match, model, settings)
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}
    assert pred.pick.value in {"1", "X", "2"}


def test_feature_trained_outside_ensemble():
    settings = _offline_settings()
    dataset = load_offline_dataset(384)
    base_names = {m.name for m in build_base_models(settings, dataset)}
    assert "feature_trained" not in base_names
    ensemble = build_ensemble(settings, dataset)
    assert all(m.name != "feature_trained" for m in ensemble._models)
