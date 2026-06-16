"""Profili dati supportati — capability attese per livello."""

from __future__ import annotations

from src.data_capabilities.capabilities import DataCapability

PROFILE_BASE: frozenset[DataCapability] = frozenset(
    {
        DataCapability.CORE_FIXTURES,
        DataCapability.LIVE_SCORES,
        DataCapability.STANDINGS,
        DataCapability.TEAM_STATS,
        DataCapability.PLAYER_STATS,
        DataCapability.LINEUPS_CONFIRMED,
        DataCapability.INJURIES_SUSPENSIONS,
        DataCapability.CALENDAR,
    }
)

PROFILE_ADVANCED: frozenset[DataCapability] = frozenset(
    PROFILE_BASE
    | {
        DataCapability.HISTORICAL_DATA,
        DataCapability.XG,
        DataCapability.SHOTS,
        DataCapability.TACTICAL_DATA,
        DataCapability.COACH_PROFILES,
    }
)

PROFILE_ALL_IN_NO_PREDICTIONS: frozenset[DataCapability] = frozenset(
    PROFILE_ADVANCED
    | {
        DataCapability.PRESSURE_INDEX,
        DataCapability.EXPECTED_LINEUPS,
        DataCapability.NEWS,
    }
)

DATA_PROFILES: dict[str, frozenset[DataCapability]] = {
    "base": PROFILE_BASE,
    "advanced": PROFILE_ADVANCED,
    "all_in_no_predictions": PROFILE_ALL_IN_NO_PREDICTIONS,
}


def profile_capabilities(profile: str) -> frozenset[DataCapability]:
    return DATA_PROFILES[profile]
