"""Test unknown player policy."""

from src.players.unknown_player_policy import (
    DEFAULT_POLICY,
    apply_transfer_hardening,
    unknown_player_estimate,
)
from src.players.general_transfer_adapter import TransferEstimate
from src.players.global_registry import get_player_snapshot_for_league
from src.players.player_skill import PlayerSkillVector, skill_from_snapshot


def test_unknown_player_policy_values():
    est = unknown_player_estimate(99999, 384)
    assert est.rating == DEFAULT_POLICY.neutral_rating
    assert est.confidence == DEFAULT_POLICY.default_confidence
    assert est.adapter_type == "unknown_player"


def test_low_sample_hardening():
    snap = get_player_snapshot_for_league(1005, 384)
    assert snap is not None
    skill = skill_from_snapshot(snap)
    base = TransferEstimate(
        player_id=1005,
        source_league_id=384,
        target_league_id=384,
        rating=skill.overall,
        skill_vector=skill,
        confidence=0.8,
        adapter_type="same_league",
        specialist_key=None,
        notes=("same_league",),
    )
    hardened = apply_transfer_hardening(base, snap)
    assert "low_sample_minutes" in hardened.notes
    assert hardened.confidence <= DEFAULT_POLICY.low_minutes_confidence_cap
