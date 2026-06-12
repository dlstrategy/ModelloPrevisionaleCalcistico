"""Adattamento rating giocatore tra campionati (coefficienti mock proprietari)."""

from __future__ import annotations

from dataclasses import dataclass

from src.players.global_registry import PlayerLeagueSnapshot

# Coefficienti placeholder — da calibrare con dati reali in futuro.
# Non rappresentano verità statistica assoluta.
LEAGUE_TRANSFER_COEFFICIENTS: dict[tuple[int, int], float] = {
    (564, 384): 0.95,  # Liga -> Serie A (mock)
    (384, 564): 0.95,  # Serie A -> Liga (mock)
    (8, 384): 0.97,  # Premier -> Serie A (mock)
    (82, 384): 0.93,  # Bundesliga -> Serie A (mock)
}

DEFAULT_UNKNOWN_TRANSFER_COEFFICIENT = 0.85
DEFAULT_UNKNOWN_TRANSFER_CONFIDENCE_CAP = 0.50
ADAPTATION_MATCHES_FULL = 15


@dataclass(frozen=True)
class TransferAdjustment:
    player_id: int
    source_league_id: int
    target_league_id: int
    transferred_rating: float
    confidence: float
    source: str
    notes: tuple[str, ...]


def _adaptation_factor(target_matches_played: int) -> float:
    return min(max(target_matches_played, 0) / ADAPTATION_MATCHES_FULL, 1.0)


def _blend_confidence(
    base_transfer_confidence: float,
    snapshot_confidence: float,
    target_matches_played: int,
) -> float:
    factor = _adaptation_factor(target_matches_played)
    blended = base_transfer_confidence * (1.0 - factor) + snapshot_confidence * factor
    return max(0.0, min(blended, 1.0))


def adapt_player_rating(
    snapshot: PlayerLeagueSnapshot,
    target_league_id: int,
    target_matches_played: int = 0,
) -> TransferAdjustment:
    """Converte un rating da lega origine a lega destinazione con prudenza."""
    if snapshot.league_id == target_league_id:
        return TransferAdjustment(
            player_id=snapshot.player_id,
            source_league_id=snapshot.league_id,
            target_league_id=target_league_id,
            transferred_rating=snapshot.rating,
            confidence=snapshot.sample_confidence,
            source="same_league",
            notes=(),
        )

    key = (snapshot.league_id, target_league_id)
    notes: list[str] = ["cross_league_transfer", "mock_transfer_coefficient"]
    if key in LEAGUE_TRANSFER_COEFFICIENTS:
        coefficient = LEAGUE_TRANSFER_COEFFICIENTS[key]
        source = "league_coefficient_table"
    else:
        coefficient = DEFAULT_UNKNOWN_TRANSFER_COEFFICIENT
        source = "unknown_league_transfer"
        notes.append("default_transfer_coefficient")

    transferred = snapshot.rating * coefficient
    base_confidence = min(
        snapshot.sample_confidence * 0.75,
        DEFAULT_UNKNOWN_TRANSFER_CONFIDENCE_CAP if source == "unknown_league_transfer" else 0.70,
    )
    confidence = _blend_confidence(base_confidence, snapshot.sample_confidence, target_matches_played)

    if target_matches_played == 0:
        notes.append("no_target_league_minutes_yet")
    elif target_matches_played < ADAPTATION_MATCHES_FULL:
        notes.append(f"partial_adaptation_{target_matches_played}_matches")
    else:
        notes.append("full_adaptation_window_reached")

    return TransferAdjustment(
        player_id=snapshot.player_id,
        source_league_id=snapshot.league_id,
        target_league_id=target_league_id,
        transferred_rating=max(0.0, min(transferred, 10.0)),
        confidence=max(0.0, min(confidence, 1.0)),
        source=source,
        notes=tuple(notes),
    )
