"""Strength of schedule — qualità avversari recenti."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.features.advanced_strength import _opponent_id
from src.features.team_strength import compute_team_strengths


@dataclass(frozen=True)
class ScheduleStrengthSnapshot:
    team_id: int
    avg_opponent_rating_last_5: float
    avg_opponent_rating_last_10: float
    points_vs_expected_last_5: float
    xg_diff_vs_opponent_strength: float


def _expected_points(opponent_rating: float) -> float:
    """Punti attesi vs avversario (0-3) da strength relativa."""
    return max(0.0, min(3.0, 1.5 + (1.0 - opponent_rating) * 0.8))


def _actual_points(dataset: MatchDataset, match, team_id: int) -> float:
    scored, conceded = dataset.team_goals(team_id, match)
    if scored > conceded:
        return 3.0
    if scored == conceded:
        return 1.0
    return 0.0


def compute_schedule_strength(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    settings: Settings,
    league_id: int,
) -> ScheduleStrengthSnapshot:
    from src.features.xg_features import get_team_xg_profile

    history = dataset.team_history(team_id, as_of)
    last_5 = history[-5:]
    last_10 = history[-10:]

    def avg_opp_rating(matches: list) -> float:
        if not matches:
            return 1.0
        total = 0.0
        for match in matches:
            opp_id = _opponent_id(match, team_id)
            opp = compute_team_strengths(dataset, opp_id, match.starting_at, settings)
            total += (opp.attack + opp.defense) / 2.0
        return total / len(matches)

    pve = 0.0
    for match in last_5:
        opp_id = _opponent_id(match, team_id)
        opp_rating = (
            compute_team_strengths(dataset, opp_id, match.starting_at, settings).attack
            + compute_team_strengths(dataset, opp_id, match.starting_at, settings).defense
        ) / 2.0
        pve += _actual_points(dataset, match, team_id) - _expected_points(opp_rating)

    xg_profile = get_team_xg_profile(dataset, team_id, as_of, league_id)
    xg_diff_adj = xg_profile.xg_diff_avg * avg_opp_rating(last_5)

    return ScheduleStrengthSnapshot(
        team_id=team_id,
        avg_opponent_rating_last_5=avg_opp_rating(last_5),
        avg_opponent_rating_last_10=avg_opp_rating(last_10),
        points_vs_expected_last_5=pve / max(len(last_5), 1),
        xg_diff_vs_opponent_strength=xg_diff_adj,
    )


def schedule_strength_to_features(prefix: str, snap: ScheduleStrengthSnapshot) -> dict[str, float]:
    return {
        f"{prefix}_avg_opponent_rating_last_5": snap.avg_opponent_rating_last_5,
        f"{prefix}_avg_opponent_rating_last_10": snap.avg_opponent_rating_last_10,
        f"{prefix}_points_vs_expected_last_5": snap.points_vs_expected_last_5,
        f"{prefix}_xg_diff_vs_opponent_strength": snap.xg_diff_vs_opponent_strength,
    }
