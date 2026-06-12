"""Comando validate — data quality report."""

from __future__ import annotations

import sys

from src.config import QUALITY_DIR, Settings
from src.data_capabilities.resolver import parse_data_profile, resolve_capabilities
from src.data_pipeline.sync import load_dataset
from src.data_quality.checks import run_all_checks
from src.data_quality.report import build_report, save_quality_report


def print_validate(
    settings: Settings,
    league_id: int,
    *,
    profile: str | None = None,
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
        print(
            f"Esegui: python -m src.cli sync --league {league_id}",
            file=sys.stderr,
        )
        return 1

    cap = resolve_capabilities(settings, league_id, dataset, profile=profile_name)
    issues, summary = run_all_checks(
        dataset, settings, league_id, profile=profile_name
    )
    report = build_report(
        league_id,
        issues,
        dataset_summary=summary,
        data_profile=profile_name,
        data_completeness=cap.completeness.as_dict(),
    )
    json_path, csv_path = save_quality_report(report, QUALITY_DIR)

    status = "PASSED" if report.passed else "FAILED"
    print(f"Data quality — league {league_id}")
    print(f"Data profile: {profile_name}")
    print(f"Status: {status}")
    print(f"Data completeness score: {cap.completeness.score:.2f}")
    print()
    print("Dataset:")
    print(f"  matches: {summary['matches']}")
    print(f"  finished: {summary['finished']}")
    print(f"  future: {summary['future']}")
    print(f"  teams: {summary['teams']}")
    print()
    print("Checks:")
    for area in ("matches", "scores", "xg", "shots", "lineups", "tactical", "calendar", "features"):
        print(f"  {area:<10} {report.area_status.get(area, 'OK')}")
    print()
    print("Feature groups (profile):")
    print(f"  enabled:  {', '.join(cap.completeness.enabled_feature_groups) or 'none'}")
    print(f"  disabled: {', '.join(cap.completeness.disabled_feature_groups) or 'none'}")
    if cap.fallbacks:
        print(f"  fallbacks: {', '.join(cap.fallbacks)}")
    print(f"  policy disabled: {', '.join(cap.policy_disabled_capabilities)}")
    print()
    print("Issues:")
    print(f"  warnings: {report.warnings}")
    print(f"  errors: {report.errors}")
    if report.issues:
        print()
        for issue in report.issues[:20]:
            fid = f" fixture={issue.fixture_id}" if issue.fixture_id else ""
            print(f"  [{issue.severity.upper()}] {issue.area}/{issue.code}{fid}: {issue.message}")
        if len(report.issues) > 20:
            print(f"  ... +{len(report.issues) - 20} altri")
    print()
    print(f"Report JSON: {json_path}")
    print(f"Report CSV:  {csv_path}")

    return 1 if not report.passed else 0
