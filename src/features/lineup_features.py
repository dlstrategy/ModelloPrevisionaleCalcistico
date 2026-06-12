"""Lineup e player impact mock — XI, assenze, bench."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.config import FIXTURES_DIR


@dataclass(frozen=True)
class LineupImpact:
    fixture_id: int
    home_offensive_quality: float
    home_defensive_quality: float
    away_offensive_quality: float
    away_defensive_quality: float
    home_absences: int = 0
    away_absences: int = 0
    home_formation: str | None = None
    away_formation: str | None = None
    duel_edges: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PlayerLineupSnapshot:
    fixture_id: int
    home_starting_xi_attack_rating: float
    away_starting_xi_attack_rating: float
    home_starting_xi_defense_rating: float
    away_starting_xi_defense_rating: float
    home_starting_xi_midfield_rating: float
    away_starting_xi_midfield_rating: float
    home_goalkeeper_rating: float
    away_goalkeeper_rating: float
    home_missing_starters_count: int
    away_missing_starters_count: int
    home_missing_minutes_share: float
    away_missing_minutes_share: float
    home_missing_goals_share: float
    away_missing_goals_share: float
    home_missing_xg_share: float
    away_missing_xg_share: float
    home_bench_strength: float
    away_bench_strength: float
    home_lineup_continuity: float
    away_lineup_continuity: float


def _lineup_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_lineups.json"


def _load_lineup_payload(league_id: int) -> dict:
    path = _lineup_fixture_path(league_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_lineup_impacts(league_id: int) -> dict[int, LineupImpact]:
    payload = _load_lineup_payload(league_id)
    impacts: dict[int, LineupImpact] = {}
    for fixture_id, row in payload.get("fixtures", {}).items():
        impacts[int(fixture_id)] = LineupImpact(
            fixture_id=int(fixture_id),
            home_offensive_quality=float(row.get("home_offensive_quality", 1.0)),
            home_defensive_quality=float(row.get("home_defensive_quality", 1.0)),
            away_offensive_quality=float(row.get("away_offensive_quality", 1.0)),
            away_defensive_quality=float(row.get("away_defensive_quality", 1.0)),
            home_absences=int(row.get("home_absences", 0)),
            away_absences=int(row.get("away_absences", 0)),
            home_formation=row.get("home_formation"),
            away_formation=row.get("away_formation"),
            duel_edges=row.get("duel_edges", {}),
        )
    return impacts


def get_lineup_impact(league_id: int, fixture_id: int) -> LineupImpact | None:
    return load_lineup_impacts(league_id).get(fixture_id)


def get_player_lineup_snapshot(league_id: int, fixture_id: int) -> PlayerLineupSnapshot | None:
    payload = _load_lineup_payload(league_id)
    row = payload.get("fixtures", {}).get(str(fixture_id))
    if row is None:
        return None

    def side(prefix: str, defaults: dict) -> dict:
        block = row.get(prefix, defaults)
        return block if isinstance(block, dict) else defaults

    home = side("home_player", {})
    away = side("away_player", {})

    return PlayerLineupSnapshot(
        fixture_id=fixture_id,
        home_starting_xi_attack_rating=float(
            home.get("starting_xi_attack_rating", row.get("home_offensive_quality", 1.0))
        ),
        away_starting_xi_attack_rating=float(
            away.get("starting_xi_attack_rating", row.get("away_offensive_quality", 1.0))
        ),
        home_starting_xi_defense_rating=float(
            home.get("starting_xi_defense_rating", row.get("home_defensive_quality", 1.0))
        ),
        away_starting_xi_defense_rating=float(
            away.get("starting_xi_defense_rating", row.get("away_defensive_quality", 1.0))
        ),
        home_starting_xi_midfield_rating=float(home.get("starting_xi_midfield_rating", 1.0)),
        away_starting_xi_midfield_rating=float(away.get("starting_xi_midfield_rating", 1.0)),
        home_goalkeeper_rating=float(home.get("goalkeeper_rating", 0.75)),
        away_goalkeeper_rating=float(away.get("goalkeeper_rating", 0.75)),
        home_missing_starters_count=int(home.get("missing_starters_count", row.get("home_absences", 0))),
        away_missing_starters_count=int(away.get("missing_starters_count", row.get("away_absences", 0))),
        home_missing_minutes_share=float(home.get("missing_minutes_share", 0.0)),
        away_missing_minutes_share=float(away.get("missing_minutes_share", 0.0)),
        home_missing_goals_share=float(home.get("missing_goals_share", 0.0)),
        away_missing_goals_share=float(away.get("missing_goals_share", 0.0)),
        home_missing_xg_share=float(home.get("missing_xg_share", 0.0)),
        away_missing_xg_share=float(away.get("missing_xg_share", 0.0)),
        home_bench_strength=float(home.get("bench_strength", 0.65)),
        away_bench_strength=float(away.get("bench_strength", 0.65)),
        home_lineup_continuity=float(home.get("lineup_continuity", 0.8)),
        away_lineup_continuity=float(away.get("lineup_continuity", 0.8)),
    )


def player_lineup_to_features(snap: PlayerLineupSnapshot) -> dict[str, float]:
    return {
        "home_starting_xi_attack_rating": snap.home_starting_xi_attack_rating,
        "away_starting_xi_attack_rating": snap.away_starting_xi_attack_rating,
        "home_starting_xi_defense_rating": snap.home_starting_xi_defense_rating,
        "away_starting_xi_defense_rating": snap.away_starting_xi_defense_rating,
        "home_starting_xi_midfield_rating": snap.home_starting_xi_midfield_rating,
        "away_starting_xi_midfield_rating": snap.away_starting_xi_midfield_rating,
        "home_goalkeeper_rating": snap.home_goalkeeper_rating,
        "away_goalkeeper_rating": snap.away_goalkeeper_rating,
        "home_missing_starters_count": float(snap.home_missing_starters_count),
        "away_missing_starters_count": float(snap.away_missing_starters_count),
        "home_missing_minutes_share": snap.home_missing_minutes_share,
        "away_missing_minutes_share": snap.away_missing_minutes_share,
        "home_missing_goals_share": snap.home_missing_goals_share,
        "away_missing_goals_share": snap.away_missing_goals_share,
        "home_missing_xg_share": snap.home_missing_xg_share,
        "away_missing_xg_share": snap.away_missing_xg_share,
        "home_bench_strength": snap.home_bench_strength,
        "away_bench_strength": snap.away_bench_strength,
        "home_lineup_continuity": snap.home_lineup_continuity,
        "away_lineup_continuity": snap.away_lineup_continuity,
    }


def default_player_lineup_snapshot(fixture_id: int) -> PlayerLineupSnapshot:
    return PlayerLineupSnapshot(
        fixture_id=fixture_id,
        home_starting_xi_attack_rating=1.0,
        away_starting_xi_attack_rating=1.0,
        home_starting_xi_defense_rating=1.0,
        away_starting_xi_defense_rating=1.0,
        home_starting_xi_midfield_rating=1.0,
        away_starting_xi_midfield_rating=1.0,
        home_goalkeeper_rating=0.75,
        away_goalkeeper_rating=0.75,
        home_missing_starters_count=0,
        away_missing_starters_count=0,
        home_missing_minutes_share=0.0,
        away_missing_minutes_share=0.0,
        home_missing_goals_share=0.0,
        away_missing_goals_share=0.0,
        home_missing_xg_share=0.0,
        away_missing_xg_share=0.0,
        home_bench_strength=0.65,
        away_bench_strength=0.65,
        home_lineup_continuity=0.8,
        away_lineup_continuity=0.8,
    )
