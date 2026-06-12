"""Calendario, riposo e fatigue score."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.config import FIXTURES_DIR
from src.data_pipeline.dataset_builder import MatchDataset


@dataclass(frozen=True)
class FatigueSnapshot:
    team_id: int
    days_rest: float
    matches_last_7_days: int
    matches_last_14_days: int
    played_midweek: float
    rotation_risk: float
    fatigue_score: float


def _calendar_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_calendar.json"


def _load_calendar_payload(league_id: int) -> dict:
    path = _calendar_fixture_path(league_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute_fatigue_snapshot(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    league_id: int,
) -> FatigueSnapshot:
    history = dataset.team_history(team_id, as_of)
    days_rest = 7.0
    if history:
        days_rest = (as_of - history[-1].starting_at).total_seconds() / 86400.0

    window_7 = as_of.timestamp() - 7 * 86400
    window_14 = as_of.timestamp() - 14 * 86400
    last_7 = sum(1 for m in history if m.starting_at.timestamp() >= window_7)
    last_14 = sum(1 for m in history if m.starting_at.timestamp() >= window_14)

    payload = _load_calendar_payload(league_id)
    team_row = payload.get("teams", {}).get(str(team_id), {})
    played_midweek = float(team_row.get("played_midweek", 0.0))
    rotation_risk = float(team_row.get("rotation_risk", 0.0))

    # Fatigue: più partite recenti e meno riposo → score alto
    fatigue = (last_7 * 0.35 + last_14 * 0.15) - min(days_rest, 7.0) * 0.08
    fatigue += played_midweek * 0.25 + rotation_risk * 0.2
    fatigue = max(0.0, fatigue)

    return FatigueSnapshot(
        team_id=team_id,
        days_rest=days_rest,
        matches_last_7_days=last_7,
        matches_last_14_days=last_14,
        played_midweek=played_midweek,
        rotation_risk=rotation_risk,
        fatigue_score=fatigue,
    )


def fatigue_to_features(home: FatigueSnapshot, away: FatigueSnapshot) -> dict[str, float]:
    return {
        "days_rest_home": home.days_rest,
        "days_rest_away": away.days_rest,
        "rest_difference": home.days_rest - away.days_rest,
        "matches_last_7_days_home": float(home.matches_last_7_days),
        "matches_last_7_days_away": float(away.matches_last_7_days),
        "matches_last_14_days_home": float(home.matches_last_14_days),
        "matches_last_14_days_away": float(away.matches_last_14_days),
        "played_midweek_home": home.played_midweek,
        "played_midweek_away": away.played_midweek,
        "rotation_risk_home": home.rotation_risk,
        "rotation_risk_away": away.rotation_risk,
        "fatigue_score_home": home.fatigue_score,
        "fatigue_score_away": away.fatigue_score,
    }
