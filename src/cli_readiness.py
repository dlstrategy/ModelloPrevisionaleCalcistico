"""Comando readiness — audit prontezza dati reali (statico, no API)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from src.config import BACKTESTS_DIR, Settings
from src.data_pipeline.readiness import (
    build_real_data_readiness_report,
    readiness_report_as_dict,
)


def _format_section(title: str, items: tuple) -> None:
    print(title)
    if not items:
        print("  (nessuno)")
    else:
        for item in items:
            print(f"  * {item.message}")
    print()


def print_readiness(
    settings: Settings,
    league_id: int,
    *,
    profile: str | None = None,
    as_json: bool = False,
    save: bool = False,
) -> int:
    report = build_real_data_readiness_report(settings, league_id, profile=profile)
    payload = readiness_report_as_dict(report)

    if save:
        BACKTESTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = BACKTESTS_DIR / f"readiness_{stamp}.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if not as_json:
            print(f"Report salvato: {out_path}")

    if as_json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Real data readiness — league {league_id}, profile {report.profile}")
    print(f"Overall: {report.overall_status}")
    print()
    _format_section("Blocking:", report.blocking_items)
    _format_section("Warnings:", report.warning_items)

    return 0


def readiness_output_safe(text: str, settings: Settings) -> bool:
    """True se l'output non contiene il token API."""
    token = settings.api_token
    if not token:
        return True
    return token not in text
