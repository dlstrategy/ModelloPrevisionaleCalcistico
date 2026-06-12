"""Confronto tattico mock — formazioni e duelli di stile."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import FIXTURES_DIR
from src.features.lineup_features import LineupImpact


FORMATION_CODES = {
    "4-3-3": 433,
    "3-5-2": 352,
    "4-4-2": 442,
    "4-2-3-1": 4231,
    "3-4-3": 343,
    "5-3-2": 532,
}


@dataclass(frozen=True)
class TacticalMatchup:
    fixture_id: int
    home_formation: str
    away_formation: str
    formation_matchup_score: float
    wing_advantage: float
    midfield_advantage: float
    aerial_advantage: float
    pressing_mismatch: float
    defensive_line_risk: float


def _tactical_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_tactical.json"


def _load_tactical_payload(league_id: int) -> dict:
    path = _tactical_fixture_path(league_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def tactical_edge_score(lineup: LineupImpact | None) -> float:
    if lineup is None or not lineup.duel_edges:
        return 0.0
    return sum(lineup.duel_edges.values()) / len(lineup.duel_edges)


def _formation_code(name: str | None) -> float:
    if not name:
        return 442.0
    return float(FORMATION_CODES.get(name, 442))


def get_tactical_matchup(
    league_id: int,
    fixture_id: int,
    lineup: LineupImpact | None = None,
) -> TacticalMatchup:
    payload = _load_tactical_payload(league_id)
    row = payload.get("fixtures", {}).get(str(fixture_id), {})

    home_form = row.get("home_formation") or (lineup.home_formation if lineup else "4-3-3")
    away_form = row.get("away_formation") or (lineup.away_formation if lineup else "4-4-2")

    edges = lineup.duel_edges if lineup else {}
    wing = float(row.get("wing_advantage", edges.get("wing", 0.0)))
    mid = float(row.get("midfield_advantage", edges.get("midfield", 0.0)))
    aerial = float(row.get("aerial_advantage", edges.get("aerial", 0.0)))
    pressing = float(row.get("pressing_mismatch", edges.get("pressing", 0.0)))
    def_line = float(row.get("defensive_line_risk", edges.get("defensive_line", 0.0)))

    home_code = _formation_code(home_form)
    away_code = _formation_code(away_form)
    matchup = (home_code - away_code) / 1000.0 + (wing + mid) * 0.15

    return TacticalMatchup(
        fixture_id=fixture_id,
        home_formation=str(home_form),
        away_formation=str(away_form),
        formation_matchup_score=matchup,
        wing_advantage=wing,
        midfield_advantage=mid,
        aerial_advantage=aerial,
        pressing_mismatch=pressing,
        defensive_line_risk=def_line,
    )


def tactical_to_features(tactical: TacticalMatchup) -> dict[str, float]:
    return {
        "home_formation_code": _formation_code(tactical.home_formation),
        "away_formation_code": _formation_code(tactical.away_formation),
        "formation_matchup_score": tactical.formation_matchup_score,
        "wing_advantage": tactical.wing_advantage,
        "midfield_advantage": tactical.midfield_advantage,
        "aerial_advantage": tactical.aerial_advantage,
        "pressing_mismatch": tactical.pressing_mismatch,
        "defensive_line_risk": tactical.defensive_line_risk,
    }
