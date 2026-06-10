"""Modelli di output previsionale."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import MatchOutcome


@dataclass(frozen=True)
class OutcomeProbabilities:
    home: float
    draw: float
    away: float

    def __post_init__(self) -> None:
        total = self.home + self.draw + self.away
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Probabilities must sum to 1.0, got {total}")

    @classmethod
    def normalize(cls, home: float, draw: float, away: float) -> OutcomeProbabilities:
        total = home + draw + away
        if total <= 0:
            return cls(home=1 / 3, draw=1 / 3, away=1 / 3)
        return cls(home=home / total, draw=draw / total, away=away / total)

    def as_dict(self) -> dict[str, float]:
        return {"home": self.home, "draw": self.draw, "away": self.away}

    def pick(self) -> MatchOutcome:
        values = {
            MatchOutcome.HOME: self.home,
            MatchOutcome.DRAW: self.draw,
            MatchOutcome.AWAY: self.away,
        }
        return max(values, key=values.get)

    def confidence(self) -> float:
        return max(self.home, self.draw, self.away)

    def is_uncertain(self, threshold: float) -> bool:
        return self.confidence() < threshold


@dataclass
class Prediction:
    fixture_id: int
    home_team: str
    away_team: str
    probabilities: OutcomeProbabilities
    model_name: str
    starting_at: datetime | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def pick(self) -> MatchOutcome:
        return self.probabilities.pick()

    @property
    def confidence(self) -> float:
        return self.probabilities.confidence()
