import json
from datetime import datetime

import pytest

from src.config import FIXTURES_DIR, load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.advanced_strength import compute_advanced_strength
from src.features.lineup_features import (
    FORECAST,
    KNOWN_PRE_MATCH,
    get_fixture_lineup_row,
    is_pre_match_lineup_usable,
    resolve_lineup_for_match,
)
from src.features.match_context import build_match_context
from src.features.recent_form import compute_team_form
from src.features.schedule_strength import compute_schedule_strength
from src.features.shots_features import get_team_shots_profile
from src.features.tactical_features import resolve_tactical_for_match
from src.features.xg_features import get_team_xg_profile


STRENGTH = {
    1: 1.85, 2: 0.95, 3: 1.75, 4: 1.05, 5: 1.70,
    6: 1.65, 7: 1.55, 8: 1.45, 9: 1.40, 10: 1.25,
}


@pytest.fixture(scope="module")
def dataset():
    return load_offline_dataset(384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def _backtest_target(dataset):
    finished = sorted(
        [m for m in dataset.matches if m.is_finished],
        key=lambda m: m.starting_at,
    )
    for match in finished:
        if dataset.team_history(match.home.team_id, match.starting_at):
            return match
    raise AssertionError("Nessuna partita finita con storico home disponibile")


def test_history_excludes_current_and_future_matches(dataset, settings):
    target = _backtest_target(dataset)
    as_of = target.starting_at
    home_id = target.home.team_id

    history = dataset.team_history(home_id, as_of)
    assert all(m.starting_at < as_of for m in history)
    assert all(m.id != target.id for m in history)
    assert all(m.is_finished for m in history)


def test_form_xg_shots_strength_sos_use_only_past_matches(dataset, settings):
    target = _backtest_target(dataset)
    as_of = target.starting_at
    home_id = target.home.team_id
    league_id = target.league_id

    history = dataset.team_history(home_id, as_of)
    assert history
    assert all(m.starting_at < as_of for m in history)

    form = compute_team_form(dataset, home_id, as_of, settings)
    assert form.matches_played == min(len(history), settings.form_window_matches)

    # Profili xG/shots/SOS derivano da team_history — verifica coerenza indiretta
    get_team_xg_profile(dataset, home_id, as_of, league_id)
    get_team_shots_profile(dataset, home_id, as_of, league_id)
    compute_advanced_strength(dataset, home_id, as_of, settings)
    compute_schedule_strength(dataset, home_id, as_of, settings, league_id)


def test_no_future_match_in_feature_inputs(dataset, settings):
    target = _backtest_target(dataset)
    as_of = target.starting_at

    future_ids = {
        m.id
        for m in dataset.matches
        if not m.is_finished or m.starting_at >= as_of
    }

    for team_id in (target.home.team_id, target.away.team_id):
        history = dataset.team_history(team_id, as_of)
        assert not any(m.id in future_ids for m in history)


def test_lineup_tactical_only_pre_match_marked(dataset):
    finished = next(m for m in dataset.matches if m.is_finished)
    future = next(m for m in dataset.matches if not m.is_finished)

    finished_row = get_fixture_lineup_row(384, finished.id)
    assert finished_row is not None
    assert finished_row["data_availability"] == KNOWN_PRE_MATCH
    assert is_pre_match_lineup_usable(finished_row, finished)

    future_row = get_fixture_lineup_row(384, future.id)
    assert future_row is not None
    assert future_row["data_availability"] == FORECAST
    assert is_pre_match_lineup_usable(future_row, future)

    resolved_finished = resolve_lineup_for_match(384, finished)
    assert resolved_finished.source == "mock_fixture"
    assert resolved_finished.lineup is not None

    resolved_future = resolve_lineup_for_match(384, future)
    assert resolved_future.source == "mock_fixture"

    # Simula riga post-match-only: non deve entrare in backtest
    bad_row = dict(finished_row)
    bad_row["data_availability"] = "post_match_only"
    assert not is_pre_match_lineup_usable(bad_row, finished)


def test_backtest_context_uses_pre_match_lineup_not_fallback(dataset, settings):
    target = _backtest_target(dataset)
    ctx = build_match_context(dataset, target, settings)
    assert ctx.lineup_source == "mock_fixture"
    assert ctx.tactical_source == "mock_fixture"
    assert ctx.player_lineup is not None
    assert ctx.player_lineup.data_availability == KNOWN_PRE_MATCH


def test_tactical_respects_pre_match_gate(dataset):
    target = _backtest_target(dataset)
    lineup = resolve_lineup_for_match(384, target).lineup
    tactical = resolve_tactical_for_match(384, target, lineup)
    assert tactical.source == "mock_fixture"
    assert tactical.tactical.source == "mock_fixture"


def test_lineup_ratings_match_fixture_teams():
    matches_path = FIXTURES_DIR / "league_384_matches.json"
    lineups_path = FIXTURES_DIR / "league_384_lineups.json"
    matches = json.loads(matches_path.read_text(encoding="utf-8"))["data"]
    lineups = json.loads(lineups_path.read_text(encoding="utf-8"))["fixtures"]

    by_id = {m["id"]: m for m in matches}

    for fixture_id, row in lineups.items():
        match = by_id[int(fixture_id)]
        home_id = next(
            p["id"] for p in match["participants"] if p["meta"]["location"] == "home"
        )
        away_id = next(
            p["id"] for p in match["participants"] if p["meta"]["location"] == "away"
        )
        assert int(row["home_id"]) == home_id
        assert int(row["away_id"]) == away_id
        assert row["home_offensive_quality"] == pytest.approx(STRENGTH[home_id], abs=0.01)
        assert row["away_offensive_quality"] == pytest.approx(STRENGTH[away_id], abs=0.01)
        assert row["home_player"]["starting_xi_attack_rating"] == pytest.approx(
            STRENGTH[home_id], abs=0.01
        )
        assert row["away_player"]["starting_xi_attack_rating"] == pytest.approx(
            STRENGTH[away_id], abs=0.01
        )
