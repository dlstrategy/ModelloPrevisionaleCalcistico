"""Predizione singola partita."""

from __future__ import annotations

from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.match import Match
from src.domain.models import Prediction
from src.features.match_context import build_match_context
from src.models.base import BaseModel
from src.models.calibration import ProbabilityCalibrator


def predict_match(
    dataset: MatchDataset,
    match: Match,
    model: BaseModel,
    settings: Settings,
    *,
    as_of: datetime | None = None,
    calibrator: ProbabilityCalibrator | None = None,
) -> Prediction:
    context = build_match_context(dataset, match, settings, as_of=as_of)
    probabilities = model.predict(context)
    if calibrator and calibrator.is_ready():
        probabilities = calibrator.calibrate(probabilities)

    return Prediction(
        fixture_id=match.id,
        home_team=match.home.team_name,
        away_team=match.away.team_name,
        probabilities=probabilities,
        model_name=model.name,
        starting_at=match.starting_at,
        metadata={
            "uncertain": probabilities.is_uncertain(settings.min_confidence_threshold),
        },
    )
