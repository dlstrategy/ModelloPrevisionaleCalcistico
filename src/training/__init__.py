"""Training offline — dataset, softmax regression, artifact."""

from src.training.artifacts import (
    load_feature_trained_artifact,
    model_artifact_path,
    save_feature_trained_artifact,
)
from src.training.dataset import TrainingSample, build_training_samples
from src.training.softmax import (
    FeatureScaler,
    FeatureTrainedArtifact,
    SoftmaxTrainingConfig,
    fit_scaler,
    train_softmax_model,
    transform_features,
)

__all__ = [
    "FeatureScaler",
    "FeatureTrainedArtifact",
    "SoftmaxTrainingConfig",
    "TrainingSample",
    "build_training_samples",
    "fit_scaler",
    "load_feature_trained_artifact",
    "model_artifact_path",
    "save_feature_trained_artifact",
    "train_softmax_model",
    "transform_features",
]
