"""Stima prudente adattamento allenatore a lega/paese target."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.coaches.coach_registry import CoachProfile
from src.coaches.unknown_coach_policy import DEFAULT_COACH_POLICY

LEAGUE_COUNTRY: dict[int, str] = {
    384: "IT",
    564: "ES",
    8: "GB",
    82: "DE",
    61: "FR",
    999: "XX",
}


def _clamp01(value: float, default: float = 0.0) -> float:
    if not math.isfinite(value):
        return default
    return max(0.0, min(float(value), 1.0))


@dataclass(frozen=True)
class CoachAdaptationEstimate:
    adaptation_score: float
    adaptation_confidence: float
    same_league: bool
    same_country: bool
    cross_country: bool
    unknown_origin: bool
    expected_integration_matches: float
    early_adaptation_risk: float
    notes: tuple[str, ...]


def _target_country(target_league_id: int, target_country_code: str | None) -> str | None:
    if target_country_code:
        return target_country_code.upper()
    return LEAGUE_COUNTRY.get(target_league_id)


def estimate_coach_adaptation(
    coach: CoachProfile,
    target_league_id: int,
    target_country_code: str | None = None,
) -> CoachAdaptationEstimate:
    policy = DEFAULT_COACH_POLICY
    notes: list[str] = []
    target_cc = _target_country(target_league_id, target_country_code)

    if coach.source == "unknown_coach_fallback" or coach.coach_id is None:
        return CoachAdaptationEstimate(
            adaptation_score=0.50,
            adaptation_confidence=policy.default_confidence,
            same_league=False,
            same_country=False,
            cross_country=False,
            unknown_origin=True,
            expected_integration_matches=16.0,
            early_adaptation_risk=0.85,
            notes=("unknown_coach_origin", "neutral_adaptation"),
        )

    prior_league = coach.prior_league_id
    prior_cc = (coach.prior_country_code or "").upper() if coach.prior_country_code else None
    if prior_cc is None and prior_league is not None:
        prior_cc = LEAGUE_COUNTRY.get(prior_league)

    same_league = prior_league is not None and prior_league == target_league_id
    same_country = (
        prior_cc is not None
        and target_cc is not None
        and prior_cc == target_cc
        and not same_league
    )
    cross_country = (
        prior_cc is not None
        and target_cc is not None
        and prior_cc != target_cc
        and not same_league
    )
    unknown_origin = prior_league is None or prior_cc is None or prior_cc == "XX"

    if same_league:
        base_score = 0.90
        base_integration = 4.0
        notes.append("same_league_coach")
    elif same_country:
        base_score = 0.72
        base_integration = 8.0
        notes.append("same_country_different_league")
    elif cross_country:
        base_score = 0.55
        base_integration = 14.0
        notes.append("cross_country_coach")
    elif unknown_origin:
        base_score = 0.50
        base_integration = 18.0
        notes.append("unknown_coach_origin")
    else:
        base_score = 0.60
        base_integration = 10.0
        notes.append("fallback_adaptation")

    experience_factor = min(coach.prior_league_matches / 80.0, 1.0) * 0.08
    cross_exp_factor = min(coach.cross_country_experience_matches / 60.0, 1.0) * 0.06
    adaptation_score = _clamp01(base_score + experience_factor + cross_exp_factor)

    confidence = coach.data_confidence
    if unknown_origin:
        confidence = min(confidence, policy.unknown_origin_confidence_cap)
        notes.append("unknown_origin_confidence_cap")
    if cross_country and coach.matches_in_charge < policy.low_sample_matches_threshold:
        confidence = min(confidence, policy.cross_country_new_coach_confidence_cap)
        notes.append("cross_country_new_coach_cap")
    if coach.matches_in_charge < policy.low_sample_matches_threshold:
        confidence = min(confidence, policy.low_sample_confidence_cap)
        notes.append("low_sample_coach")
    if coach.career_matches < policy.low_career_matches_threshold:
        confidence = min(confidence, policy.low_sample_confidence_cap)
        notes.append("low_career_sample")

    expected_integration = base_integration
    if coach.prior_league_matches >= 80:
        expected_integration = max(3.0, expected_integration - 2.0)
    if coach.cross_country_experience_matches >= 40:
        expected_integration = max(3.0, expected_integration - 2.0)
    expected_integration = max(3.0, min(expected_integration, 20.0))

    integration_progress = _clamp01(
        coach.matches_in_charge / expected_integration if expected_integration > 0 else 0.0
    )
    early_risk = _clamp01(1.0 - integration_progress)
    if same_league:
        early_risk = _clamp01(early_risk * 0.70)
    if cross_country:
        early_risk = _clamp01(early_risk * 1.15)

    return CoachAdaptationEstimate(
        adaptation_score=adaptation_score,
        adaptation_confidence=confidence,
        same_league=same_league,
        same_country=same_country,
        cross_country=cross_country,
        unknown_origin=unknown_origin,
        expected_integration_matches=expected_integration,
        early_adaptation_risk=early_risk,
        notes=tuple(dict.fromkeys(notes)),
    )
