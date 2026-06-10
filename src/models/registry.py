"""Registry modelli previsionali."""

from __future__ import annotations

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.models.base import BaseModel
from src.models.dixon_coles import DixonColesModel
from src.models.elo import EloModel
from src.models.ensemble import EnsembleModel
from src.models.feature_model import FeatureModel
from src.models.poisson import PoissonModel


def build_base_models(settings: Settings, dataset: MatchDataset) -> list[BaseModel]:
    return [
        PoissonModel(settings),
        DixonColesModel(settings),
        EloModel(settings, dataset),
        FeatureModel(),
    ]


def build_ensemble(settings: Settings, dataset: MatchDataset) -> EnsembleModel:
    return EnsembleModel.from_settings(settings, build_base_models(settings, dataset))


def get_model_by_name(
    name: str,
    settings: Settings,
    dataset: MatchDataset,
) -> BaseModel:
    if name == "ensemble":
        return build_ensemble(settings, dataset)
    for model in build_base_models(settings, dataset):
        if model.name == name:
            return model
    raise ValueError(f"Modello sconosciuto: {name}")
