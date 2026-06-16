"""Test hardening explain coach (Fase 2l-b)."""

from dataclasses import replace

import pytest

from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.coach_features import build_coach_summary
from src.features.match_context import build_match_context
from src.models.registry import get_model_by_name
from src.prediction.explain import explain_prediction
from src.prediction.predict_match import predict_match


STYLE_FIT_WARNING = (
    "Coach style fit insufficient data — compatibilità stile/rosa non certa"
)


def _match(dataset, match_id: int = 1001):
    return next(m for m in dataset.matches if m.id == match_id)


@pytest.fixture
def dataset():
    return load_offline_dataset(384)


@pytest.fixture
def settings():
    return load_settings()


def test_coach_summary_fields_advanced(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = _match(dataset)
    ctx = build_match_context(dataset, match, advanced)
    summary = build_coach_summary(match, tactical=ctx.tactical)
    for side in ("home", "away"):
        entry = summary[side]
        assert "style_fit_confidence" in entry
        assert "style_fit_notes" in entry
        assert "adaptation_notes" in entry
        assert isinstance(entry["style_fit_notes"], list)
        assert isinstance(entry["adaptation_notes"], list)


def test_explain_coach_summary_present(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = _match(dataset)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, advanced)
    ctx = build_match_context(dataset, match, advanced)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=advanced)
    assert "coach_summary" in explanation
    assert "style_fit_confidence" in explanation["coach_summary"]["home"]


def test_style_fit_warning_when_confidence_low(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = _match(dataset, 1006)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, advanced)
    ctx = build_match_context(dataset, match, advanced)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=advanced)
    assert STYLE_FIT_WARNING in explanation["warnings"]


def test_style_fit_warning_absent_in_base_profile(dataset, settings):
    match = _match(dataset)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, settings)
    ctx = build_match_context(dataset, match, settings, profile="base")
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=settings)
    assert "coach_summary" not in explanation
    assert STYLE_FIT_WARNING not in explanation["warnings"]


def test_unknown_coach_warning_preserved(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = _match(dataset, 1006)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, advanced)
    ctx = build_match_context(dataset, match, advanced)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=advanced)
    assert any("sconosciuto" in w for w in explanation["warnings"])


def test_recent_change_warning_preserved(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = next(m for m in dataset.matches if m.home.team_id == 2 or m.away.team_id == 2)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, advanced)
    ctx = build_match_context(dataset, match, advanced)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=advanced)
    assert any("Recent coach change" in w for w in explanation["warnings"])


def test_cross_country_warning_preserved(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = next(m for m in dataset.matches if m.home.team_id == 4 or m.away.team_id == 4)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, advanced)
    ctx = build_match_context(dataset, match, advanced)
    explanation = explain_prediction(ctx, pred, dataset=dataset, settings=advanced)
    assert any("Cross-country coach adaptation" in w for w in explanation["warnings"])


def test_prediction_output_invariant(dataset, settings):
    advanced = replace(settings, data_profile="advanced")
    match = _match(dataset)
    model = get_model_by_name("feature", settings, dataset)
    pred = predict_match(dataset, match, model, advanced)
    assert set(pred.probabilities.as_dict().keys()) == {"home", "draw", "away"}
    assert hasattr(pred, "pick")
    assert hasattr(pred, "confidence")


def test_feature_model_has_no_coach_weights():
    from src.models.feature_model import WEIGHTS

    coach_keys = [k for outcome in WEIGHTS.values() for k in outcome if "coach" in k.lower()]
    assert coach_keys == []


def test_feature_trained_not_in_all_models_registry(dataset, settings):
    from src.models.registry import build_base_models

    names = {m.name for m in build_base_models(settings, dataset)}
    assert "feature_trained" not in names
