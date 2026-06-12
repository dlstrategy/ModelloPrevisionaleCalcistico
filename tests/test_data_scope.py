"""Test DataScope — isolamento league/season."""

import pytest

from src.config import SERIE_A_LEAGUE_ID
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_pipeline.scope import DataScope, legacy_processed_dataset_filename, scope_metadata_dict
from src.data_pipeline.sync import load_offline_dataset
from src.domain.enums import ParticipantLocation
from src.domain.match import Match, MatchParticipant


def test_league_only_dataset_key():
    scope = DataScope(league_id=384)
    assert scope.league_key == "league_384"
    assert scope.dataset_key == "league_384"
    assert scope.season_key is None


def test_league_and_season_dataset_key():
    scope = DataScope(league_id=384, season_id=23614)
    assert scope.dataset_key == "league_384_season_23614"
    assert scope.season_key == "season_23614"


def test_validate_match_rejects_wrong_league():
    scope = DataScope(league_id=384)
    dataset = load_offline_dataset(SERIE_A_LEAGUE_ID)
    match = dataset.matches[0]
    wrong = Match(
        id=match.id,
        league_id=564,
        season_id=match.season_id,
        starting_at=match.starting_at,
        participants=match.participants,
        score=match.score,
    )
    with pytest.raises(ValueError, match="league mismatch"):
        scope.validate_match(wrong)


def test_from_dataset():
    dataset = load_offline_dataset(384)
    scope = DataScope.from_dataset(dataset)
    assert scope.league_id == 384
    assert scope.season_id == dataset.season_id


def test_scope_metadata_dict():
    scope = DataScope(league_id=384, season_id=23614)
    meta = scope_metadata_dict(scope)
    assert meta["league_id"] == 384
    assert meta["dataset_key"] == "league_384_season_23614"


def test_legacy_filename_unchanged():
    scope = DataScope(league_id=384, season_id=23614)
    assert legacy_processed_dataset_filename(scope) == "league_384_dataset.json"


def test_dataset_save_includes_scope(tmp_path):
    dataset = load_offline_dataset(384)
    path = tmp_path / "dataset.json"
    dataset.save(path)
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["data_scope"]["league_key"] == "league_384"
