"""Walk-forward con refit reale per feature_trained."""

from __future__ import annotations

from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.backtesting.walk_forward import WalkForwardReport, WalkForwardWindow
from src.config import Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import MatchOutcome
from src.domain.models import Prediction
from src.models.feature_trained import FeatureTrainedModel
from src.prediction.predict_match import predict_match
from src.training.dataset import build_training_samples
from src.training.softmax import SoftmaxTrainingConfig, train_softmax_model

TRAINING_MODE_REFIT = "walk_forward_refit"


def run_walk_forward_refit(
    dataset: MatchDataset,
    settings: Settings,
    *,
    profile: str | None = None,
    min_train_matches: int = 10,
    test_window_size: int = 5,
    step_size: int = 5,
) -> WalkForwardReport:
    """Walk-forward con refit per finestra — valutazione onesta per feature_trained."""
    from datetime import datetime, timezone

    profile_name = parse_data_profile(profile or settings.data_profile)
    finished = [
        m
        for m in dataset.matches
        if m.is_finished and m.actual_outcome is not None
    ]
    finished.sort(key=lambda m: m.starting_at)

    windows: list[WalkForwardWindow] = []
    all_predictions: list[Prediction] = []
    all_actuals: list[MatchOutcome] = []

    train_config = SoftmaxTrainingConfig(epochs=200, min_samples=5)
    train_end_idx = min_train_matches
    window_index = 0

    while train_end_idx + test_window_size <= len(finished):
        train_matches = finished[:train_end_idx]
        test_matches = finished[train_end_idx : train_end_idx + test_window_size]
        train_ids = frozenset(m.id for m in train_matches)
        test_ids = frozenset(m.id for m in test_matches)
        assert train_ids.isdisjoint(test_ids)

        train_samples = build_training_samples(
            dataset,
            settings,
            profile=profile_name,
            only_match_ids=train_ids,
        )

        artifact = train_softmax_model(
            train_samples,
            league_id=dataset.league_id,
            data_profile=profile_name,
            config=train_config,
        )
        window_model = FeatureTrainedModel.from_artifact(settings, dataset, artifact)

        predictions: list[Prediction] = []
        actuals: list[MatchOutcome] = []
        for match in test_matches:
            pred = predict_match(
                dataset,
                match,
                window_model,
                settings,
                as_of=match.starting_at,
            )
            predictions.append(pred)
            actuals.append(match.actual_outcome)  # type: ignore[arg-type]

        metrics = compute_metrics(predictions, actuals)
        windows.append(
            WalkForwardWindow(
                window_index=window_index,
                train_until=train_matches[-1].starting_at.isoformat(sep=" "),
                test_from=test_matches[0].starting_at.isoformat(sep=" "),
                test_to=test_matches[-1].starting_at.isoformat(sep=" "),
                train_matches=len(train_matches),
                test_matches=len(test_matches),
                metrics=metrics,
                predictions=tuple(predictions),
                actuals=tuple(actuals),
                train_from=train_matches[0].starting_at.isoformat(sep=" "),
                training_features=len(artifact.feature_names),
                training_warnings=artifact.warnings,
            )
        )
        all_predictions.extend(predictions)
        all_actuals.extend(actuals)

        window_index += 1
        train_end_idx += step_size

    aggregate = compute_metrics(all_predictions, all_actuals)

    return WalkForwardReport(
        model_name="feature_trained",
        league_id=dataset.league_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        min_train_matches=min_train_matches,
        test_window_size=test_window_size,
        step_size=step_size,
        training_mode=TRAINING_MODE_REFIT,
        total_tested_matches=len(all_predictions),
        windows=tuple(windows),
        aggregate_metrics=aggregate,
        data_profile=profile_name,
    )
