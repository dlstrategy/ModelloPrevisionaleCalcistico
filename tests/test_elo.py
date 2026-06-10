from datetime import datetime
from unittest.mock import patch

from src.config import load_settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_pipeline.sync import load_offline_dataset
from src.domain.enums import ParticipantLocation
from src.domain.match import Match, MatchParticipant
from src.features.match_context import build_match_context
from src.models.elo import EloModel
from src.models.elo_ratings import EloTable


def _make_upcoming_match(home_id: int, away_id: int) -> Match:
    return Match(
        id=9000,
        league_id=384,
        season_id=25000,
        starting_at=datetime(2025, 9, 20, 20, 45, 0),
        participants=[
            MatchParticipant(team_id=home_id, team_name="Home", location=ParticipantLocation.HOME),
            MatchParticipant(team_id=away_id, team_name="Away", location=ParticipantLocation.AWAY),
        ],
    )


def _elo_table_with_ratings(ratings: dict[int, float]) -> EloTable:
    table = EloTable()
    table.ratings.update(ratings)
    return table


def test_elo_predicts_valid_probabilities():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if not m.is_finished][0]
    model = EloModel(settings, dataset)
    context = build_match_context(dataset, upcoming, settings)
    probs = model.predict(context)
    assert abs(probs.home + probs.draw + probs.away - 1.0) < 1e-6


def test_elo_is_ready():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    assert EloModel(settings, dataset).is_ready() is True


def test_elo_strong_home_favored():
    settings = load_settings()
    dataset = MatchDataset(league_id=384, season_id=25000, matches=[])
    match = _make_upcoming_match(home_id=1, away_id=2)
    context = build_match_context(dataset, match, settings)
    model = EloModel(settings, dataset)

    with patch(
        "src.models.elo.build_elo_table",
        return_value=_elo_table_with_ratings({1: 1900.0, 2: 1200.0}),
    ):
        probs = model.predict(context)

    assert probs.home > probs.away


def test_elo_strong_away_can_be_favored():
    settings = load_settings()
    dataset = MatchDataset(league_id=384, season_id=25000, matches=[])
    match = _make_upcoming_match(home_id=1, away_id=2)
    context = build_match_context(dataset, match, settings)
    model = EloModel(settings, dataset)

    with patch(
        "src.models.elo.build_elo_table",
        return_value=_elo_table_with_ratings({1: 1200.0, 2: 1900.0}),
    ):
        probs = model.predict(context)

    assert probs.away > probs.home


def test_elo_away_win_probability_uses_expected_score():
    settings = load_settings()
    table = EloTable(ratings={1: 1200.0, 2: 1900.0})
    rh_adj = 1200.0 + settings.elo_home_advantage
    ra = 1900.0
    assert table.expected_score(ra, rh_adj) > table.expected_score(rh_adj, ra)
