"""Importanza approssimata feature da pesi softmax."""

from __future__ import annotations

import json
from pathlib import Path

from src.config import MODELS_DIR
from src.training.softmax import CLASSES, FeatureTrainedArtifact


def compute_feature_importance(artifact: FeatureTrainedArtifact) -> list[dict]:
    """Importanza = somma |peso| sulle classi HOME/DRAW/AWAY."""
    rows: list[dict] = []
    for index, name in enumerate(artifact.feature_names):
        importance = sum(
            abs(artifact.weights[class_name][index]) for class_name in CLASSES
        )
        rows.append({"feature_name": name, "importance": float(importance)})
    rows.sort(key=lambda row: row["importance"], reverse=True)
    return rows


def top_feature_importance(artifact: FeatureTrainedArtifact, n: int = 20) -> list[dict]:
    return compute_feature_importance(artifact)[: max(n, 0)]


def save_feature_importance(
    artifact: FeatureTrainedArtifact,
    *,
    path: Path | None = None,
) -> Path:
    target = path or (MODELS_DIR / f"feature_trained_{artifact.league_id}_importance.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "league_id": artifact.league_id,
        "feature_policy": artifact.feature_policy,
        "feature_count": len(artifact.feature_names),
        "importance": compute_feature_importance(artifact),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target
