"""Feature giocatori — predisposto; dati da lineup mock o Fase 3 API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerAvailability:
    team_id: int
    missing_starters: int
    avg_starter_rating: float | None = None
