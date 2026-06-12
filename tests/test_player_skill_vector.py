"""Test player skill vector."""

import math

from src.players.global_registry import get_player_snapshot_for_league
from src.players.player_skill import PlayerSkillVector, blend_skill_vectors, clamp01, skill_from_snapshot


def test_clamp_out_of_range():
    assert clamp01(1.5) == 1.0
    assert clamp01(-0.2) == 0.0
    assert clamp01(float("nan")) == 0.0


def test_skill_from_snapshot_normalized():
    snap = get_player_snapshot_for_league(1001, 384)
    assert snap is not None
    skill = skill_from_snapshot(snap)
    assert 0.0 <= skill.overall <= 1.0
    assert 0.0 <= skill.sample_confidence <= 1.0
    assert skill.role == "forward"


def test_none_handling_in_blend():
    a = PlayerSkillVector(player_id=1, role="forward", overall=0.6, finishing=0.7, sample_confidence=0.8)
    b = PlayerSkillVector(player_id=1, role="forward", overall=0.8, finishing=None, sample_confidence=0.9)
    blended = blend_skill_vectors(a, b, 0.5)
    assert blended.finishing is not None
    assert 0.0 <= blended.overall <= 1.0


def test_blend_weight():
    a = PlayerSkillVector(player_id=1, role=None, overall=0.4, sample_confidence=0.5)
    b = PlayerSkillVector(player_id=1, role=None, overall=0.8, sample_confidence=0.9)
    blended = blend_skill_vectors(a, b, 1.0)
    assert blended.overall == 0.8
    assert blended.sample_confidence == 0.9


def test_sanitize_clamps():
    raw = PlayerSkillVector(player_id=1, role=None, overall=2.0, sample_confidence=3.0)
    clean = raw.sanitized()
    assert clean.overall == 1.0
    assert clean.sample_confidence == 1.0
    assert math.isfinite(clean.overall)
