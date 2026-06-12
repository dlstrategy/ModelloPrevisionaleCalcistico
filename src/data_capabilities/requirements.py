"""Requisiti capability per gruppo feature."""

from __future__ import annotations

from typing import TypedDict

from src.data_capabilities.capabilities import DataCapability


class FeatureRequirement(TypedDict):
    required: list[DataCapability]
    optional: list[DataCapability]
    fallback: str


FEATURE_REQUIREMENTS: dict[str, FeatureRequirement] = {
    "base": {
        "required": [DataCapability.CORE_FIXTURES, DataCapability.STANDINGS],
        "optional": [DataCapability.TEAM_STATS],
        "fallback": "historical_basic",
    },
    "advanced_strength": {
        "required": [DataCapability.CORE_FIXTURES],
        "optional": [DataCapability.TEAM_STATS, DataCapability.HISTORICAL_DATA],
        "fallback": "basic_strength",
    },
    "xg": {
        "required": [DataCapability.XG],
        "optional": [],
        "fallback": "disabled_or_proxy",
    },
    "shots": {
        "required": [DataCapability.SHOTS],
        "optional": [],
        "fallback": "disabled_or_basic_shots",
    },
    "strength_of_schedule": {
        "required": [DataCapability.CORE_FIXTURES],
        "optional": [DataCapability.HISTORICAL_DATA],
        "fallback": "disabled",
    },
    "player_lineup": {
        "required": [],
        "optional": [DataCapability.LINEUPS_CONFIRMED, DataCapability.EXPECTED_LINEUPS],
        "fallback": "default_neutral_lineup",
    },
    "tactical": {
        "required": [],
        "optional": [
            DataCapability.TACTICAL_DATA,
            DataCapability.LINEUPS_CONFIRMED,
            DataCapability.EXPECTED_LINEUPS,
        ],
        "fallback": "default_tactical",
    },
    "calendar": {
        "required": [DataCapability.CALENDAR],
        "optional": [],
        "fallback": "basic_rest_days",
    },
    "motivation": {
        "required": [DataCapability.STANDINGS],
        "optional": [],
        "fallback": "neutral_motivation",
    },
}

ALL_FEATURE_GROUPS: frozenset[str] = frozenset(FEATURE_REQUIREMENTS.keys())
