"""Enumerazioni di dominio."""

from __future__ import annotations

from enum import Enum


class MatchOutcome(str, Enum):
    HOME = "1"
    DRAW = "X"
    AWAY = "2"


class ParticipantLocation(str, Enum):
    HOME = "home"
    AWAY = "away"
