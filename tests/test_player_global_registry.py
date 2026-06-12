"""Test registry globale giocatori."""

from src.players.global_registry import (
    get_latest_snapshot,
    get_player_snapshot_for_league,
    load_player_careers,
)


def test_load_player_careers():
    careers = load_player_careers()
    assert len(careers) >= 4
    assert 1001 in careers
    assert 1002 in careers


def test_player_id_global_across_leagues():
    careers = load_player_careers()
    winger = careers[1002]
    leagues = {s.league_id for s in winger.snapshots}
    assert winger.player_id == 1002
    assert 564 in leagues
    assert 384 in leagues


def test_filter_by_league():
    serie_a = load_player_careers(league_id=384)
    assert 1001 in serie_a
    assert all(s.league_id == 384 for s in serie_a[1001].snapshots)


def test_get_player_snapshot_for_league():
    snap = get_player_snapshot_for_league(1002, 564)
    assert snap is not None
    assert snap.league_id == 564
    assert snap.rating == 7.8


def test_get_latest_snapshot_excludes_target_league():
    snap = get_latest_snapshot(1002, before_league_id=384)
    assert snap is not None
    assert snap.league_id == 564


def test_unknown_player_empty_career():
    careers = load_player_careers()
    rookie = careers.get(1004)
    assert rookie is not None
    assert rookie.snapshots == ()
