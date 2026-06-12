"""Comando train — allenamento offline feature_trained."""

from __future__ import annotations

import sys

from src.config import Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.sync import load_dataset
from src.training.artifacts import save_feature_trained_artifact
from src.training.dataset import build_training_samples
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model


def print_train(
    settings: Settings,
    league_id: int,
    *,
    model_name: str = "feature_trained",
    profile: str | None = None,
    epochs: int | None = None,
    learning_rate: float | None = None,
    l2: float | None = None,
    min_samples: int | None = None,
) -> int:
    if model_name != "feature_trained":
        print(
            f"Modello non supportato per train: {model_name!r}. "
            "Usa --model feature_trained.",
            file=sys.stderr,
        )
        return 1

    try:
        profile_name = parse_data_profile(profile or settings.data_profile)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        dataset = load_dataset(settings, league_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print(f"Esegui: python -m src.cli sync --league {league_id}", file=sys.stderr)
        return 1

    samples = build_training_samples(dataset, settings, profile=profile_name)
    config = SoftmaxTrainingConfig(
        epochs=epochs if epochs is not None else SoftmaxTrainingConfig().epochs,
        learning_rate=learning_rate if learning_rate is not None else SoftmaxTrainingConfig().learning_rate,
        l2=l2 if l2 is not None else SoftmaxTrainingConfig().l2,
        min_samples=min_samples if min_samples is not None else SoftmaxTrainingConfig().min_samples,
    )

    try:
        artifact = train_softmax_model(
            samples,
            league_id=league_id,
            data_profile=profile_name,
            config=config,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    path = save_feature_trained_artifact(artifact)

    print(f"Training {model_name} — league {league_id}")
    print(f"Profile: {profile_name}")
    print(f"Training matches: {artifact.training_matches}")
    print(f"Features: {len(artifact.feature_names)}")
    if artifact.warnings:
        print(f"Warnings: {', '.join(artifact.warnings)}")
    else:
        print("Warnings: none")
    print(f"Saved: {path}")
    return 0
