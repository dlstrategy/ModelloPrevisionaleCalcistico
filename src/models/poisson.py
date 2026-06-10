"""Modello Poisson per mercato 1X2."""

from __future__ import annotations

from src.config import Settings
from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext
from src.models.base import BaseModel
from src.models.score_matrix import ScoreMatrix


class PoissonModel(BaseModel):
    name = "poisson"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.max_goals = settings.poisson_max_goals

    def _lambdas(self, context: MatchContext) -> tuple[float, float]:
        home = context.home_strength
        away = context.away_strength
        lambda_home = home.attack_home * away.defense_away * context.home_advantage
        lambda_away = away.attack_away * home.defense_home
        if context.lineup_impact:
            li = context.lineup_impact
            lambda_home *= li.home_offensive_quality / max(li.away_defensive_quality, 0.1)
            lambda_away *= li.away_offensive_quality / max(li.home_defensive_quality, 0.1)
        return lambda_home, lambda_away

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        lambda_home, lambda_away = self._lambdas(context)
        matrix = ScoreMatrix.from_lambdas(lambda_home, lambda_away, self.max_goals)
        return matrix.to_outcome_probabilities()
