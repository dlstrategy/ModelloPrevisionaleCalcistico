"""Walk-forward backtest — simulazione predizioni nel tempo."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.config import BACKTESTS_DIR, Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_pipeline.scope import DataScope, scope_metadata_dict
from src.domain.enums import MatchOutcome
from src.domain.models import Prediction
from src.models.base import BaseModel
from src.prediction.predict_match import predict_match

# I modelli attuali non vengono ri-addestrati per finestra: ogni predizione rispetta
# as_of=match.starting_at mentre train_matches definisce solo la cornice temporale.
TRAINING_MODE = "as_of_simulation_no_refit"


@dataclass(frozen=True)
class WalkForwardWindow:
    window_index: int
    train_until: str
    test_from: str
    test_to: str
    train_matches: int
    test_matches: int
    metrics: BacktestMetrics
    predictions: tuple[Prediction, ...]
    actuals: tuple[MatchOutcome, ...]
    train_from: str | None = None
    training_features: int | None = None
    training_warnings: tuple[str, ...] | None = None
    feature_policy: str | None = None
    original_feature_count: int | None = None
    feature_selection_warnings: tuple[str, ...] | None = None
    clip_value: float | None = None
    training_l2: float | None = None


@dataclass(frozen=True)
class WalkForwardReport:
    model_name: str
    league_id: int
    generated_at: str
    min_train_matches: int
    test_window_size: int
    step_size: int
    training_mode: str
    total_tested_matches: int
    windows: tuple[WalkForwardWindow, ...]
    aggregate_metrics: BacktestMetrics
    data_profile: str | None = None

    def as_dict(self) -> dict:
        def window_dict(window: WalkForwardWindow) -> dict:
            payload = {
                "window_index": window.window_index,
                "train_until": window.train_until,
                "test_from": window.test_from,
                "test_to": window.test_to,
                "train_matches": window.train_matches,
                "test_matches": window.test_matches,
                "metrics": window.metrics.as_dict(),
                "predictions": [
                    {
                        "fixture_id": p.fixture_id,
                        "home_team": p.home_team,
                        "away_team": p.away_team,
                        "starting_at": p.starting_at.isoformat() if p.starting_at else None,
                        "probabilities": p.probabilities.as_dict(),
                        "pick": p.pick.value,
                        "confidence": p.confidence,
                        "actual": a.value,
                        "correct": p.pick == a,
                    }
                    for p, a in zip(window.predictions, window.actuals)
                ],
            }
            if window.train_from is not None:
                payload["train_from"] = window.train_from
            if window.training_features is not None:
                payload["training_features"] = window.training_features
            if window.training_warnings is not None:
                payload["training_warnings"] = list(window.training_warnings)
            if window.feature_policy is not None:
                payload["feature_policy"] = window.feature_policy
            if window.original_feature_count is not None:
                payload["original_feature_count"] = window.original_feature_count
            if window.feature_selection_warnings is not None:
                payload["feature_selection_warnings"] = list(window.feature_selection_warnings)
            if window.clip_value is not None:
                payload["clip_value"] = window.clip_value
            if window.training_l2 is not None:
                payload["training_l2"] = window.training_l2
            return payload

        result = {
            "model_name": self.model_name,
            "league_id": self.league_id,
            "data_scope": scope_metadata_dict(DataScope(league_id=self.league_id)),
            "generated_at": self.generated_at,
            "training_mode": self.training_mode,
            "min_train_matches": self.min_train_matches,
            "test_window_size": self.test_window_size,
            "step_size": self.step_size,
            "total_tested_matches": self.total_tested_matches,
            "aggregate_metrics": self.aggregate_metrics.as_dict(),
            "windows": [window_dict(w) for w in self.windows],
        }
        if self.data_profile is not None:
            result["data_profile"] = self.data_profile
        return result


def run_walk_forward(
    dataset: MatchDataset,
    model: BaseModel,
    settings: Settings,
    *,
    min_train_matches: int = 10,
    test_window_size: int = 5,
    step_size: int = 5,
) -> WalkForwardReport:
    """Walk-forward pre-kickoff: simulazione temporale senza refit per finestra.

    train_matches delimita la cornice storica di ogni window ma i modelli attuali
    (Poisson, Elo, Feature, Ensemble) non vengono ri-addestrati: usano il dataset
    completo con as_of=match.starting_at. In futuro train_matches alimenterà
    modelli trainabili.
    """
    finished = [
        m
        for m in dataset.matches
        if m.is_finished and m.actual_outcome is not None
    ]
    finished.sort(key=lambda m: m.starting_at)

    windows: list[WalkForwardWindow] = []
    all_predictions: list[Prediction] = []
    all_actuals: list[MatchOutcome] = []

    train_end_idx = min_train_matches
    window_index = 0

    while train_end_idx + test_window_size <= len(finished):
        train_matches = finished[:train_end_idx]
        test_matches = finished[train_end_idx : train_end_idx + test_window_size]

        predictions: list[Prediction] = []
        actuals: list[MatchOutcome] = []
        for match in test_matches:
            pred = predict_match(
                dataset,
                match,
                model,
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
            )
        )
        all_predictions.extend(predictions)
        all_actuals.extend(actuals)

        window_index += 1
        train_end_idx += step_size

    aggregate = compute_metrics(all_predictions, all_actuals)

    return WalkForwardReport(
        model_name=model.name,
        league_id=dataset.league_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        min_train_matches=min_train_matches,
        test_window_size=test_window_size,
        step_size=step_size,
        training_mode=TRAINING_MODE,
        total_tested_matches=len(all_predictions),
        windows=tuple(windows),
        aggregate_metrics=aggregate,
    )


def save_walk_forward_report(report: WalkForwardReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"walk_forward_{report.model_name}_{report.league_id}.json"
    csv_path = output_dir / f"walk_forward_{report.model_name}_{report.league_id}.csv"

    json_path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "window_index",
                "fixture_id",
                "starting_at",
                "home_team",
                "away_team",
                "p_home",
                "p_draw",
                "p_away",
                "pick",
                "confidence",
                "actual",
                "correct",
            ]
        )
        for window in report.windows:
            for pred, actual in zip(window.predictions, window.actuals):
                writer.writerow(
                    [
                        window.window_index,
                        pred.fixture_id,
                        pred.starting_at.isoformat(sep=" ") if pred.starting_at else "",
                        pred.home_team,
                        pred.away_team,
                        f"{pred.probabilities.home:.6f}",
                        f"{pred.probabilities.draw:.6f}",
                        f"{pred.probabilities.away:.6f}",
                        pred.pick.value,
                        f"{pred.confidence:.6f}",
                        actual.value,
                        pred.pick == actual,
                    ]
                )

    return json_path, csv_path
