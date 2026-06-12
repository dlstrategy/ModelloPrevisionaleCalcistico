"""Test league profiles."""

from src.players.league_profiles import FALLBACK_PROFILE, get_league_profile, load_league_profiles


def test_load_league_profiles():
    profiles = load_league_profiles()
    assert len(profiles) >= 5
    assert 384 in profiles
    assert 564 in profiles


def test_profile_confidence_in_range():
    for profile in load_league_profiles().values():
        assert 0.0 <= profile.confidence <= 1.0
        assert 0.0 <= profile.strength_index <= 1.0
        assert 0.0 <= profile.data_quality <= 1.0


def test_profile_indices_finite():
    for profile in load_league_profiles().values():
        for field in (
            profile.pace_index,
            profile.physicality_index,
            profile.tactical_complexity_index,
            profile.defensive_intensity_index,
            profile.scoring_environment_index,
        ):
            assert field == field  # not NaN
            assert 0.0 <= field <= 1.0


def test_unknown_league_uses_fallback():
    profile = get_league_profile(99999)
    assert profile.confidence <= FALLBACK_PROFILE.confidence + 0.01
    assert profile.strength_index == FALLBACK_PROFILE.strength_index
