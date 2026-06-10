"""Matrice punteggi condivisa tra modelli basati su Poisson."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.domain.models import OutcomeProbabilities


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam**k) / math.factorial(k)


@dataclass(frozen=True)
class ScoreMatrix:
    matrix: list[list[float]]
    lambda_home: float
    lambda_away: float

    @classmethod
    def from_lambdas(cls, lambda_home: float, lambda_away: float, max_goals: int) -> ScoreMatrix:
        matrix = [
            [poisson_pmf(hg, lambda_home) * poisson_pmf(ag, lambda_away) for ag in range(max_goals + 1)]
            for hg in range(max_goals + 1)
        ]
        return cls(matrix=matrix, lambda_home=lambda_home, lambda_away=lambda_away)

    def to_outcome_probabilities(self) -> OutcomeProbabilities:
        p_home = p_draw = p_away = 0.0
        for hg, row in enumerate(self.matrix):
            for ag, prob in enumerate(row):
                if hg > ag:
                    p_home += prob
                elif hg == ag:
                    p_draw += prob
                else:
                    p_away += prob
        return OutcomeProbabilities.normalize(p_home, p_draw, p_away)

    def apply_adjustment(
        self,
        adjuster: callable[[int, int, float], float],
    ) -> ScoreMatrix:
        adjusted = [
            [prob * adjuster(hg, ag, prob) for ag, prob in enumerate(row)]
            for hg, row in enumerate(self.matrix)
        ]
        return ScoreMatrix(matrix=adjusted, lambda_home=self.lambda_home, lambda_away=self.lambda_away)

    def normalized(self) -> ScoreMatrix:
        total = sum(sum(row) for row in self.matrix)
        if total <= 0:
            return self
        return ScoreMatrix(
            matrix=[[cell / total for cell in row] for row in self.matrix],
            lambda_home=self.lambda_home,
            lambda_away=self.lambda_away,
        )
