"""Ablation test — valutazione incrementale gruppi feature."""

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
from src.features.feature_groups import ABLATION_VARIANTS, keys_for_groups
from src.features.match_context import build_match_context
from src.models.feature_model import FeatureModel


@dataclass
class AblationResult:
    variant: str
    enabled_groups: frozenset[str]
    feature_count: int
    metrics: BacktestMetrics
    predictions: list[Prediction]
    actuals: list[MatchOutcome]


def run_ablation_variant(
    dataset: MatchDataset,
    settings: Settings,
    variant: str,
    *,
    max_matches: int | None = None,
) -> AblationResult:
    if variant not in ABLATION_VARIANTS:
        raise ValueError(f"Variante ablation sconosciuta: {variant}")

    groups = ABLATION_VARIANTS[variant]
    model = FeatureModel(enabled_groups=groups)

    finished = [m for m in dataset.matches if m.is_finished and m.actual_outcome is not None]
    finished.sort(key=lambda m: m.starting_at)
    if max_matches:
        finished = finished[-max_matches:]

    predictions: list[Prediction] = []
    actuals: list[MatchOutcome] = []

    for match in finished:
        context = build_match_context(
            dataset, match, settings, as_of=match.starting_at, enabled_feature_groups=groups
        )
        probs = model.predict(context)
        pred = Prediction(
            fixture_id=match.id,
            home_team=match.home.team_name,
            away_team=match.away.team_name,
            probabilities=probs,
            model_name=f"feature[{variant}]",
            starting_at=match.starting_at,
        )
        predictions.append(pred)
        actuals.append(match.actual_outcome)  # type: ignore[arg-type]

    metrics = compute_metrics(predictions, actuals)
    return AblationResult(
        variant=variant,
        enabled_groups=groups,
        feature_count=len(keys_for_groups(groups)),
        metrics=metrics,
        predictions=predictions,
        actuals=actuals,
    )


def run_ablation_study(
    dataset: MatchDataset,
    settings: Settings,
    *,
    max_matches: int | None = None,
    variants: list[str] | None = None,
) -> list[AblationResult]:
    names = variants or list(ABLATION_VARIANTS.keys())
    return [
        run_ablation_variant(dataset, settings, variant, max_matches=max_matches)
        for variant in names
    ]


def save_ablation_report(results: list[AblationResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"ablation_{stamp}.json"

    payload = {
        "generated_at": stamp,
        "variants": [
            {
                "variant": r.variant,
                "enabled_groups": sorted(r.enabled_groups),
                "feature_count": r.feature_count,
                "metrics": r.metrics.as_dict(),
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
