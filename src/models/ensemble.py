"""Ensemble di modelli — combinazione pesata probabilità 1/X/2."""

from __future__ import annotations

from src.config import Settings
from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext
from src.models.base import BaseModel
from src.models.calibration import TemperatureCalibrator


class EnsembleModel(BaseModel):
    name = "ensemble"

    def __init__(
        self,
        models: list[BaseModel],
        weights: list[float],
        calibrator: TemperatureCalibrator | None = None,
    ) -> None:
        ready = [(m, w) for m, w in zip(models, weights) if m.is_ready() and w > 0]
        if not ready:
            raise ValueError("Nessun modello pronto per l'ensemble")
        self._models = [m for m, _ in ready]
        self._weights = [w for _, w in ready]
        total = sum(self._weights)
        self._weights = [w / total for w in self._weights]
        self._calibrator = calibrator

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        models: list[BaseModel],
    ) -> EnsembleModel:
        weight_map = {
            "poisson": settings.ensemble_weight_poisson,
            "dixon_coles": settings.ensemble_weight_dixon_coles,
            "elo": settings.ensemble_weight_elo,
            "feature": settings.ensemble_weight_feature,
        }
        weights = [weight_map.get(m.name, 0.0) for m in models]
        calibrator = TemperatureCalibrator.from_settings(settings)
        return cls(models, weights, calibrator=calibrator)

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        home = draw = away = 0.0
        for model, weight in zip(self._models, self._weights):
            probs = model.predict(context)
            home += weight * probs.home
            draw += weight * probs.draw
            away += weight * probs.away
        result = OutcomeProbabilities.normalize(home, draw, away)
        if self._calibrator:
            result = self._calibrator.calibrate(result)
        return result
