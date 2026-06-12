"""Feature xG estese — rolling, overperformance, split casa/trasferta."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.config import FIXTURES_DIR
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import ParticipantLocation


@dataclass(frozen=True)
class TeamXgSnapshot:
    team_id: int
    xg_for: float
    xg_against: float
    clean_sheet_rate: float


@dataclass(frozen=True)
class TeamXgProfile:
    team_id: int
    xg_for_avg: float
    xg_against_avg: float
    xg_diff_avg: float
    xg_for_home: float
    xg_against_home: float
    xg_for_away: float
    xg_against_away: float
    rolling_xg_for_5: float
    rolling_xg_against_5: float
    rolling_xg_diff_5: float
    goals_minus_xg: float
    goals_against_minus_xga: float


def _xg_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_xg.json"


def _load_xg_payload(league_id: int) -> dict:
    path = _xg_fixture_path(league_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_xg_table(league_id: int) -> dict[int, TeamXgSnapshot]:
    payload = _load_xg_payload(league_id)
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


def _match_xg_row(payload: dict, match_id: int) -> dict | None:
    history = payload.get("match_history", {})
    return history.get(str(match_id)) or history.get(match_id)


def _team_xg_from_match(row: dict, location: ParticipantLocation) -> tuple[float, float, float, float]:
    if location == ParticipantLocation.HOME:
        return (
            float(row.get("home_xg", 1.3)),
            float(row.get("home_xga", 1.3)),
            float(row.get("home_goals", 0)),
            float(row.get("home_goals_against", 0)),
        )
    return (
        float(row.get("away_xg", 1.3)),
        float(row.get("away_xga", 1.3)),
        float(row.get("away_goals", 0)),
        float(row.get("away_goals_against", 0)),
    )


def get_team_xg_profile(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    league_id: int,
) -> TeamXgProfile:
    payload = _load_xg_payload(league_id)
    team_defaults = payload.get("teams", {}).get(str(team_id), {})
    history = dataset.team_history(team_id, as_of)

    xg_for_list: list[float] = []
    xga_list: list[float] = []
    goals_list: list[float] = []
    ga_list: list[float] = []
    home_xgf: list[float] = []
    home_xga: list[float] = []
    away_xgf: list[float] = []
    away_xga: list[float] = []

    for match in history:
        row = _match_xg_row(payload, match.id)
        if row is None:
            scored, conceded = dataset.team_goals(team_id, match)
            xg_for_list.append(float(team_defaults.get("xg_for", 1.3)))
            xga_list.append(float(team_defaults.get("xg_against", 1.3)))
            goals_list.append(float(scored))
            ga_list.append(float(conceded))
            continue
        for participant in match.participants:
            if participant.team_id != team_id:
                continue
            xgf, xga, gf, ga = _team_xg_from_match(row, participant.location)
            xg_for_list.append(xgf)
            xga_list.append(xga)
            goals_list.append(gf)
            ga_list.append(ga)
            if participant.location == ParticipantLocation.HOME:
                home_xgf.append(xgf)
                home_xga.append(xga)
            else:
                away_xgf.append(xgf)
                away_xga.append(xga)

    def avg(values: list[float], default: float) -> float:
        return sum(values) / len(values) if values else default

    default_xgf = float(team_defaults.get("xg_for", 1.3))
    default_xga = float(team_defaults.get("xg_against", 1.3))
    xg_for_avg = avg(xg_for_list, default_xgf)
    xg_against_avg = avg(xga_list, default_xga)
    rolling_5_xgf = avg(xg_for_list[-5:], xg_for_avg)
    rolling_5_xga = avg(xga_list[-5:], xg_against_avg)
    goals_minus = avg(goals_list, 0.0) - xg_for_avg
    ga_minus_xga = avg(ga_list, 0.0) - xg_against_avg

    return TeamXgProfile(
        team_id=team_id,
        xg_for_avg=xg_for_avg,
        xg_against_avg=xg_against_avg,
        xg_diff_avg=xg_for_avg - xg_against_avg,
        xg_for_home=avg(home_xgf, default_xgf),
        xg_against_home=avg(home_xga, default_xga),
        xg_for_away=avg(away_xgf, default_xgf),
        xg_against_away=avg(away_xga, default_xga),
        rolling_xg_for_5=rolling_5_xgf,
        rolling_xg_against_5=rolling_5_xga,
        rolling_xg_diff_5=rolling_5_xgf - rolling_5_xga,
        goals_minus_xg=goals_minus,
        goals_against_minus_xga=ga_minus_xga,
    )


def xg_profile_to_features(prefix: str, profile: TeamXgProfile) -> dict[str, float]:
    return {
        f"{prefix}_xg_for_avg": profile.xg_for_avg,
        f"{prefix}_xg_against_avg": profile.xg_against_avg,
        f"{prefix}_xg_diff_avg": profile.xg_diff_avg,
        f"{prefix}_xg_for_home": profile.xg_for_home,
        f"{prefix}_xg_against_home": profile.xg_against_home,
        f"{prefix}_xg_for_away": profile.xg_for_away,
        f"{prefix}_xg_against_away": profile.xg_against_away,
        f"{prefix}_rolling_xg_for_5": profile.rolling_xg_for_5,
        f"{prefix}_rolling_xg_against_5": profile.rolling_xg_against_5,
        f"{prefix}_rolling_xg_diff_5": profile.rolling_xg_diff_5,
        f"{prefix}_goals_minus_xg": profile.goals_minus_xg,
        f"{prefix}_goals_against_minus_xga": profile.goals_against_minus_xga,
    }
