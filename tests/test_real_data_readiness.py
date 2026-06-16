"""Test audit prontezza dati reali (Fase 2m)."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from dataclasses import replace
from unittest.mock import patch

import pytest

from src.backtesting.backtest import run_backtest_all_models
from src.cli_readiness import print_readiness, readiness_output_safe
from src.config import load_settings
from src.data_capabilities.capabilities import POLICY_DISABLED_CAPABILITIES
from src.data_capabilities.requirements import ALL_FEATURE_GROUPS
from src.data_pipeline.readiness import (
    OVERALL_PARTIAL,
    build_real_data_readiness_report,
    readiness_report_as_dict,
)
from src.data_pipeline.sync import load_offline_dataset
from src.features.feature_groups import FEATURE_GROUPS
from src.models.registry import build_base_models, build_ensemble
from src.models.registry import MODEL_NAMES
from src.prediction.predict_match import predict_match
from src.training.feature_policy import VALID_POLICIES


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def dataset():
    return load_offline_dataset(384)


def test_readiness_report_does_not_call_api(settings):
    with patch("src.sportmonks.client.SportmonksClient.get") as mock_get:
        report = build_real_data_readiness_report(settings, 384, profile="advanced")
        mock_get.assert_not_called()
    assert report.league_id == 384
    assert report.profile == "advanced"


def test_overall_status_partial_ready(settings):
    report = build_real_data_readiness_report(settings, 384, profile="advanced")
    assert report.overall_status == OVERALL_PARTIAL


def test_predictions_odds_policy_disabled(settings):
    report = build_real_data_readiness_report(settings, 384)
    policy_items = [i for i in report.items if i.area == "policy_predictions_odds"]
    assert policy_items
    assert policy_items[0].status == "ready"
    assert {c.value for c in POLICY_DISABLED_CAPABILITIES} == {"PREDICTIONS", "ODDS"}


def test_coach_mapping_doc_present(settings):
    report = build_real_data_readiness_report(settings, 384)
    doc_items = [i for i in report.items if i.area == "coach_mapping_doc"]
    assert doc_items and doc_items[0].status == "ready"


def test_feature_groups_include_coach():
    assert "coach" in ALL_FEATURE_GROUPS
    assert "coach" in FEATURE_GROUPS
    assert len(FEATURE_GROUPS["coach"]) > 0


def test_compact_policy_present():
    assert VALID_POLICIES == frozenset({"full", "compact"})


def test_promotion_gate_present(settings):
    report = build_real_data_readiness_report(settings, 384)
    gate = [i for i in report.items if i.area == "promotion_gate"]
    assert gate and gate[0].status == "ready"


def test_cli_readiness_exit_code_zero(settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_readiness(settings, 384, profile="advanced")
    assert code == 0
    assert "PARTIAL_READY" in buf.getvalue()


def test_json_readiness_serializable(settings):
    report = build_real_data_readiness_report(settings, 384, profile="advanced")
    payload = readiness_report_as_dict(report)
    text = json.dumps(payload)
    parsed = json.loads(text)
    assert parsed["overall_status"] == OVERALL_PARTIAL
    assert "blocking" in parsed
    assert "warnings" in parsed


def test_token_not_in_readiness_output(settings):
    fake_token = "super-secret-test-token-xyz"
    s = replace(settings, api_token=fake_token, enable_sportmonks_sync=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        print_readiness(s, 384, profile="advanced", as_json=True)
    output = buf.getvalue()
    assert fake_token not in output
    assert readiness_output_safe(output, s)


def test_prediction_output_unchanged(dataset, settings):
    from src.models.registry import get_model_by_name

    match = next(m for m in dataset.matches if not m.is_finished)
    model = get_model_by_name("ensemble", settings, dataset)
    pred = predict_match(dataset, match, model, settings)
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}
    assert pred.pick.value in {"1", "X", "2"}
    assert 0.0 < pred.confidence <= 1.0


def test_mapper_offline_items_present(settings):
    report = build_real_data_readiness_report(settings, 384, profile="advanced")
    areas = {i.area for i in report.items}
    assert "mapper_offline_xg" in areas
    assert "sync_wiring_xg" in areas
    assert "advanced_mapper_flag" in areas
    mapper_xg = next(i for i in report.items if i.area == "mapper_offline_xg")
    assert mapper_xg.status == "partial"
    sync_xg = next(i for i in report.items if i.area == "sync_wiring_xg")
    assert sync_xg.status == "partial"
    adv_flag = next(i for i in report.items if i.area == "advanced_mapper_flag")
    assert adv_flag.status == "ready"


def test_feature_trained_outside_ensemble_and_all_models(dataset, settings):
    base_names = {m.name for m in build_base_models(settings, dataset)}
    assert "feature_trained" not in base_names
    ensemble = build_ensemble(settings, dataset)
    assert all(m.name != "feature_trained" for m in ensemble._models)
    results = run_backtest_all_models(dataset, settings, max_matches=3)
    assert "feature_trained" not in {r.model_name for r in results}
    assert "feature_trained" in MODEL_NAMES
