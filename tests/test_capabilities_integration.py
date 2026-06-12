"""Integrazione capability layer con status, validate, predict explain."""

import io
import json
from contextlib import redirect_stdout
from dataclasses import replace

import pytest

from src.cli import main
from src.cli_status import print_status
from src.cli_validate import print_validate
from src.config import QUALITY_DIR, load_settings
from src.data_pipeline.sync import load_offline_dataset, sync_league_data
from src.features.match_context import build_match_context
from src.models.feature_model import FeatureModel
from src.prediction.explain import explain_prediction
from src.prediction.predict_match import predict_match


@pytest.fixture(scope="module")
def synced():
    settings = load_settings()
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def test_status_shows_data_profile(synced, settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_status(settings, 384)
    output = buf.getvalue()
    assert code == 0
    assert "Data profile:" in output
    assert "Data completeness:" in output
    assert "Policy disabled:" in output


def test_validate_base_profile_passes(synced, settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_validate(settings, 384, profile="base")
    output = buf.getvalue()
    assert code == 0
    assert "Data profile: base" in output
    assert "Data completeness score:" in output
    assert "Status: PASSED" in output


def test_validate_json_includes_data_completeness(synced, settings):
    print_validate(settings, 384, profile="base")
    payload = json.loads((QUALITY_DIR / "quality_384_latest.json").read_text(encoding="utf-8"))
    assert payload["data_profile"] == "base"
    assert "data_completeness" in payload
    assert "score" in payload["data_completeness"]


def test_predict_explain_includes_data_completeness(settings):
    advanced = replace(settings, data_profile="advanced")
    dataset = load_offline_dataset(384)
    upcoming = next(m for m in dataset.matches if not m.is_finished)
    model = FeatureModel()
    pred = predict_match(dataset, upcoming, model, advanced)
    ctx = build_match_context(dataset, upcoming, advanced)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=advanced)

    assert explanation["data_profile"] == "advanced"
    dc = explanation["data_completeness"]
    assert "score" in dc
    assert "enabled_feature_groups" in dc
    assert "policy_disabled_capabilities" in dc
    assert "PREDICTIONS" in dc["policy_disabled_capabilities"]
    assert "probabilities" in explanation
    assert "pick" in explanation
    assert set(explanation["probabilities"].keys()) == {"home", "draw", "away"}


def test_validate_cli_with_profile_flag(synced):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["validate", "--league", "384", "--profile", "base"])
    assert code == 0
    assert "Data profile: base" in buf.getvalue()
