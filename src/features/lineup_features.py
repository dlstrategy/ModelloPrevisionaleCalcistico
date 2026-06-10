"""Feature lineup e assenze — da fixture offline; Fase 3 da include lineups/sidelined."""

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


def _lineup_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_lineups.json"


def load_lineup_impacts(league_id: int) -> dict[int, LineupImpact]:
    path = _lineup_fixture_path(league_id)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
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
