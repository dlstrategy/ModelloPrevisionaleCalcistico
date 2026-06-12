"""Resolver componibile: general adapter + pair specialist opzionale."""

from __future__ import annotations

from src.players.general_transfer_adapter import (
    TransferEstimate,
    estimate_transfer_with_general_adapter,
)
from src.players.global_registry import (
    get_best_available_snapshot,
    get_player_snapshot_for_league,
    load_player_careers,
)
from src.players.league_profiles import get_league_profile, load_league_profiles
from src.players.pair_specialists import apply_pair_specialist, find_best_specialist
from src.players.player_skill import normalize_role, skill_from_snapshot
from src.players.unknown_player_policy import (
    apply_transfer_hardening,
    unknown_player_estimate,
)


def _known_league_ids(profiles: dict) -> frozenset[int]:
    return frozenset(profiles.keys())


def _finalize(
    estimate: TransferEstimate,
    snapshot,
    *,
    resolved_role: str | None,
    raw_role: str | None,
    known_leagues: frozenset[int],
    cross_league: bool = False,
) -> TransferEstimate:
    return apply_transfer_hardening(
        estimate,
        snapshot,
        resolved_role=resolved_role,
        raw_role_input=raw_role,
        known_league_ids=known_leagues,
        cross_league_transfer=cross_league,
    )


def resolve_composable_transfer_estimate(
    player_id: int,
    target_league_id: int,
    target_matches_played: int = 0,
    role: str | None = None,
) -> TransferEstimate:
    careers = load_player_careers()
    profiles = load_league_profiles()
    known_leagues = _known_league_ids(profiles)
    normalized_input_role = normalize_role(role) if role is not None else None

    career = careers.get(player_id)
    if career is None or not career.snapshots:
        return unknown_player_estimate(player_id, target_league_id)

    same_league = get_player_snapshot_for_league(
        player_id, target_league_id, careers=careers
    )
    if same_league is not None:
        skill = skill_from_snapshot(same_league)
        profile = get_league_profile(target_league_id, profiles=profiles)
        resolved_role = (
            normalized_input_role
            or normalize_role(same_league.position)
            or skill.role
        )
        estimate = estimate_transfer_with_general_adapter(
            skill,
            profile,
            profile,
            target_league_id,
            source_league_id=target_league_id,
            target_matches_played=target_matches_played,
        )
        return _finalize(
            estimate,
            same_league,
            resolved_role=resolved_role,
            raw_role=role,
            known_leagues=known_leagues,
        )

    origin = get_best_available_snapshot(
        player_id, before_league_id=target_league_id, careers=careers
    )
    if origin is None:
        return unknown_player_estimate(player_id, target_league_id)

    skill = skill_from_snapshot(origin)
    resolved_role = (
        normalized_input_role
        or normalize_role(origin.position)
        or skill.role
    )
    source_profile = get_league_profile(origin.league_id, profiles=profiles)
    target_profile = get_league_profile(target_league_id, profiles=profiles)

    base = estimate_transfer_with_general_adapter(
        skill,
        source_profile,
        target_profile,
        target_league_id,
        source_league_id=origin.league_id,
        target_matches_played=target_matches_played,
    )

    specialist = find_best_specialist(
        origin.league_id,
        target_league_id,
        resolved_role,
    )
    if specialist is not None:
        estimate = apply_pair_specialist(base, specialist)
    else:
        estimate = base

    return _finalize(
        estimate,
        origin,
        resolved_role=resolved_role,
        raw_role=role,
        known_leagues=known_leagues,
        cross_league=True,
    )
