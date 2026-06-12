"""Registry modelli previsionali."""

from __future__ import annotations

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.models.base import BaseModel
from src.models.dixon_coles import DixonColesModel
from src.models.elo import EloModel
from src.models.ensemble import EnsembleModel
from src.features.feature_groups import ABLATION_VARIANTS
from src.models.feature_model import FeatureModel
from src.models.poisson import PoissonModel


def build_base_models(
    settings: Settings,
    dataset: MatchDataset,
    *,
    feature_groups: frozenset[str] | None = None,
) -> list[BaseModel]:
    return [
        PoissonModel(settings),
        DixonColesModel(settings),
        EloModel(settings, dataset),
        FeatureModel(enabled_groups=feature_groups),
    ]


def build_ensemble(
    settings: Settings,
    dataset: MatchDataset,
    *,
    feature_groups: frozenset[str] | None = None,
) -> EnsembleModel:
    return EnsembleModel.from_settings(
        settings, build_base_models(settings, dataset, feature_groups=feature_groups)
    )


def get_model_by_name(
    name: str,
    settings: Settings,
    dataset: MatchDataset,
    *,
    feature_groups: frozenset[str] | None = None,
) -> BaseModel:
    if name == "ensemble":
        return build_ensemble(settings, dataset, feature_groups=feature_groups)
    for model in build_base_models(settings, dataset, feature_groups=feature_groups):
        if model.name == name:
            return model
    raise ValueError(f"Modello sconosciuto: {name}")


def get_ablation_feature_groups(variant: str) -> frozenset[str]:
    if variant not in ABLATION_VARIANTS:
        raise ValueError(f"Variante ablation sconosciuta: {variant}")
    return ABLATION_VARIANTS[variant]
