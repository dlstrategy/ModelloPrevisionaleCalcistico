"""Comando capabilities — profilo dati e completeness."""

from __future__ import annotations

import sys

from src.config import Settings
from src.data_capabilities.capabilities import DataCapability, POLICY_DISABLED_CAPABILITIES
from src.data_capabilities.profiles import profile_capabilities
from src.data_capabilities.resolver import (
    capability_status_label,
    detect_available_capabilities,
    feature_group_display_status,
    parse_data_profile,
    resolve_capabilities,
)
from src.data_pipeline.sync import load_dataset


def print_capabilities(
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
    except FileNotFoundError:
        dataset = None

    resolution = resolve_capabilities(settings, league_id, dataset, profile=profile_name)
    profile_caps = profile_capabilities(profile_name)
    detected = detect_available_capabilities(league_id, dataset)

    print(f"Data capabilities — profile: {profile_name}")
    print()
    print("Available:")
    for cap in sorted(profile_caps, key=lambda c: c.value):
        if cap in POLICY_DISABLED_CAPABILITIES:
            continue
        label = capability_status_label(cap, profile_caps, detected)
        print(f"  {cap.value:<26} {label}")

    print()
    print("Unavailable / not expected:")
    for cap in sorted(DataCapability, key=lambda c: c.value):
        if cap in profile_caps or cap in POLICY_DISABLED_CAPABILITIES:
            continue
        print(f"  {cap.value:<26} not_in_profile")

    print()
    print("Disabled by project policy:")
    for cap in sorted(POLICY_DISABLED_CAPABILITIES, key=lambda c: c.value):
        print(f"  {cap.value:<26} disabled")

    print()
    print("Feature groups:")
    from src.data_capabilities.requirements import ALL_FEATURE_GROUPS

    for group in sorted(ALL_FEATURE_GROUPS):
        status = feature_group_display_status(group, resolution)
        print(f"  {group:<26} {status}")

    print()
    print(f"Data completeness score: {resolution.completeness.score:.2f}")
    if resolution.missing_capabilities:
        print(f"Missing (expected): {', '.join(resolution.missing_capabilities)}")
    if resolution.fallbacks:
        print(f"Fallbacks: {', '.join(resolution.fallbacks)}")

    return 0
