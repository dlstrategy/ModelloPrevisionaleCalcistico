import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from src.config import QUALITY_DIR, load_settings
from src.data_pipeline.sync import load_offline_dataset, sync_league_data
from src.data_quality.checks import (
    IssueCollector,
    _check_lineup_tactical_row,
    _check_tactical_numeric_fields,
    copy_dataset,
    copy_match,
    run_all_checks,
)
from src.data_quality.report import build_report, save_quality_report
from src.domain.enums import ParticipantLocation
from src.domain.match import Match, MatchParticipant, Score
from src.features.lineup_features import FORECAST, KNOWN_PRE_MATCH
from src.features.match_context import build_match_context


@pytest.fixture(scope="module")
def settings():
    return load_settings()


@pytest.fixture(scope="module")
def valid_dataset(settings):
    sync_league_data(settings, 384)
    return load_offline_dataset(384)


def test_mock_dataset_passes_without_errors(valid_dataset, settings):
    issues, _ = run_all_checks(valid_dataset, settings, 384)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == []


def test_duplicate_fixture_generates_error(valid_dataset, settings):
    dup = copy.deepcopy(valid_dataset.matches[0])
    matches = valid_dataset.matches + [dup]
    dataset = copy_dataset(valid_dataset, matches)
    issues, _ = run_all_checks(dataset, settings, 384)
    codes = {i.code for i in issues if i.severity == "error"}
    assert "duplicate_fixture_id" in codes


def test_finished_without_score_generates_error(valid_dataset, settings):
    target = next(m for m in valid_dataset.matches if m.is_finished)
    broken = copy_match(target, score=None, state_id=5)
    matches = [broken if m.id == target.id else m for m in valid_dataset.matches]
    dataset = copy_dataset(valid_dataset, matches)
    issues, _ = run_all_checks(dataset, settings, 384)
    codes = {i.code for i in issues if i.severity == "error"}
    assert "finished_without_score" in codes


def test_future_with_score_generates_error(valid_dataset, settings):
    target = next(m for m in valid_dataset.matches if not m.is_finished)
    broken = copy_match(target, score=Score(home=1, away=0), state_id=1)
    matches = [broken if m.id == target.id else m for m in valid_dataset.matches]
    dataset = copy_dataset(valid_dataset, matches)
    issues, _ = run_all_checks(dataset, settings, 384)
    codes = {i.code for i in issues if i.severity == "error"}
    assert "future_with_score" in codes


def test_lineup_home_id_mismatch_generates_error(valid_dataset):
    collector = IssueCollector()
    match = valid_dataset.matches[0]
    row = {
        "home_id": match.home.team_id + 999,
        "away_id": match.away.team_id,
        "data_availability": KNOWN_PRE_MATCH if match.is_finished else FORECAST,
    }
    _check_lineup_tactical_row(valid_dataset, "lineups", match.id, row, collector)
    codes = {i.code for i in collector.issues}
    assert "home_id_mismatch" in codes


def test_tactical_wrong_availability_on_future_generates_error(valid_dataset):
    collector = IssueCollector()
    future = next(m for m in valid_dataset.matches if not m.is_finished)
    row = {
        "home_id": future.home.team_id,
        "away_id": future.away.team_id,
        "data_availability": KNOWN_PRE_MATCH,
    }
    _check_lineup_tactical_row(valid_dataset, "tactical", future.id, row, collector)
    codes = {i.code for i in collector.issues if i.severity == "error"}
    assert "future_with_known_pre_match" in codes


def test_feature_vector_nonempty_without_nan(valid_dataset, settings):
    sample = next(m for m in valid_dataset.matches if not m.is_finished)
    ctx = build_match_context(valid_dataset, sample, settings, as_of=sample.starting_at)
    assert ctx.feature_vector
    for value in ctx.feature_vector.values():
        assert value == value  # not NaN
        assert abs(value) != float("inf")


def test_model_probabilities_normalized(valid_dataset, settings):
    from src.models.registry import get_model_by_name

    model = get_model_by_name("ensemble", settings, valid_dataset)
    sample = next(m for m in valid_dataset.matches if not m.is_finished)
    ctx = build_match_context(valid_dataset, sample, settings, as_of=sample.starting_at)
    probs = model.predict(ctx)
    total = probs.home + probs.draw + probs.away
    assert abs(total - 1.0) < 1e-4
    assert probs.home >= 0 and probs.draw >= 0 and probs.away >= 0


def test_build_report_passed_only_without_errors(valid_dataset, settings):
    issues, summary = run_all_checks(valid_dataset, settings, 384)
    report = build_report(384, issues, dataset_summary=summary)
    assert report.passed is True
    assert report.errors == 0


def test_quality_report_serializable(valid_dataset, settings, tmp_path):
    issues, summary = run_all_checks(valid_dataset, settings, 384)
    report = build_report(384, issues, dataset_summary=summary)
    json_path, csv_path = save_quality_report(report, tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "passed" in payload
    assert "issues" in payload
    assert csv_path.exists()


def test_tactical_nan_generates_error(valid_dataset):
    collector = IssueCollector()
    match = valid_dataset.matches[0]
    row = {
        "home_id": match.home.team_id,
        "away_id": match.away.team_id,
        "data_availability": KNOWN_PRE_MATCH if match.is_finished else FORECAST,
        "wing_advantage": float("nan"),
    }
    _check_tactical_numeric_fields(collector, match.id, row)
    assert any(i.severity == "error" and "nan_inf" in i.code for i in collector.issues)


def test_tactical_non_numeric_generates_error(valid_dataset):
    collector = IssueCollector()
    match = valid_dataset.matches[0]
    row = {
        "home_id": match.home.team_id,
        "away_id": match.away.team_id,
        "data_availability": KNOWN_PRE_MATCH if match.is_finished else FORECAST,
        "midfield_advantage": "bad",
    }
    _check_tactical_numeric_fields(collector, match.id, row)
    assert any(i.severity == "error" for i in collector.issues)


def test_tactical_wing_out_of_range_generates_warning(valid_dataset):
    collector = IssueCollector()
    match = valid_dataset.matches[0]
    row = {
        "home_id": match.home.team_id,
        "away_id": match.away.team_id,
        "data_availability": KNOWN_PRE_MATCH if match.is_finished else FORECAST,
        "wing_advantage": 5.0,
    }
    _check_tactical_numeric_fields(collector, match.id, row)
    assert any(i.severity == "warning" and i.code == "tactical_out_of_range" for i in collector.issues)


def test_tactical_defensive_line_risk_negative_generates_warning(valid_dataset):
    collector = IssueCollector()
    match = valid_dataset.matches[0]
    row = {
        "home_id": match.home.team_id,
        "away_id": match.away.team_id,
        "data_availability": KNOWN_PRE_MATCH if match.is_finished else FORECAST,
        "defensive_line_risk": -0.5,
    }
    _check_tactical_numeric_fields(collector, match.id, row)
    assert any(
        i.severity == "warning"
        and i.code == "tactical_out_of_range"
        and "defensive_line_risk" in i.message
        for i in collector.issues
    )
