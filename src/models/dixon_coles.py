"""Modello Dixon-Coles con correzione tau sui punteggi bassi."""

from __future__ import annotations

from src.config import Settings
from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext
from src.models.base import BaseModel
from src.models.poisson import PoissonModel
from src.models.score_matrix import ScoreMatrix


def dixon_coles_tau(hg: int, ag: int, lambda_home: float, lambda_away: float, rho: float) -> float:
    if hg == 0 and ag == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if hg == 0 and ag == 1:
        return 1.0 + lambda_home * rho
    if hg == 1 and ag == 0:
        return 1.0 + lambda_away * rho
    if hg == 1 and ag == 1:
        return 1.0 - rho
    return 1.0


class DixonColesModel(BaseModel):
    name = "dixon_coles"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._poisson = PoissonModel(settings)
        self.rho = settings.dixon_coles_rho

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        lambda_home, lambda_away = self._poisson._lambdas(context)
        matrix = ScoreMatrix.from_lambdas(
            lambda_home, lambda_away, self.settings.poisson_max_goals
        )

        def adjuster(hg: int, ag: int, _prob: float) -> float:
            return dixon_coles_tau(hg, ag, lambda_home, lambda_away, self.rho)

        return matrix.apply_adjustment(adjuster).normalized().to_outcome_probabilities()
