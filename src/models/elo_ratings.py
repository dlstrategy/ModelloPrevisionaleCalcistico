"""Calcolo rating Elo da storico partite (no leakage)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import MatchOutcome, ParticipantLocation


@dataclass
class EloTable:
    ratings: dict[int, float] = field(default_factory=dict)

    def get(self, team_id: int, default: float) -> float:
        return self.ratings.get(team_id, default)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def update(
        self,
        home_id: int,
        away_id: int,
        outcome: MatchOutcome,
        settings: Settings,
    ) -> None:
        rh = self.get(home_id, settings.elo_initial_rating)
        ra = self.get(away_id, settings.elo_initial_rating)
        rh_adj = rh + settings.elo_home_advantage
        eh = self.expected_score(rh_adj, ra)
        ea = 1.0 - eh

        if outcome == MatchOutcome.HOME:
            sh, sa = 1.0, 0.0
        elif outcome == MatchOutcome.DRAW:
            sh, sa = 0.5, 0.5
        else:
            sh, sa = 0.0, 1.0

        k = settings.elo_k_factor
        self.ratings[home_id] = rh + k * (sh - eh)
        self.ratings[away_id] = ra + k * (sa - ea)


def build_elo_table(dataset: MatchDataset, as_of: datetime, settings: Settings) -> EloTable:
    table = EloTable()
    for match in dataset.finished_before(as_of):
        if match.actual_outcome is None:
            continue
        table.update(match.home.team_id, match.away.team_id, match.actual_outcome, settings)
    return table
