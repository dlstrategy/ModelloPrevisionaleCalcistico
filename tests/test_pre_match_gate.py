import pytest

from src.data_pipeline.sync import load_offline_dataset
from src.features.lineup_features import (
    FORECAST,
    KNOWN_PRE_MATCH,
    POST_MATCH_ONLY,
    is_pre_match_fixture_row_usable,
    is_pre_match_lineup_usable,
)


@pytest.fixture(scope="module")
def dataset():
    return load_offline_dataset(384)


def _row(match, availability: str | None, home_id=None, away_id=None) -> dict:
    return {
        "home_id": match.home.team_id if home_id is None else home_id,
        "away_id": match.away.team_id if away_id is None else away_id,
        "data_availability": availability,
    }


def test_known_pre_match_on_finished_valid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    assert is_pre_match_fixture_row_usable(_row(finished, KNOWN_PRE_MATCH), finished)


def test_forecast_on_future_valid(dataset):
    future = next(m for m in dataset.matches if not m.is_finished)
    assert is_pre_match_fixture_row_usable(_row(future, FORECAST), future)


def test_forecast_on_finished_invalid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    assert not is_pre_match_fixture_row_usable(_row(finished, FORECAST), finished)


def test_known_pre_match_on_future_invalid(dataset):
    future = next(m for m in dataset.matches if not m.is_finished)
    assert not is_pre_match_fixture_row_usable(_row(future, KNOWN_PRE_MATCH), future)


def test_post_match_only_invalid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    assert not is_pre_match_fixture_row_usable(_row(finished, POST_MATCH_ONLY), finished)


def test_missing_data_availability_invalid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    row = _row(finished, KNOWN_PRE_MATCH)
    del row["data_availability"]
    assert not is_pre_match_fixture_row_usable(row, finished)


def test_unknown_availability_invalid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    assert not is_pre_match_fixture_row_usable(_row(finished, "unknown"), finished)


def test_wrong_home_id_invalid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    assert not is_pre_match_fixture_row_usable(
        _row(finished, KNOWN_PRE_MATCH, home_id=finished.home.team_id + 999),
        finished,
    )


def test_wrong_away_id_invalid(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    assert not is_pre_match_fixture_row_usable(
        _row(finished, KNOWN_PRE_MATCH, away_id=finished.away.team_id + 999),
        finished,
    )


def test_lineup_wrapper_matches_generic(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    row = _row(finished, KNOWN_PRE_MATCH)
    assert is_pre_match_lineup_usable(row, finished) == is_pre_match_fixture_row_usable(row, finished)
