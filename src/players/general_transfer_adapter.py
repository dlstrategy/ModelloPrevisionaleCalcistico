"""General transfer adapter basato su profili lega e skill vector."""

from __future__ import annotations

from dataclasses import dataclass

from src.players.league_profiles import LeagueProfile, load_league_profiles
from src.players.player_skill import PlayerSkillVector, clamp01

ADAPTATION_MATCHES_FULL = 15


@dataclass(frozen=True)
class TransferEstimate:
    player_id: int
    source_league_id: int | None
    target_league_id: int
    rating: float
    skill_vector: PlayerSkillVector
    confidence: float
    adapter_type: str
    specialist_key: str | None
    notes: tuple[str, ...]


def _adaptation_factor(target_matches_played: int) -> float:
    return min(max(target_matches_played, 0) / ADAPTATION_MATCHES_FULL, 1.0)


def _context_distance(source: LeagueProfile, target: LeagueProfile) -> float:
    deltas = (
        abs(target.strength_index - source.strength_index),
        abs(target.pace_index - source.pace_index),
        abs(target.physicality_index - source.physicality_index),
        abs(target.tactical_complexity_index - source.tactical_complexity_index),
        abs(target.defensive_intensity_index - source.defensive_intensity_index),
        abs(target.scoring_environment_index - source.scoring_environment_index),
    )
    weights = (0.25, 0.15, 0.15, 0.15, 0.15, 0.15)
    return sum(w * d for w, d in zip(weights, deltas))


def estimate_transfer_with_general_adapter(
    skill_vector: PlayerSkillVector,
    source_profile: LeagueProfile,
    target_profile: LeagueProfile,
    target_league_id: int,
    *,
    source_league_id: int | None = None,
    target_matches_played: int = 0,
) -> TransferEstimate:
    """Stima prudente cross-league usando differenza profili lega."""
    if source_league_id is not None and source_league_id == target_league_id:
        return TransferEstimate(
            player_id=skill_vector.player_id,
            source_league_id=source_league_id,
            target_league_id=target_league_id,
            rating=skill_vector.overall,
            skill_vector=skill_vector,
            confidence=skill_vector.sample_confidence,
            adapter_type="same_league",
            specialist_key=None,
            notes=("same_league",),
        )

    distance = _context_distance(source_profile, target_profile)
    rating_factor = 1.0 - min(distance * 0.20, 0.20)
    adjusted_rating = clamp01(skill_vector.overall * rating_factor, 0.0) or 0.0

    adaptation = _adaptation_factor(target_matches_played)
    base_confidence = (
        skill_vector.sample_confidence
        * source_profile.confidence
        * target_profile.confidence
    )
    confidence = base_confidence * (0.70 + 0.30 * adaptation)
    if source_profile.confidence < 0.5 or target_profile.confidence < 0.5:
        confidence *= 0.85

    known = load_league_profiles()
    source_unknown = (
        source_league_id is not None and source_league_id not in known
    )
    target_unknown = target_league_id not in known

    notes = (
        "general_adapter",
        f"context_distance={distance:.3f}",
        f"rating_factor={rating_factor:.3f}",
        f"target_matches_played={target_matches_played}",
    )
    if source_unknown or target_unknown:
        notes = notes + ("fallback_league_profile",)
        if source_unknown:
            notes = notes + ("unknown_source_league",)
        confidence = min(confidence, 0.25)

    return TransferEstimate(
        player_id=skill_vector.player_id,
        source_league_id=source_league_id,
        target_league_id=target_league_id,
        rating=clamp01(adjusted_rating, 0.0) or 0.0,
        skill_vector=skill_vector,
        confidence=clamp01(confidence, 0.0) or 0.0,
        adapter_type="general_adapter",
        specialist_key=None,
        notes=notes,
    )


# Re-export per retrocompatibilità — implementazione in unknown_player_policy.
from src.players.unknown_player_policy import unknown_player_estimate  # noqa: E402,F401
