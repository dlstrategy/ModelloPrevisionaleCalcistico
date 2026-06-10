"""Predizioni per giornata/data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.config import PREDICTIONS_DIR, Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.match import Match
from src.domain.models import Prediction
from src.models.base import BaseModel
from src.prediction.predict_match import predict_match


def predict_round(
    dataset: MatchDataset,
    matches: list[Match],
    model: BaseModel,
    settings: Settings,
    *,
    as_of: datetime | None = None,
) -> list[Prediction]:
    return [predict_match(dataset, match, model, settings, as_of=as_of) for match in matches]


def save_predictions(predictions: list[Prediction], output_path: Path) -> None:
    payload = [
        {
            "fixture_id": p.fixture_id,
            "home_team": p.home_team,
            "away_team": p.away_team,
            "starting_at": p.starting_at.isoformat() if p.starting_at else None,
            "model": p.model_name,
            "probabilities": p.probabilities.as_dict(),
            "pick": p.pick.value,
            "confidence": p.confidence,
            "metadata": p.metadata,
        }
        for p in predictions
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def default_output_path(date_str: str) -> Path:
    return PREDICTIONS_DIR / f"predictions_{date_str}.json"
