"""Feature xG — da fixture offline; Fase 3 da endpoint expected-xg Sportmonks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import FIXTURES_DIR


@dataclass(frozen=True)
class TeamXgSnapshot:
    team_id: int
    xg_for: float
    xg_against: float
    clean_sheet_rate: float


def _xg_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_xg.json"


def load_xg_table(league_id: int) -> dict[int, TeamXgSnapshot]:
    path = _xg_fixture_path(league_id)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    table: dict[int, TeamXgSnapshot] = {}
    for tid, row in payload.get("teams", {}).items():
        table[int(tid)] = TeamXgSnapshot(
            team_id=int(tid),
            xg_for=float(row.get("xg_for", 1.3)),
            xg_against=float(row.get("xg_against", 1.3)),
            clean_sheet_rate=float(row.get("clean_sheet_rate", 0.25)),
        )
    return table


def get_team_xg(league_id: int, team_id: int) -> TeamXgSnapshot | None:
    return load_xg_table(league_id).get(team_id)
