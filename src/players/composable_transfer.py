"""Resolver componibile: general adapter + pair specialist opzionale."""

from __future__ import annotations

from src.players.general_transfer_adapter import (
    TransferEstimate,
    estimate_transfer_with_general_adapter,
    unknown_player_estimate,
)
from src.players.global_registry import (
    get_latest_snapshot,
    get_player_snapshot_for_league,
    load_player_careers,
)
from src.players.league_profiles import get_league_profile, load_league_profiles
from src.players.pair_specialists import apply_pair_specialist, find_best_specialist
from src.players.player_skill import normalize_role, skill_from_snapshot


def resolve_composable_transfer_estimate(
    player_id: int,
    target_league_id: int,
    target_matches_played: int = 0,
    role: str | None = None,
) -> TransferEstimate:
    careers = load_player_careers()
    profiles = load_league_profiles()
    career = careers.get(player_id)
    if career is None or not career.snapshots:
        return unknown_player_estimate(player_id, target_league_id)

    same_league = get_player_snapshot_for_league(
        player_id, target_league_id, careers=careers
    )
    if same_league is not None:
        skill = skill_from_snapshot(same_league)
        profile = get_league_profile(target_league_id, profiles=profiles)
        return estimate_transfer_with_general_adapter(
            skill,
            profile,
            profile,
            target_league_id,
            source_league_id=target_league_id,
            target_matches_played=target_matches_played,
        )

    origin = get_latest_snapshot(
        player_id, before_league_id=target_league_id, careers=careers
    )
    if origin is None:
        return unknown_player_estimate(player_id, target_league_id)

    skill = skill_from_snapshot(origin)
    resolved_role = role or normalize_role(origin.position) or skill.role
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
        return apply_pair_specialist(base, specialist)
    return base
