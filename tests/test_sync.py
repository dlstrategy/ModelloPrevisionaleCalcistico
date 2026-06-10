from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import patch

from src.config import load_settings
from src.data_pipeline.sync import FUTURE_SYNC_DAYS, PAST_SYNC_DAYS, _merge_matches, _sync_from_api
from src.domain.enums import ParticipantLocation
from src.domain.match import Match, MatchParticipant


def _fixture_response(match_id: int, date_str: str, *, finished: bool) -> dict:
    scores = []
    if finished:
        scores = [
            {"description": "CURRENT", "score": {"participant": "home", "goals": 1}},
            {"description": "CURRENT", "score": {"participant": "away", "goals": 0}},
        ]
    return {
        "data": [
            {
                "id": match_id,
                "league_id": 384,
                "season_id": 25000,
                "starting_at": date_str,
                "participants": [
                    {"id": 1, "name": "Home", "meta": {"location": "home"}},
                    {"id": 2, "name": "Away", "meta": {"location": "away"}},
                ],
                "scores": scores,
            }
        ]
    }


def test_merge_matches_deduplicates_by_id():
    shared = Match(
        id=1,
        league_id=384,
        season_id=25000,
        starting_at=datetime(2025, 9, 20, 18, 0, 0),
        participants=[
            MatchParticipant(1, "A", ParticipantLocation.HOME),
            MatchParticipant(2, "B", ParticipantLocation.AWAY),
        ],
        score=None,
    )
    updated = Match(
        id=1,
        league_id=384,
        season_id=25000,
        starting_at=datetime(2025, 9, 20, 18, 0, 0),
        participants=shared.participants,
        score=None,
    )
    other = Match(
        id=2,
        league_id=384,
        season_id=25000,
        starting_at=datetime(2025, 9, 21, 18, 0, 0),
        participants=shared.participants,
        score=None,
    )
    merged = _merge_matches([shared], [updated, other])
    assert [match.id for match in merged] == [1, 2]


@patch("src.data_pipeline.sync.leagues_api.fetch_league")
@patch("src.data_pipeline.sync.fixtures_api.fetch_fixtures_between")
@patch("src.data_pipeline.sync.SportmonksClient")
@patch("src.data_pipeline.sync.ResponseCache")
@patch("src.data_pipeline.sync.datetime")
def test_sync_from_api_fetches_past_and_future_windows(
    mock_datetime,
    _mock_cache,
    _mock_client,
    mock_fetch_between,
    mock_fetch_league,
):
    fixed_now = datetime(2025, 9, 10, 12, 0, 0)
    mock_datetime.utcnow.return_value = fixed_now

    mock_fetch_league.return_value = {"data": {"currentseason": {"id": 25000}}}
    mock_fetch_between.side_effect = [
        _fixture_response(100, "2025-09-01 18:00:00", finished=True),
        _fixture_response(200, "2025-09-20 20:45:00", finished=False),
    ]

    settings = replace(
        load_settings(),
        api_token="token",
        enable_sportmonks_sync=True,
    )

    dataset = _sync_from_api(settings, 384)

    assert mock_fetch_between.call_count == 2
    past_call = mock_fetch_between.call_args_list[0]
    future_call = mock_fetch_between.call_args_list[1]

    today = fixed_now.date()
    assert past_call.args[1] == (today - timedelta(days=PAST_SYNC_DAYS)).isoformat()
    assert past_call.args[2] == today.isoformat()
    assert future_call.args[1] == today.isoformat()
    assert future_call.args[2] == (today + timedelta(days=FUTURE_SYNC_DAYS)).isoformat()

    assert len(dataset.matches) == 2
    assert dataset.upcoming_on("2025-09-20")[0].id == 200
