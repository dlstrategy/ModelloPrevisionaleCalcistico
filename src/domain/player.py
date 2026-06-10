"""Entità giocatore — predisposta per feature avanzate (lineup, xG, duelli)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    id: int
    name: str
    team_id: int | None = None
    position: str | None = None
