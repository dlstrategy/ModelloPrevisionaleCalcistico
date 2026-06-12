"""Softmax regression multinomial — training e scaler."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.training.dataset import TrainingSample

CLASSES: tuple[str, ...] = ("HOME", "DRAW", "AWAY")
MODEL_VERSION = "2j.0"
TRAINING_ALGORITHM = "softmax_regression_python"


@dataclass(frozen=True)
class FeatureScaler:
    means: dict[str, float]
    stds: dict[str, float]


@dataclass(frozen=True)
class SoftmaxTrainingConfig:
    learning_rate: float = 0.05
    epochs: int = 300
    l2: float = 0.001
    min_samples: int = 20
    clip_value: float | None = None


@dataclass(frozen=True)
class FeatureTrainedArtifact:
    model_name: str
    model_version: str
    league_id: int
    data_profile: str
    feature_names: tuple[str, ...]
    scaler_means: dict[str, float]
    scaler_stds: dict[str, float]
    weights: dict[str, list[float]]
    bias: dict[str, float]
    training_matches: int
    created_at: str
    training_config: dict
    warnings: tuple[str, ...] = ()
    training_algorithm: str = TRAINING_ALGORITHM
    feature_policy: str = "full"
    selected_feature_count: int = 0
    original_feature_count: int = 0
    feature_selection_warnings: tuple[str, ...] = ()
    regularization_notes: tuple[str, ...] = ()
    clip_value: float | None = None


def _safe_float(value: float) -> float:
    if value != value or math.isinf(value):  # NaN or inf
        return 0.0
    return value


def _collect_feature_names(samples: list[TrainingSample]) -> list[str]:
    names: set[str] = set()
    for sample in samples:
        names.update(sample.features.keys())
    return sorted(names)


def fit_scaler(samples: list[TrainingSample], feature_names: list[str]) -> FeatureScaler:
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    n = len(samples)
    if n == 0:
        return FeatureScaler(means={}, stds={})

    for name in feature_names:
        values = [_safe_float(sample.features.get(name, 0.0)) for sample in samples]
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance)
        if std < 1e-8:
            std = 1.0
        means[name] = mean
        stds[name] = std

    return FeatureScaler(means=means, stds=stds)


def transform_features(
    features: dict[str, float],
    feature_names: list[str],
    scaler: FeatureScaler,
    *,
    clip_value: float | None = None,
) -> list[float]:
    vector: list[float] = []
    for name in feature_names:
        raw = _safe_float(features.get(name, 0.0))
        mean = scaler.means.get(name, 0.0)
        std = scaler.stds.get(name, 1.0)
        if std < 1e-8:
            std = 1.0
        scaled = (raw - mean) / std
        if clip_value is not None:
            scaled = max(-clip_value, min(clip_value, scaled))
        vector.append(scaled)
    return vector


def _softmax_logits(logits: list[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps)
    if total <= 0:
        return [1 / 3, 1 / 3, 1 / 3]
    return [e / total for e in exps]


def _init_weights(n_features: int) -> tuple[list[list[float]], list[float]]:
    weights = [[0.0] * n_features for _ in CLASSES]
    bias = [0.0] * len(CLASSES)
    return weights, bias


def train_softmax_model(
    samples: list[TrainingSample],
    *,
    league_id: int,
    data_profile: str,
    config: SoftmaxTrainingConfig | None = None,
    feature_names: list[str] | None = None,
    feature_policy: str = "full",
    original_feature_count: int | None = None,
    feature_selection_warnings: tuple[str, ...] = (),
    regularization_notes: tuple[str, ...] = (),
) -> FeatureTrainedArtifact:
    cfg = config or SoftmaxTrainingConfig()
    warnings: list[str] = list(feature_selection_warnings)

    if len(samples) < 3:
        raise ValueError(
            f"Training insufficiente: servono almeno 3 match finiti, trovati {len(samples)}."
        )

    class_set = {s.label for s in samples}
    if len(class_set) < 2:
        raise ValueError(
            f"Training insufficiente: servono almeno 2 classi (HOME/DRAW/AWAY), "
            f"trovate {len(class_set)} ({', '.join(sorted(class_set))})."
        )

    if len(samples) < cfg.min_samples:
        warnings.append(
            f"dataset piccolo ({len(samples)} sample, minimo consigliato {cfg.min_samples})"
        )
        warnings.append("modello sperimentale")

    all_names = _collect_feature_names(samples)
    orig_count = original_feature_count if original_feature_count is not None else len(all_names)
    selected_names = feature_names if feature_names is not None else all_names
    if not selected_names:
        raise ValueError("Nessuna feature disponibile nei sample di training.")

    reg_notes = list(regularization_notes)
    if cfg.clip_value is not None:
        reg_notes.append(f"feature_clip={cfg.clip_value}")
    if cfg.l2 > 0:
        reg_notes.append(f"l2={cfg.l2}")

    scaler = fit_scaler(samples, selected_names)
    n_features = len(selected_names)
    weights, bias = _init_weights(n_features)
    class_index = {label: idx for idx, label in enumerate(CLASSES)}

    for _epoch in range(cfg.epochs):
        for sample in samples:
            x = transform_features(
                sample.features,
                selected_names,
                scaler,
                clip_value=cfg.clip_value,
            )
            logits = [
                sum(weights[c][j] * x[j] for j in range(n_features)) + bias[c]
                for c in range(len(CLASSES))
            ]
            probs = _softmax_logits(logits)
            y = class_index[sample.label]

            for c in range(len(CLASSES)):
                grad = probs[c]
                if c == y:
                    grad -= 1.0
                for j in range(n_features):
                    weights[c][j] -= cfg.learning_rate * (grad * x[j] + cfg.l2 * weights[c][j])
                bias[c] -= cfg.learning_rate * grad

    weights_dict = {CLASSES[i]: weights[i] for i in range(len(CLASSES))}
    bias_dict = {CLASSES[i]: bias[i] for i in range(len(CLASSES))}

    return FeatureTrainedArtifact(
        model_name="feature_trained",
        model_version=MODEL_VERSION,
        league_id=league_id,
        data_profile=data_profile,
        feature_names=tuple(selected_names),
        scaler_means=dict(scaler.means),
        scaler_stds=dict(scaler.stds),
        weights=weights_dict,
        bias=bias_dict,
        training_matches=len(samples),
        created_at=datetime.now(timezone.utc).isoformat(),
        training_config={
            "learning_rate": cfg.learning_rate,
            "epochs": cfg.epochs,
            "l2": cfg.l2,
            "min_samples": cfg.min_samples,
            "clip_value": cfg.clip_value,
            "feature_policy": feature_policy,
        },
        warnings=tuple(dict.fromkeys(warnings)),
        training_algorithm=TRAINING_ALGORITHM,
        feature_policy=feature_policy,
        selected_feature_count=len(selected_names),
        original_feature_count=orig_count,
        feature_selection_warnings=tuple(feature_selection_warnings),
        regularization_notes=tuple(dict.fromkeys(reg_notes)),
        clip_value=cfg.clip_value,
    )


def predict_proba_from_artifact(
    artifact: FeatureTrainedArtifact,
    features: dict[str, float],
) -> tuple[float, float, float]:
    """Restituisce (P(home), P(draw), P(away))."""
    feature_names = list(artifact.feature_names)
    scaler = FeatureScaler(means=artifact.scaler_means, stds=artifact.scaler_stds)
    clip = artifact.clip_value
    if clip is None:
        clip = artifact.training_config.get("clip_value")
    x = transform_features(features, feature_names, scaler, clip_value=clip)
    n_features = len(feature_names)

    logits = [
        sum(artifact.weights[CLASSES[c]][j] * x[j] for j in range(n_features))
        + artifact.bias[CLASSES[c]]
        for c in range(len(CLASSES))
    ]
    probs = _softmax_logits(logits)
    return probs[0], probs[1], probs[2]
