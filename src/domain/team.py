"""Entità squadra."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Team:
    id: int
    name: str
    short_code: str | None = None
