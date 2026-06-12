"""Rilevamento capability e risoluzione gruppi feature per profilo."""

from __future__ import annotations

import json

from src.config import FIXTURES_DIR, Settings
from src.data_capabilities.capabilities import (
    POLICY_DISABLED_CAPABILITIES,
    VALID_PROFILES,
    DataCapability,
)
from src.data_capabilities.profiles import profile_capabilities
from src.data_capabilities.report import CapabilityResolution, DataCompletenessReport
from src.data_capabilities.requirements import ALL_FEATURE_GROUPS, FEATURE_REQUIREMENTS
from src.data_pipeline.dataset_builder import MatchDataset
from src.features.lineup_features import FORECAST


def parse_data_profile(value: str) -> str:
    profile = value.strip().lower()
    if profile not in VALID_PROFILES:
        valid = ", ".join(sorted(VALID_PROFILES))
        raise ValueError(
            f"DATA_PROFILE non valido: {value!r}. Valori ammessi: {valid}"
        )
    return profile


def _has_forecast_lineups(league_id: int) -> bool:
    path = FIXTURES_DIR / f"league_{league_id}_lineups.json"
    if not path.exists():
        return False
    payload = json.loads(path.read_text(encoding="utf-8"))
    for row in payload.get("fixtures", {}).values():
        if isinstance(row, dict) and row.get("data_availability") == FORECAST:
            return True
    return False


def detect_available_capabilities(
    league_id: int,
    dataset: MatchDataset | None,
) -> frozenset[DataCapability]:
    available: set[DataCapability] = set()
    if dataset and dataset.matches:
        available.add(DataCapability.CORE_FIXTURES)
        available.add(DataCapability.STANDINGS)
        available.add(DataCapability.TEAM_STATS)
        if any(m.is_finished for m in dataset.matches):
            available.add(DataCapability.LIVE_SCORES)
            available.add(DataCapability.HISTORICAL_DATA)

    companions = {
        name: (FIXTURES_DIR / f"league_{league_id}_{name}.json").exists()
        for name in ("xg", "shots", "lineups", "tactical", "calendar")
    }
    if companions.get("lineups"):
        available.add(DataCapability.LINEUPS_CONFIRMED)
        available.add(DataCapability.PLAYER_STATS)
        available.add(DataCapability.INJURIES_SUSPENSIONS)
        if _has_forecast_lineups(league_id):
            available.add(DataCapability.EXPECTED_LINEUPS)
    if companions.get("xg"):
        available.add(DataCapability.XG)
    if companions.get("shots"):
        available.add(DataCapability.SHOTS)
    if companions.get("tactical"):
        available.add(DataCapability.TACTICAL_DATA)
    if companions.get("calendar"):
        available.add(DataCapability.CALENDAR)

    return frozenset(available)


def _group_status(
    group: str,
    profile_caps: frozenset[DataCapability],
    detected: frozenset[DataCapability],
) -> tuple[str, str | None]:
    req = FEATURE_REQUIREMENTS[group]
    fallback = req["fallback"]
    required_in_profile = [c for c in req["required"] if c in profile_caps]
    optional_in_profile = [c for c in req["optional"] if c in profile_caps]

    if required_in_profile:
        if all(c in detected for c in required_in_profile):
            return "enabled", None
        return "disabled", fallback

    if optional_in_profile:
        if any(c in detected for c in optional_in_profile):
            return "enabled", None
        return "fallback", fallback

    if req["required"]:
        return "disabled", fallback
    return "fallback", fallback


def _compute_score(
    profile_caps: frozenset[DataCapability],
    detected: frozenset[DataCapability],
    fallbacks: tuple[str, ...],
) -> float:
    expected = profile_caps - POLICY_DISABLED_CAPABILITIES
    if not expected:
        return 1.0
    present = sum(1 for cap in expected if cap in detected)
    base_score = present / len(expected)
    penalty = min(0.15, 0.02 * len(fallbacks))
    return max(0.0, min(1.0, round(base_score - penalty, 4)))


def resolve_capabilities(
    settings: Settings,
    league_id: int,
    dataset: MatchDataset | None = None,
    *,
    profile: str | None = None,
) -> CapabilityResolution:
    profile_name = parse_data_profile(profile or settings.data_profile)
    profile_caps = profile_capabilities(profile_name)
    detected = detect_available_capabilities(league_id, dataset)

    expected = profile_caps - POLICY_DISABLED_CAPABILITIES
    missing = tuple(sorted(cap.value for cap in expected if cap not in detected))
    policy_disabled = tuple(sorted(c.value for c in POLICY_DISABLED_CAPABILITIES))

    enabled: set[str] = set()
    disabled: set[str] = set()
    fallbacks: list[str] = []

    for group in sorted(ALL_FEATURE_GROUPS):
        status, fb = _group_status(group, profile_caps, detected)
        if status == "enabled":
            enabled.add(group)
        elif status == "fallback":
            enabled.add(group)
            if fb:
                fallbacks.append(f"{group}_{fb}")
        else:
            disabled.add(group)
            if fb:
                fallbacks.append(f"{group}_{fb}")

    fallbacks_tuple = tuple(fallbacks)
    score = _compute_score(profile_caps, detected, fallbacks_tuple)

    completeness = DataCompletenessReport(
        profile=profile_name,
        score=score,
        available_capabilities=tuple(sorted(c.value for c in detected if c in profile_caps)),
        missing_capabilities=missing,
        policy_disabled_capabilities=policy_disabled,
        enabled_feature_groups=tuple(sorted(enabled)),
        disabled_feature_groups=tuple(sorted(disabled)),
        fallbacks_used=fallbacks_tuple,
    )

    return CapabilityResolution(
        profile=profile_name,
        enabled_feature_groups=frozenset(enabled),
        disabled_feature_groups=frozenset(disabled),
        fallbacks=fallbacks_tuple,
        missing_capabilities=missing,
        policy_disabled_capabilities=policy_disabled,
        available_capabilities=tuple(sorted(c.value for c in detected)),
        completeness=completeness,
    )


def capability_status_label(
    cap: DataCapability,
    profile_caps: frozenset[DataCapability],
    detected: frozenset[DataCapability],
) -> str:
    if cap in POLICY_DISABLED_CAPABILITIES:
        return "disabled"
    if cap not in profile_caps:
        return "not_in_profile"
    if cap in detected:
        return "OK"
    return "missing"


def feature_group_display_status(
    group: str,
    resolution: CapabilityResolution,
) -> str:
    if group in resolution.enabled_feature_groups:
        prefix = f"{group}_"
        if any(fb.startswith(prefix) for fb in resolution.fallbacks):
            return "fallback_allowed"
        return "enabled"
    req = FEATURE_REQUIREMENTS.get(group, {})
    fb = req.get("fallback", "")
    if "disabled" in fb:
        return "disabled_or_fallback"
    return "disabled"
