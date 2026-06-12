"""Valore giocatore league-aware — composable transfer resolver."""

from __future__ import annotations

from src.players.composable_transfer import resolve_composable_transfer_estimate


def resolve_player_value_for_league(
    player_id: int,
    target_league_id: int,
    target_matches_played: int = 0,
    role: str | None = None,
) -> dict:
    """Risolve rating giocatore nella lega target via composable transfer stack."""
    estimate = resolve_composable_transfer_estimate(
        player_id,
        target_league_id,
        target_matches_played=target_matches_played,
        role=role,
    )
    return {
        "player_id": estimate.player_id,
        "rating": estimate.rating,
        "confidence": estimate.confidence,
        "source": estimate.adapter_type,
        "source_league_id": estimate.source_league_id,
        "target_league_id": estimate.target_league_id,
        "specialist_key": estimate.specialist_key,
        "notes": list(estimate.notes),
    }
