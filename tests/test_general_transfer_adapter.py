"""Test general transfer adapter."""

from src.players.general_transfer_adapter import estimate_transfer_with_general_adapter
from src.players.league_profiles import get_league_profile, load_league_profiles
from src.players.player_skill import PlayerSkillVector


def _skill(overall: float = 0.75, confidence: float = 0.80) -> PlayerSkillVector:
    return PlayerSkillVector(
        player_id=1001,
        role="forward",
        overall=overall,
        sample_confidence=confidence,
    ).sanitized()


def test_same_league_no_penalty():
    profiles = load_league_profiles()
    profile = profiles[384]
    est = estimate_transfer_with_general_adapter(
        _skill(),
        profile,
        profile,
        384,
        source_league_id=384,
    )
    assert est.adapter_type == "same_league"
    assert est.rating == 0.75
    assert est.confidence == 0.80


def test_different_profiles_penalize_more():
    profiles = load_league_profiles()
    similar = estimate_transfer_with_general_adapter(
        _skill(),
        profiles[384],
        profiles[564],
        564,
        source_league_id=384,
    )
    distant = estimate_transfer_with_general_adapter(
        _skill(),
        get_league_profile(99999),
        profiles[8],
        8,
        source_league_id=99999,
    )
    assert similar.rating >= distant.rating


def test_confidence_grows_with_matches():
    profiles = load_league_profiles()
    low = estimate_transfer_with_general_adapter(
        _skill(),
        profiles[564],
        profiles[384],
        384,
        source_league_id=564,
        target_matches_played=0,
    )
    high = estimate_transfer_with_general_adapter(
        _skill(),
        profiles[564],
        profiles[384],
        384,
        source_league_id=564,
        target_matches_played=15,
    )
    assert high.confidence > low.confidence


def test_output_bounded():
    profiles = load_league_profiles()
    est = estimate_transfer_with_general_adapter(
        _skill(overall=0.95),
        profiles[8],
        profiles[82],
        82,
        source_league_id=8,
    )
    assert 0.0 <= est.rating <= 1.0
    assert 0.0 <= est.confidence <= 1.0


def test_missing_profile_fallback_no_exception():
    est = estimate_transfer_with_general_adapter(
        _skill(),
        get_league_profile(88888),
        get_league_profile(77777),
        77777,
        source_league_id=88888,
    )
    assert est.adapter_type == "general_adapter"
    assert "fallback_league_profile" in est.notes
