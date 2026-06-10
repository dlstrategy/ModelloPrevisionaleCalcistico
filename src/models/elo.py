"""Modello Elo → probabilità 1/X/2."""

from __future__ import annotations

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext
from src.models.base import BaseModel
from src.models.elo_ratings import build_elo_table


class EloModel(BaseModel):
    name = "elo"

    def __init__(self, settings: Settings, dataset: MatchDataset | None = None) -> None:
        self.settings = settings
        self._dataset = dataset
        self._base_draw = 0.26

    def with_dataset(self, dataset: MatchDataset) -> EloModel:
        return EloModel(self.settings, dataset)

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        if self._dataset is None:
            raise RuntimeError("EloModel richiede dataset per calcolo rating")

        table = build_elo_table(self._dataset, context.as_of, self.settings)
        rh = table.get(context.match.home.team_id, self.settings.elo_initial_rating)
        ra = table.get(context.match.away.team_id, self.settings.elo_initial_rating)
        rh_adj = rh + self.settings.elo_home_advantage

        p_home_beats = table.expected_score(rh_adj, ra)
        p_away_beats = 1.0 - table.expected_score(ra, rh_adj)

        closeness = 1.0 - abs(p_home_beats - p_away_beats)
        p_draw = self._base_draw * (0.6 + 0.4 * closeness)
        p_home = p_home_beats * (1.0 - p_draw)
        p_away = p_away_beats * (1.0 - p_draw)

        return OutcomeProbabilities.normalize(p_home, p_draw, p_away)
