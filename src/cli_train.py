"""Comando train — allenamento offline feature_trained."""

from __future__ import annotations

import sys

from src.config import Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.sync import load_dataset
from src.training.artifacts import save_feature_trained_artifact
from src.training.dataset import build_training_samples, training_samples_insufficient_message
from src.training.feature_importance import save_feature_importance, top_feature_importance
from src.training.feature_policy import (
    apply_feature_policy_to_sample,
    collect_feature_names,
    parse_feature_policy,
    select_features_for_policy,
)
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
    feature_policy: str = "full",
    clip_value: float | None = None,
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
        policy = parse_feature_policy(feature_policy)
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
    insufficient = training_samples_insufficient_message(samples, min_finished_matches=10)
    if insufficient:
        print(f"Warning: {insufficient}", file=sys.stderr)

    resolved_l2 = l2 if l2 is not None else policy.default_l2
    resolved_clip = clip_value if clip_value is not None else policy.default_clip_value
    config = SoftmaxTrainingConfig(
        epochs=epochs if epochs is not None else SoftmaxTrainingConfig().epochs,
        learning_rate=(
            learning_rate if learning_rate is not None else SoftmaxTrainingConfig().learning_rate
        ),
        l2=resolved_l2,
        min_samples=min_samples if min_samples is not None else SoftmaxTrainingConfig().min_samples,
        clip_value=resolved_clip,
    )

    try:
        original_count = len(collect_feature_names(samples))
        selected_names, selection_warnings = select_features_for_policy(samples, policy)
        filtered_samples = [
            apply_feature_policy_to_sample(sample, selected_names) for sample in samples
        ]
        artifact = train_softmax_model(
            filtered_samples,
            league_id=league_id,
            data_profile=profile_name,
            config=config,
            feature_names=selected_names,
            feature_policy=policy.name,
            original_feature_count=original_count,
            feature_selection_warnings=tuple(selection_warnings),
            regularization_notes=(f"train_policy={policy.name}",),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    path = save_feature_trained_artifact(artifact)
    importance_path = save_feature_importance(artifact)
    top_features = top_feature_importance(artifact, n=10)

    print(f"Training {model_name} — league {league_id}")
    print(f"Profile: {profile_name}")
    print(f"Feature policy: {artifact.feature_policy}")
    print(f"Original features: {artifact.original_feature_count}")
    print(f"Selected features: {artifact.selected_feature_count}")
    print(f"Clip value: {artifact.clip_value}")
    print(f"L2: {config.l2}")
    print(f"Training matches: {artifact.training_matches}")
    if artifact.feature_selection_warnings:
        print(f"Feature selection warnings: {', '.join(artifact.feature_selection_warnings)}")
    if artifact.warnings:
        print(f"Warnings: {', '.join(artifact.warnings)}")
    else:
        print("Warnings: none")
    print("Top 10 features by importance:")
    for row in top_features:
        print(f"  {row['feature_name']}: {row['importance']:.4f}")
    print(f"Saved: {path}")
    print(f"Importance: {importance_path}")
    return 0
