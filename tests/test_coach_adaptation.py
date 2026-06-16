"""Test adattamento allenatore a lega/paese."""

import pytest

from src.coaches.coach_adaptation import estimate_coach_adaptation
from src.coaches.coach_registry import get_team_coach_profile, unknown_coach_profile


def test_same_league_adaptation():
    coach = get_team_coach_profile(1, 384)
    est = estimate_coach_adaptation(coach, 384, "IT")
    assert est.same_league
    assert est.adaptation_score >= 0.85
    assert est.expected_integration_matches <= 6.0
    assert est.adaptation_confidence >= 0.5


def test_same_country_different_league_not_applicable_in_fixture():
    coach = get_team_coach_profile(3, 384)
    est = estimate_coach_adaptation(coach, 384, "IT")
    assert est.cross_country
    assert not est.same_country
    assert 0.45 <= est.adaptation_score <= 0.75


def test_cross_country_adaptation():
    coach = get_team_coach_profile(4, 384)
    est = estimate_coach_adaptation(coach, 384, "IT")
    assert est.cross_country
    assert est.adaptation_score <= 0.70
    assert est.expected_integration_matches >= 10.0
    assert est.early_adaptation_risk > 0.3


def test_unknown_origin():
    coach = get_team_coach_profile(5, 384)
    est = estimate_coach_adaptation(coach, 384, "IT")
    assert est.unknown_origin or est.cross_country
    assert "unknown_coach_origin" in est.notes or "cross_country_coach" in est.notes


def test_unknown_coach_neutral():
    coach = unknown_coach_profile(6, 384)
    est = estimate_coach_adaptation(coach, 384, "IT")
    assert est.adaptation_score == 0.50
    assert est.adaptation_confidence <= 0.15
    assert est.unknown_origin
    assert "unknown_coach_origin" in est.notes


def test_integration_progress_logic():
    coach = get_team_coach_profile(2, 384)
    est = estimate_coach_adaptation(coach, 384, "IT")
    progress = min(coach.matches_in_charge / est.expected_integration_matches, 1.0)
    assert progress == min(3 / est.expected_integration_matches, 1.0)
    assert 0.0 <= progress <= 1.0
    assert est.early_adaptation_risk == pytest.approx(max(0.0, min(1.0, 1.0 - progress)), abs=0.2)
