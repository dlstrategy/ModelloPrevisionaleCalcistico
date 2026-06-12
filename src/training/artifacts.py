"""Persistenza artifact feature_trained su JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.config import MODELS_DIR
from src.training.softmax import FeatureTrainedArtifact


def model_artifact_path(league_id: int, model_name: str = "feature_trained") -> Path:
    return MODELS_DIR / f"{model_name}_{league_id}.json"


def save_feature_trained_artifact(artifact: FeatureTrainedArtifact) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = model_artifact_path(artifact.league_id, artifact.model_name)
    payload = asdict(artifact)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_feature_trained_artifact(league_id: int) -> FeatureTrainedArtifact:
    path = model_artifact_path(league_id)
    if not path.exists():
        raise FileNotFoundError(
            f"Artifact feature_trained non trovato: {path}. "
            f"Esegui: python -m src.cli train --league {league_id} --model feature_trained"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return FeatureTrainedArtifact(
        model_name=payload["model_name"],
        model_version=payload["model_version"],
        league_id=int(payload["league_id"]),
        data_profile=payload["data_profile"],
        feature_names=tuple(payload["feature_names"]),
        scaler_means=dict(payload["scaler_means"]),
        scaler_stds=dict(payload["scaler_stds"]),
        weights={k: list(v) for k, v in payload["weights"].items()},
        bias=dict(payload["bias"]),
        training_matches=int(payload["training_matches"]),
        created_at=payload["created_at"],
        training_config=dict(payload["training_config"]),
        warnings=tuple(payload.get("warnings", ())),
    )
