"""Test pair transfer specialists."""

from src.players.general_transfer_adapter import TransferEstimate
from src.players.pair_specialists import (
    MIN_SPECIALIST_RELIABILITY,
    MIN_SPECIALIST_SAMPLE_SIZE,
    PairSpecialist,
    apply_pair_specialist,
    find_best_specialist,
    load_pair_specialists,
    specialist_key,
)
from src.players.player_skill import PlayerSkillVector


def test_specialist_key_directional():
    assert specialist_key(564, 384) == "564->384:any"
    assert specialist_key(384, 564) == "384->564:any"
    assert specialist_key(564, 384, "forward") == "564->384:forward"


def test_specialist_key_normalizes_fw_alias():
    assert specialist_key(564, 384, "FW") == "564->384:forward"


def test_find_best_specialist_accepts_fw_alias():
    spec = find_best_specialist(564, 384, role="FW")
    assert spec is not None
    assert spec.role == "forward"


def test_liga_serie_a_differs_from_reverse():
    specialists = load_pair_specialists()
    forward = specialists.get("564->384:forward")
    reverse = specialists.get("384->564:forward")
    assert forward is not None
    assert reverse is None


def test_role_specific_beats_general():
    spec = find_best_specialist(564, 384, role="forward")
    assert spec is not None
    assert spec.role == "forward"


def test_low_sample_specialist_ignored():
    bad = PairSpecialist(
        source_league_id=564,
        target_league_id=384,
        role="forward",
        sample_size=5,
        reliability=0.90,
        rating_multiplier=0.90,
        confidence_multiplier=1.0,
        learned_version="test",
        notes=(),
    )
    assert bad.is_valid is False
    assert bad.sample_size < MIN_SPECIALIST_SAMPLE_SIZE


def test_low_reliability_ignored():
    bad = PairSpecialist(
        source_league_id=564,
        target_league_id=384,
        role=None,
        sample_size=100,
        reliability=0.40,
        rating_multiplier=0.90,
        confidence_multiplier=1.0,
        learned_version="test",
        notes=(),
    )
    assert bad.is_valid is False
    assert bad.reliability < MIN_SPECIALIST_RELIABILITY


def test_apply_pair_specialist_clamped():
    skill = PlayerSkillVector(player_id=1, role="forward", overall=0.8, sample_confidence=0.7)
    base = TransferEstimate(
        player_id=1,
        source_league_id=564,
        target_league_id=384,
        rating=0.72,
        skill_vector=skill,
        confidence=0.60,
        adapter_type="general_adapter",
        specialist_key=None,
        notes=("general_adapter",),
    )
    specialist = PairSpecialist(
        source_league_id=564,
        target_league_id=384,
        role="forward",
        sample_size=45,
        reliability=0.68,
        rating_multiplier=0.93,
        confidence_multiplier=1.02,
        learned_version="test",
        notes=(),
    )
    adjusted = apply_pair_specialist(base, specialist)
    assert adjusted.adapter_type == "pair_specialist"
    assert 0.0 <= adjusted.rating <= 1.0
    assert 0.0 <= adjusted.confidence <= 1.0
    assert adjusted.specialist_key == "564->384:forward"
