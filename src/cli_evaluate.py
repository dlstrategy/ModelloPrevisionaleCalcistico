"""Comando evaluate-models — promotion gate report."""

from __future__ import annotations

import json
import sys

from src.backtesting.model_evaluation import format_evaluation_console, run_model_evaluation
from src.backtesting.promotion_gate import PromotionThresholds, decision_as_dict
from src.config import Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.sync import load_dataset


def print_evaluate_models(
    settings: Settings,
    league_id: int,
    *,
    profile: str | None = None,
    baseline_policy: str = "full",
    candidate_policy: str = "compact",
    min_train_matches: int = 10,
    test_window_size: int = 5,
    step_size: int = 5,
    include_ensemble_baseline: bool = False,
    as_json: bool = False,
) -> int:
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

    payload = run_model_evaluation(
        dataset,
        settings,
        profile=profile_name,
        baseline_policy=baseline_policy,
        candidate_policy=candidate_policy,
        min_train_matches=min_train_matches,
        test_window_size=test_window_size,
        step_size=step_size,
        include_ensemble_baseline=include_ensemble_baseline,
    )

    export = dict(payload)
    export.pop("_decision", None)

    if as_json:
        print(json.dumps(export, indent=2))
    else:
        print(format_evaluation_console(payload))
    return 0
