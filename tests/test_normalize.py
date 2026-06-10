from datetime import datetime

import pytest

from src.data_pipeline.normalize import _parse_datetime, normalize_fixture, normalize_fixtures_response


def test_parse_datetime_sportmonks_format():
    assert _parse_datetime("2025-09-20 20:45:00") == datetime(2025, 9, 20, 20, 45, 0)


def test_parse_datetime_iso_with_timezone_offset():
    assert _parse_datetime("2025-09-20T18:45:00+02:00") == datetime(2025, 9, 20, 16, 45, 0)


def test_parse_datetime_iso_utc_z_suffix():
    assert _parse_datetime("2025-09-20T18:45:00Z") == datetime(2025, 9, 20, 18, 45, 0)


def test_parse_datetime_iso_without_timezone():
    assert _parse_datetime("2025-09-20T18:45:00") == datetime(2025, 9, 20, 18, 45, 0)


def test_parse_datetime_date_only():
    assert _parse_datetime("2025-09-20") == datetime(2025, 9, 20, 0, 0, 0)


def test_parse_datetime_strips_whitespace():
    assert _parse_datetime("  2025-09-20 20:45:00  ") == datetime(2025, 9, 20, 20, 45, 0)


def test_parse_datetime_rejects_invalid():
    with pytest.raises(ValueError, match="Unsupported"):
        _parse_datetime("not-a-date")


def test_normalize_fixture_realistic_sportmonks_payload():
    raw = {
        "id": 19146726,
        "league_id": 384,
        "season_id": 23700,
        "round_id": 339123,
        "state_id": 1,
        "starting_at": "2025-09-20T18:45:00+00:00",
        "participants": [
            {"id": 113, "name": "Milan", "meta": {"location": "home"}},
            {"id": 102, "name": "Genoa", "meta": {"location": "away"}},
        ],
        "scores": [],
    }
    match = normalize_fixture(raw)
    assert match is not None
    assert match.id == 19146726
    assert match.starting_at == datetime(2025, 9, 20, 18, 45, 0)
    assert match.home.team_name == "Milan"
    assert match.away.team_name == "Genoa"
    assert match.score is None


def test_normalize_fixtures_response_extracts_finished_score():
    response = {
        "data": [
            {
                "id": 1001,
                "league_id": 384,
                "season_id": 25000,
                "starting_at": "2025-08-23 18:45:00",
                "participants": [
                    {"id": 1, "name": "Inter", "meta": {"location": "home"}},
                    {"id": 2, "name": "Genoa", "meta": {"location": "away"}},
                ],
                "scores": [
                    {"description": "CURRENT", "score": {"participant": "home", "goals": 2}},
                    {"description": "CURRENT", "score": {"participant": "away", "goals": 0}},
                ],
            }
        ]
    }
    matches = normalize_fixtures_response(response)
    assert len(matches) == 1
    assert matches[0].score is not None
    assert matches[0].score.home == 2
    assert matches[0].score.away == 0
