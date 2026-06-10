"""Validatori dataset."""

from __future__ import annotations

from src.domain.match import Match


def validate_match(match: Match) -> list[str]:
    errors: list[str] = []
    if len(match.participants) < 2:
        errors.append(f"Match {match.id}: meno di 2 partecipanti")
    try:
        _ = match.home
        _ = match.away
    except ValueError as exc:
        errors.append(str(exc))
    return errors
