"""Policy esplicita per giocatori sconosciuti o con dati insufficienti."""

from __future__ import annotations

from dataclasses import dataclass, replace

from src.players.general_transfer_adapter import TransferEstimate
from src.players.global_registry import PlayerLeagueSnapshot
from src.players.player_skill import PlayerSkillVector, clamp01, normalize_role

CANONICAL_ROLES = frozenset({"forward", "midfielder", "defender", "goalkeeper"})


@dataclass(frozen=True)
class UnknownPlayerPolicy:
    """Soglie conservative — placeholder offline, da calibrare con dati reali."""

    neutral_rating: float = 0.50
    default_confidence: float = 0.10
    low_minutes_threshold: int = 300
    low_minutes_confidence_cap: float = 0.30
    low_sample_confidence_threshold: float = 0.30
    low_sample_confidence_cap: float = 0.30
    unknown_league_confidence_cap: float = 0.25
    unknown_role_confidence_penalty: float = 0.05


DEFAULT_POLICY = UnknownPlayerPolicy()


def unknown_player_estimate(
    player_id: int,
    target_league_id: int,
    *,
    policy: UnknownPlayerPolicy = DEFAULT_POLICY,
) -> TransferEstimate:
    """Giocatore assente dal registry o senza snapshot utilizzabili."""
    neutral = PlayerSkillVector(
        player_id=player_id,
        role=None,
        overall=policy.neutral_rating,
        sample_confidence=policy.default_confidence,
    ).sanitized()
    return TransferEstimate(
        player_id=player_id,
        source_league_id=None,
        target_league_id=target_league_id,
        rating=policy.neutral_rating,
        skill_vector=neutral,
        confidence=policy.default_confidence,
        adapter_type="unknown_player",
        specialist_key=None,
        notes=(
            "unknown_player",
            "player_not_in_career_registry",
            "neutral_rating_low_confidence",
        ),
    )


def apply_transfer_hardening(
    estimate: TransferEstimate,
    snapshot: PlayerLeagueSnapshot | None,
    *,
    resolved_role: str | None = None,
    raw_role_input: str | None = None,
    known_league_ids: frozenset[int] | None = None,
    policy: UnknownPlayerPolicy = DEFAULT_POLICY,
    cross_league_transfer: bool = False,
) -> TransferEstimate:
    """Applica cap confidence e note per casi incerti (non modifica rating in modo aggressivo)."""
    if estimate.adapter_type == "unknown_player":
        return estimate

    notes: list[str] = list(estimate.notes)
    confidence = estimate.confidence

    if cross_league_transfer:
        notes.append("known_player_unknown_target_league")

    if known_league_ids is not None and snapshot is not None:
        if snapshot.league_id not in known_league_ids:
            notes.append("unknown_source_league")
            confidence = min(confidence, policy.unknown_league_confidence_cap)
        if estimate.target_league_id not in known_league_ids:
            if "fallback_league_profile" not in notes:
                notes.append("fallback_league_profile")
            confidence = min(confidence, policy.unknown_league_confidence_cap)

    if snapshot is not None:
        if snapshot.minutes < policy.low_minutes_threshold:
            notes.append("low_sample_minutes")
            confidence = min(confidence, policy.low_minutes_confidence_cap)
        if snapshot.sample_confidence < policy.low_sample_confidence_threshold:
            notes.append("low_sample_confidence")
            confidence = min(confidence, policy.low_sample_confidence_cap)
            notes.append("low_sample_player")

    if estimate.skill_vector.sample_confidence < policy.low_sample_confidence_threshold:
        if "low_sample_confidence" not in notes:
            notes.append("low_sample_confidence")
        confidence = min(confidence, policy.low_sample_confidence_cap)

    if raw_role_input is not None and normalize_role(raw_role_input) is None:
        notes.append("unknown_role")
        confidence = max(
            0.0,
            confidence - policy.unknown_role_confidence_penalty,
        )
    elif resolved_role is not None and resolved_role not in CANONICAL_ROLES:
        notes.append("unknown_role")
        confidence = max(
            0.0,
            confidence - policy.unknown_role_confidence_penalty,
        )

    return replace(
        estimate,
        confidence=clamp01(confidence, 0.0) or 0.0,
        notes=tuple(dict.fromkeys(notes)),
    )
