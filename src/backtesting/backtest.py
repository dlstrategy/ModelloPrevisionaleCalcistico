"""Backtesting senza data leakage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.backtesting.metrics import BacktestMetrics, compute_metrics
from src.config import BACKTESTS_DIR, Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import MatchOutcome
from src.domain.models import Prediction
from src.models.base import BaseModel
from src.models.registry import build_base_models, build_ensemble
from src.prediction.predict_match import predict_match


@dataclass
class BacktestResult:
    model_name: str
    league_id: int
    metrics: BacktestMetrics
    predictions: list[Prediction]
    actuals: list[MatchOutcome]
    evaluation_mode: str | None = None
    training_leakage_risk: bool = False
    warning: str | None = None


IN_SAMPLE_ARTIFACT_WARNING = (
    "feature_trained artifact may have been trained on the same matches used for evaluation"
)


def run_backtest(
    dataset: MatchDataset,
    model: BaseModel,
    settings: Settings,
    *,
    max_matches: int | None = None,
) -> BacktestResult:
    finished = [m for m in dataset.matches if m.is_finished and m.actual_outcome is not None]
    finished.sort(key=lambda m: m.starting_at)
    if max_matches:
        finished = finished[-max_matches:]

    predictions: list[Prediction] = []
    actuals: list[MatchOutcome] = []

    for match in finished:
        pred = predict_match(dataset, match, model, settings, as_of=match.starting_at)
        predictions.append(pred)
        actuals.append(match.actual_outcome)  # type: ignore[arg-type]

    evaluation_mode: str | None = None
    training_leakage_risk = False
    warning: str | None = None
    if model.name == "feature_trained" and model.is_ready():
        evaluation_mode = "in_sample_artifact"
        training_leakage_risk = True
        warning = IN_SAMPLE_ARTIFACT_WARNING

    return BacktestResult(
        model_name=model.name,
        league_id=dataset.league_id,
        metrics=compute_metrics(predictions, actuals),
        predictions=predictions,
        actuals=actuals,
        evaluation_mode=evaluation_mode,
        training_leakage_risk=training_leakage_risk,
        warning=warning,
    )


def run_backtest_all_models(
    dataset: MatchDataset,
    settings: Settings,
    *,
    max_matches: int | None = None,
    include_ensemble: bool = True,
) -> list[BacktestResult]:
    models = build_base_models(settings, dataset)
    if include_ensemble:
        models.append(build_ensemble(settings, dataset))
    return [run_backtest(dataset, model, settings, max_matches=max_matches) for model in models]


def save_report(result: BacktestResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"backtest_{result.model_name}_{stamp}.json"
    csv_path = output_dir / f"backtest_{result.model_name}_{stamp}.csv"

    payload = {
        "model": result.model_name,
        "league_id": result.league_id,
        "metrics": result.metrics.as_dict(),
        "predictions": [
            {
                "fixture_id": p.fixture_id,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "pick": p.pick.value,
                "confidence": p.confidence,
                "probabilities": p.probabilities.as_dict(),
                "actual": a.value,
                "correct": p.pick == a,
            }
            for p, a in zip(result.predictions, result.actuals)
        ],
    }
    if result.evaluation_mode is not None:
        payload["evaluation_mode"] = result.evaluation_mode
        payload["training_leakage_risk"] = result.training_leakage_risk
    if result.warning is not None:
        payload["warning"] = result.warning
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "fixture_id,home_team,away_team,pick,confidence,p_home,p_draw,p_away,actual,correct"
    ]
    for p, a in zip(result.predictions, result.actuals):
        lines.append(
            f"{p.fixture_id},{p.home_team},{p.away_team},{p.pick.value},{p.confidence:.4f},"
            f"{p.probabilities.home:.4f},{p.probabilities.draw:.4f},{p.probabilities.away:.4f},"
            f"{a.value},{p.pick == a}"
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, csv_path
