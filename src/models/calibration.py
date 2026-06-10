"""Calibrazione probabilità."""

from __future__ import annotations

import math

from src.config import Settings
from src.domain.models import OutcomeProbabilities


class TemperatureCalibrator:
    """Temperature scaling per ridurre overconfidence."""

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = max(temperature, 0.05)

    @classmethod
    def from_settings(cls, settings: Settings) -> TemperatureCalibrator:
        return cls(settings.calibration_temperature)

    def is_ready(self) -> bool:
        return abs(self.temperature - 1.0) > 1e-6

    def calibrate(self, probabilities: OutcomeProbabilities) -> OutcomeProbabilities:
        if not self.is_ready():
            return probabilities

        def scale(p: float) -> float:
            return math.exp(math.log(max(p, 1e-15)) / self.temperature)

        return OutcomeProbabilities.normalize(
            scale(probabilities.home),
            scale(probabilities.draw),
            scale(probabilities.away),
        )


class ProbabilityCalibrator(TemperatureCalibrator):
    """Alias per compatibilità."""
