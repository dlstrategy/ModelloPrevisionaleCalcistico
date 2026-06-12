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
    enabled_groups = getattr(model, "enabled_groups", None)
    profile = getattr(model, "data_profile", None)
    context = build_match_context(
        dataset,
        match,
        settings,
        as_of=as_of,
        enabled_feature_groups=enabled_groups,
        profile=profile,
    )
    if not model.is_ready():
        raise RuntimeError(
            f"Modello {model.name} non pronto. "
            + (
                "Esegui: python -m src.cli train --league "
                f"{dataset.league_id} --model feature_trained"
                if model.name == "feature_trained"
                else "Verifica configurazione e dati."
            )
        )
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
