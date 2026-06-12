"""Modello feature_trained — softmax regression allenata offline."""

from __future__ import annotations

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext
from src.models.base import BaseModel
from src.training.artifacts import load_feature_trained_artifact
from src.training.softmax import FeatureTrainedArtifact, predict_proba_from_artifact

_MISSING_MSG = (
    "Modello feature_trained non trovato. "
    "Esegui: python -m src.cli train --league 384 --model feature_trained"
)


class FeatureTrainedModel(BaseModel):
    name = "feature_trained"

    def __init__(self, settings: Settings, dataset: MatchDataset) -> None:
        self.settings = settings
        self.league_id = dataset.league_id
        self._artifact: FeatureTrainedArtifact | None = None
        try:
            self._artifact = load_feature_trained_artifact(dataset.league_id)
        except FileNotFoundError:
            pass

    @property
    def data_profile(self) -> str | None:
        return self._artifact.data_profile if self._artifact else None

    def is_ready(self) -> bool:
        return self._artifact is not None

    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        if self._artifact is None:
            raise RuntimeError(_MISSING_MSG)
        home, draw, away = predict_proba_from_artifact(
            self._artifact, context.feature_vector
        )
        return OutcomeProbabilities.normalize(home, draw, away)
