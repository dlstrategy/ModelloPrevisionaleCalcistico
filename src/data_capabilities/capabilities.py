"""Capability dati — enum e costanti."""

from __future__ import annotations

from enum import StrEnum


class DataCapability(StrEnum):
    CORE_FIXTURES = "CORE_FIXTURES"
    LIVE_SCORES = "LIVE_SCORES"
    STANDINGS = "STANDINGS"
    TEAM_STATS = "TEAM_STATS"
    PLAYER_STATS = "PLAYER_STATS"
    LINEUPS_CONFIRMED = "LINEUPS_CONFIRMED"
    INJURIES_SUSPENSIONS = "INJURIES_SUSPENSIONS"
    HISTORICAL_DATA = "HISTORICAL_DATA"
    XG = "XG"
    SHOTS = "SHOTS"
    PRESSURE_INDEX = "PRESSURE_INDEX"
    EXPECTED_LINEUPS = "EXPECTED_LINEUPS"
    TACTICAL_DATA = "TACTICAL_DATA"
    CALENDAR = "CALENDAR"
    ODDS = "ODDS"
    PREDICTIONS = "PREDICTIONS"
    NEWS = "NEWS"


ALL_CAPABILITIES: frozenset[DataCapability] = frozenset(DataCapability)

POLICY_DISABLED_CAPABILITIES: frozenset[DataCapability] = frozenset(
    {DataCapability.PREDICTIONS, DataCapability.ODDS}
)

VALID_PROFILES: frozenset[str] = frozenset({"base", "advanced", "all_in_no_predictions"})
