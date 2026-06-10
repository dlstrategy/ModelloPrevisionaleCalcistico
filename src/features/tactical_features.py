"""Confronto moduli tattici — usa LineupImpact.duel_edges quando disponibile."""

from __future__ import annotations

from src.features.lineup_features import LineupImpact


def tactical_edge_score(lineup: LineupImpact | None) -> float:
    if lineup is None or not lineup.duel_edges:
        return 0.0
    return sum(lineup.duel_edges.values()) / len(lineup.duel_edges)
