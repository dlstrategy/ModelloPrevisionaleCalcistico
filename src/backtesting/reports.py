"""Report confronto modelli."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.backtesting.backtest import BacktestResult, save_report


def save_comparison_report(
    results: list[BacktestResult],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"backtest_comparison_{stamp}.json"

    ranked = sorted(results, key=lambda r: r.metrics.brier_score)
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "best_model": ranked[0].model_name if ranked else None,
        "models": [
            {
                "name": r.model_name,
                "metrics": r.metrics.as_dict(),
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for result in results:
        save_report(result, output_dir)

    return path
