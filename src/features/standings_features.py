"""Feature da classifica calcolata su partite finite."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import MatchOutcome, ParticipantLocation


@dataclass(frozen=True)
class TeamStandingsSnapshot:
    team_id: int
    position: int
    points: int
    played: int
    goals_for: int
    goals_against: int
    goal_difference: int
    win_streak: int
    unbeaten_streak: int
    loss_streak: int


def _match_points(outcome: MatchOutcome, location: ParticipantLocation) -> int:
    if outcome == MatchOutcome.DRAW:
        return 1
    if outcome == MatchOutcome.HOME and location == ParticipantLocation.HOME:
        return 3
    if outcome == MatchOutcome.AWAY and location == ParticipantLocation.AWAY:
        return 3
    return 0


def compute_standings_table(dataset: MatchDataset, as_of: datetime) -> dict[int, TeamStandingsSnapshot]:
    stats: dict[int, dict] = {}

    for match in dataset.finished_before(as_of):
        if match.score is None or match.actual_outcome is None:
            continue
        for participant in match.participants:
            tid = participant.team_id
            if tid not in stats:
                stats[tid] = {
                    "points": 0,
                    "played": 0,
                    "gf": 0,
                    "ga": 0,
                    "results": [],
                }
            scored, conceded = dataset.team_goals(tid, match)
            pts = _match_points(match.actual_outcome, participant.location)
            stats[tid]["points"] += pts
            stats[tid]["played"] += 1
            stats[tid]["gf"] += scored
            stats[tid]["ga"] += conceded
            if pts == 3:
                stats[tid]["results"].append("W")
            elif pts == 1:
                stats[tid]["results"].append("D")
            else:
                stats[tid]["results"].append("L")

    rows: list[tuple[int, int, int, int]] = []
    for tid, s in stats.items():
        rows.append((tid, s["points"], s["gf"] - s["ga"], s["gf"]))

    rows.sort(key=lambda r: (-r[1], -r[2], -r[3]))

    table: dict[int, TeamStandingsSnapshot] = {}
    for pos, (tid, points, gd, gf) in enumerate(rows, start=1):
        results = stats[tid]["results"]
        win_streak = unbeaten = loss_streak = 0
        for code in reversed(results):
            if code == "W" and loss_streak == 0 and unbeaten == win_streak:
                win_streak += 1
                unbeaten += 1
            elif code == "D" and loss_streak == 0:
                unbeaten += 1
                break
            elif code == "L" and win_streak == 0 and unbeaten == 0:
                loss_streak += 1
            else:
                break

        table[tid] = TeamStandingsSnapshot(
            team_id=tid,
            position=pos,
            points=points,
            played=stats[tid]["played"],
            goals_for=stats[tid]["gf"],
            goals_against=stats[tid]["ga"],
            goal_difference=gd,
            win_streak=win_streak,
            unbeaten_streak=unbeaten,
            loss_streak=loss_streak,
        )
    return table


def get_team_standings(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    total_teams: int = 20,
) -> TeamStandingsSnapshot:
    table = compute_standings_table(dataset, as_of)
    if team_id in table:
        return table[team_id]
    return TeamStandingsSnapshot(
        team_id=team_id,
        position=total_teams,
        points=0,
        played=0,
        goals_for=0,
        goals_against=0,
        goal_difference=0,
        win_streak=0,
        unbeaten_streak=0,
        loss_streak=0,
    )
