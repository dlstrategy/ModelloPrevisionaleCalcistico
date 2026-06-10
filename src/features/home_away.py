"""Feature casa/trasferta: riposo e congestione calendario."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.data_pipeline.dataset_builder import MatchDataset


@dataclass(frozen=True)
class ScheduleSnapshot:
    team_id: int
    days_since_last_match: float | None
    matches_last_14_days: int


def compute_schedule_snapshot(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
) -> ScheduleSnapshot:
    history = dataset.team_history(team_id, as_of)
    days_since: float | None = None
    if history:
        delta = as_of - history[-1].starting_at
        days_since = delta.total_seconds() / 86400.0

    window_start = as_of.timestamp() - 14 * 86400
    recent_count = sum(
        1 for m in history if m.starting_at.timestamp() >= window_start
    )

    return ScheduleSnapshot(
        team_id=team_id,
        days_since_last_match=days_since,
        matches_last_14_days=recent_count,
    )
