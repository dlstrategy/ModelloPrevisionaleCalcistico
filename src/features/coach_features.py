"""Feature aggregate impatto allenatore."""

from __future__ import annotations

import math
from typing import Any

from src.coaches.coach_adaptation import CoachAdaptationEstimate, estimate_coach_adaptation
from src.coaches.coach_registry import CoachProfile, get_team_coach_profile
from src.coaches.unknown_coach_policy import DEFAULT_COACH_POLICY
from src.domain.match import Match
from src.features.tactical_features import TacticalMatchup

STYLE_FIT_LOW_CONFIDENCE_THRESHOLD = 0.20

COACH_FEATURE_KEYS: frozenset[str] = frozenset(
    {
        "home_coach_tenure_matches",
        "away_coach_tenure_matches",
        "home_coach_tenure_norm",
        "away_coach_tenure_norm",
        "home_recent_coach_change",
        "away_recent_coach_change",
        "home_new_manager_bounce_signal",
        "away_new_manager_bounce_signal",
        "home_coach_ppg_delta",
        "away_coach_ppg_delta",
        "home_coach_attack_delta",
        "away_coach_attack_delta",
        "home_coach_defense_delta",
        "away_coach_defense_delta",
        "home_coach_xg_delta",
        "away_coach_xg_delta",
        "home_coach_xga_delta",
        "away_coach_xga_delta",
        "home_coach_tactical_stability",
        "away_coach_tactical_stability",
        "home_coach_lineup_rotation_rate",
        "away_coach_lineup_rotation_rate",
        "home_coach_data_confidence",
        "away_coach_data_confidence",
        "home_unknown_coach",
        "away_unknown_coach",
        "home_low_sample_coach",
        "away_low_sample_coach",
        "home_coach_same_league",
        "away_coach_same_league",
        "home_coach_same_country",
        "away_coach_same_country",
        "home_coach_cross_country",
        "away_coach_cross_country",
        "home_coach_adaptation_score",
        "away_coach_adaptation_score",
        "home_coach_adaptation_confidence",
        "away_coach_adaptation_confidence",
        "home_coach_expected_integration_matches",
        "away_coach_expected_integration_matches",
        "home_coach_integration_progress",
        "away_coach_integration_progress",
        "home_coach_early_adaptation_risk",
        "away_coach_early_adaptation_risk",
        "home_coach_style_fit",
        "away_coach_style_fit",
        "home_coach_style_fit_confidence",
        "away_coach_style_fit_confidence",
        "home_coach_potential_signal",
        "away_coach_potential_signal",
        "coach_tenure_diff",
        "coach_ppg_delta_diff",
        "coach_attack_delta_diff",
        "coach_defense_delta_diff",
        "coach_xg_delta_diff",
        "coach_xga_delta_diff",
        "coach_tactical_stability_diff",
        "coach_lineup_rotation_diff",
        "coach_confidence_diff",
        "unknown_coach_diff",
        "low_sample_coach_diff",
        "coach_adaptation_score_diff",
        "coach_adaptation_confidence_diff",
        "coach_integration_progress_diff",
        "coach_early_adaptation_risk_diff",
        "coach_style_fit_diff",
        "coach_style_fit_confidence_diff",
        "coach_potential_signal_diff",
    }
)


def _finite(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(value)


def _clamp01(value: float) -> float:
    return max(0.0, min(_finite(value), 1.0))


def _clamp_diff(value: float) -> float:
    return max(-1.0, min(_finite(value), 1.0))


def _ppg_delta(coach: CoachProfile) -> float:
    if coach.team_ppg_under_coach is None or coach.team_ppg_before is None:
        return 0.0
    return _clamp_diff(coach.team_ppg_under_coach - coach.team_ppg_before)


def _tactical_stability(coach: CoachProfile) -> float:
    if coach.formation_changes_last_10 is None:
        return 0.50
    return _clamp01(1.0 - coach.formation_changes_last_10 / 10.0)


def _is_unknown(coach: CoachProfile) -> bool:
    return coach.source == "unknown_coach_fallback" or coach.coach_id is None


def _is_low_sample(coach: CoachProfile) -> bool:
    policy = DEFAULT_COACH_POLICY
    return (
        coach.matches_in_charge < policy.low_sample_matches_threshold
        or coach.career_matches < policy.low_career_matches_threshold
    )


def _bounce_signal(coach: CoachProfile) -> float:
    policy = DEFAULT_COACH_POLICY
    if coach.matches_in_charge <= 0 or coach.matches_in_charge > 8:
        return 0.0
    raw = min(coach.matches_in_charge / 8.0, 1.0) * 0.25
    capped = min(raw, policy.max_new_manager_bounce_signal)
    return _clamp01(capped * coach.data_confidence)


def _style_fit(
    coach: CoachProfile,
    tactical: TacticalMatchup | None,
) -> tuple[float, float, tuple[str, ...]]:
    notes: list[str] = []
    if tactical is None or tactical.source == "default_fallback" or coach.pressing_intensity is None:
        return 0.50, 0.15, ("style_fit_insufficient_data",)
    pressing_gap = abs(coach.pressing_intensity - tactical.pressing_mismatch)
    line_gap = 0.0
    if coach.defensive_line_height is not None:
        line_gap = abs(coach.defensive_line_height - tactical.defensive_line_risk)
    fit = _clamp01(1.0 - (pressing_gap + line_gap) / 2.0)
    confidence = _clamp01(coach.data_confidence * 0.70)
    if confidence < STYLE_FIT_LOW_CONFIDENCE_THRESHOLD or fit == 0.50:
        notes.append("style_fit_insufficient_data")
    return fit, confidence, tuple(dict.fromkeys(notes))


def _potential_signal(
    coach: CoachProfile,
    adaptation: CoachAdaptationEstimate,
    *,
    low_sample: bool,
    tactical_stability: float,
    ppg_delta: float,
    xg_delta: float,
    xga_improvement: float,
    integration_progress: float,
) -> float:
    policy = DEFAULT_COACH_POLICY
    if _is_unknown(coach):
        return policy.neutral_signal
    raw = 0.5
    raw += 0.12 * ppg_delta
    raw += 0.08 * xg_delta
    raw += 0.08 * xga_improvement
    raw += 0.05 * tactical_stability
    raw += 0.05 * adaptation.adaptation_score
    raw += 0.04 * integration_progress
    if low_sample:
        raw -= 0.10
    raw -= 0.06 * adaptation.early_adaptation_risk
    raw = _clamp01(raw)
    return _clamp01(0.5 + (raw - 0.5) * coach.data_confidence)


def _side_features(
    prefix: str,
    coach: CoachProfile,
    adaptation: CoachAdaptationEstimate,
    tactical: TacticalMatchup | None,
) -> dict[str, float]:
    policy = DEFAULT_COACH_POLICY
    unknown = _is_unknown(coach)
    low_sample = _is_low_sample(coach)
    tenure_norm = _clamp01(coach.matches_in_charge / 38.0)
    recent_change = 1.0 if coach.matches_in_charge < policy.recent_change_matches_threshold else 0.0
    ppg_delta = _ppg_delta(coach)
    attack_delta = _clamp_diff(coach.goals_for_delta or 0.0)
    defense_delta = _clamp_diff(-(coach.goals_against_delta or 0.0))
    xg_delta = _clamp_diff(coach.xg_delta or 0.0)
    xga_delta = _clamp_diff(-(coach.xga_delta or 0.0))
    stability = _tactical_stability(coach)
    rotation = _clamp01(coach.lineup_rotation_rate or 0.0)
    confidence = coach.data_confidence
    if low_sample:
        confidence = min(confidence, policy.low_sample_confidence_cap)
    style_fit, style_conf, _ = _style_fit(coach, tactical)
    integration_progress = _clamp01(
        coach.matches_in_charge / adaptation.expected_integration_matches
        if adaptation.expected_integration_matches > 0
        else 0.0
    )
    early_risk = _clamp01(1.0 - integration_progress)
    if adaptation.same_league:
        early_risk = _clamp01(early_risk * 0.70)
    if adaptation.cross_country:
        early_risk = _clamp01(early_risk * 1.15)
    early_risk = _clamp01(early_risk * (0.5 + 0.5 * confidence))

    potential = _potential_signal(
        coach,
        adaptation,
        low_sample=low_sample,
        tactical_stability=stability,
        ppg_delta=ppg_delta,
        xg_delta=xg_delta,
        xga_improvement=xga_delta,
        integration_progress=integration_progress,
    )

    return {
        f"{prefix}_coach_tenure_matches": float(coach.matches_in_charge),
        f"{prefix}_coach_tenure_norm": tenure_norm,
        f"{prefix}_recent_coach_change": recent_change,
        f"{prefix}_new_manager_bounce_signal": _bounce_signal(coach),
        f"{prefix}_coach_ppg_delta": ppg_delta,
        f"{prefix}_coach_attack_delta": attack_delta,
        f"{prefix}_coach_defense_delta": defense_delta,
        f"{prefix}_coach_xg_delta": xg_delta,
        f"{prefix}_coach_xga_delta": xga_delta,
        f"{prefix}_coach_tactical_stability": stability,
        f"{prefix}_coach_lineup_rotation_rate": rotation,
        f"{prefix}_coach_data_confidence": confidence,
        f"{prefix}_unknown_coach": 1.0 if unknown else 0.0,
        f"{prefix}_low_sample_coach": 1.0 if low_sample else 0.0,
        f"{prefix}_coach_same_league": 1.0 if adaptation.same_league else 0.0,
        f"{prefix}_coach_same_country": 1.0 if adaptation.same_country else 0.0,
        f"{prefix}_coach_cross_country": 1.0 if adaptation.cross_country else 0.0,
        f"{prefix}_coach_adaptation_score": adaptation.adaptation_score,
        f"{prefix}_coach_adaptation_confidence": adaptation.adaptation_confidence,
        f"{prefix}_coach_expected_integration_matches": adaptation.expected_integration_matches,
        f"{prefix}_coach_integration_progress": integration_progress,
        f"{prefix}_coach_early_adaptation_risk": early_risk,
        f"{prefix}_coach_style_fit": style_fit,
        f"{prefix}_coach_style_fit_confidence": style_conf,
        f"{prefix}_coach_potential_signal": potential,
    }


def build_coach_features(
    match: Match,
    *,
    tactical: TacticalMatchup | None = None,
) -> dict[str, float]:
    league_id = match.league_id
    home_id = match.home.team_id
    away_id = match.away.team_id

    home_coach = get_team_coach_profile(home_id, league_id)
    away_coach = get_team_coach_profile(away_id, league_id)
    home_adapt = estimate_coach_adaptation(home_coach, league_id)
    away_adapt = estimate_coach_adaptation(away_coach, league_id)

    home_tac = tactical
    away_tac = tactical

    features: dict[str, float] = {}
    home_feats = _side_features("home", home_coach, home_adapt, home_tac)
    away_feats = _side_features("away", away_coach, away_adapt, away_tac)
    features.update(home_feats)
    features.update(away_feats)

    def diff(home_key: str, away_key: str) -> float:
        return _clamp_diff(home_feats[home_key] - away_feats[away_key])

    features["coach_tenure_diff"] = diff("home_coach_tenure_norm", "away_coach_tenure_norm")
    features["coach_ppg_delta_diff"] = diff("home_coach_ppg_delta", "away_coach_ppg_delta")
    features["coach_attack_delta_diff"] = diff("home_coach_attack_delta", "away_coach_attack_delta")
    features["coach_defense_delta_diff"] = diff("home_coach_defense_delta", "away_coach_defense_delta")
    features["coach_xg_delta_diff"] = diff("home_coach_xg_delta", "away_coach_xg_delta")
    features["coach_xga_delta_diff"] = diff("home_coach_xga_delta", "away_coach_xga_delta")
    features["coach_tactical_stability_diff"] = diff("home_coach_tactical_stability", "away_coach_tactical_stability")
    features["coach_lineup_rotation_diff"] = diff("home_coach_lineup_rotation_rate", "away_coach_lineup_rotation_rate")
    features["coach_confidence_diff"] = diff("home_coach_data_confidence", "away_coach_data_confidence")
    features["unknown_coach_diff"] = diff("home_unknown_coach", "away_unknown_coach")
    features["low_sample_coach_diff"] = diff("home_low_sample_coach", "away_low_sample_coach")
    features["coach_adaptation_score_diff"] = diff("home_coach_adaptation_score", "away_coach_adaptation_score")
    features["coach_adaptation_confidence_diff"] = diff("home_coach_adaptation_confidence", "away_coach_adaptation_confidence")
    features["coach_integration_progress_diff"] = diff("home_coach_integration_progress", "away_coach_integration_progress")
    features["coach_early_adaptation_risk_diff"] = diff("home_coach_early_adaptation_risk", "away_coach_early_adaptation_risk")
    features["coach_style_fit_diff"] = diff("home_coach_style_fit", "away_coach_style_fit")
    features["coach_style_fit_confidence_diff"] = diff("home_coach_style_fit_confidence", "away_coach_style_fit_confidence")
    features["coach_potential_signal_diff"] = diff("home_coach_potential_signal", "away_coach_potential_signal")

    return features


def coach_side_style_fit_insufficient(side: dict[str, Any]) -> bool:
    notes = side.get("style_fit_notes") or ()
    if "style_fit_insufficient_data" in notes:
        return True
    confidence = side.get("style_fit_confidence", 1.0)
    return float(confidence) < STYLE_FIT_LOW_CONFIDENCE_THRESHOLD


def _side_summary_entry(
    coach: CoachProfile,
    adaptation: CoachAdaptationEstimate,
    feats: dict[str, float],
    prefix: str,
    tactical: TacticalMatchup | None,
) -> dict[str, Any]:
    _, style_conf, style_notes = _style_fit(coach, tactical)
    return {
        "coach_name": coach.coach_name,
        "tenure_matches": coach.matches_in_charge,
        "recent_change": feats[f"{prefix}_recent_coach_change"],
        "ppg_delta": round(feats[f"{prefix}_coach_ppg_delta"], 4),
        "attack_delta": round(feats[f"{prefix}_coach_attack_delta"], 4),
        "defense_delta": round(feats[f"{prefix}_coach_defense_delta"], 4),
        "tactical_stability": round(feats[f"{prefix}_coach_tactical_stability"], 4),
        "data_confidence": round(coach.data_confidence, 4),
        "unknown_coach": coach.source == "unknown_coach_fallback",
        "low_sample_coach": feats[f"{prefix}_low_sample_coach"] > 0,
        "same_league": adaptation.same_league,
        "same_country": adaptation.same_country,
        "cross_country": adaptation.cross_country,
        "adaptation_score": round(adaptation.adaptation_score, 4),
        "adaptation_confidence": round(adaptation.adaptation_confidence, 4),
        "expected_integration_matches": round(adaptation.expected_integration_matches, 2),
        "integration_progress": round(feats[f"{prefix}_coach_integration_progress"], 4),
        "early_adaptation_risk": round(feats[f"{prefix}_coach_early_adaptation_risk"], 4),
        "style_fit": round(feats[f"{prefix}_coach_style_fit"], 4),
        "style_fit_confidence": round(feats[f"{prefix}_coach_style_fit_confidence"], 4),
        "potential_signal": round(feats[f"{prefix}_coach_potential_signal"], 4),
        "adaptation_notes": list(adaptation.notes),
        "style_fit_notes": list(style_notes),
    }


def build_coach_summary(
    match: Match,
    *,
    tactical: TacticalMatchup | None = None,
) -> dict[str, Any]:
    league_id = match.league_id
    home_coach = get_team_coach_profile(match.home.team_id, league_id)
    away_coach = get_team_coach_profile(match.away.team_id, league_id)
    home_adapt = estimate_coach_adaptation(home_coach, league_id)
    away_adapt = estimate_coach_adaptation(away_coach, league_id)
    home_feats = _side_features("home", home_coach, home_adapt, tactical)
    away_feats = _side_features("away", away_coach, away_adapt, tactical)

    has_known = (
        home_coach.source != "unknown_coach_fallback"
        or away_coach.source != "unknown_coach_fallback"
    )
    return {
        "home": _side_summary_entry(home_coach, home_adapt, home_feats, "home", tactical),
        "away": _side_summary_entry(away_coach, away_adapt, away_feats, "away", tactical),
        "source": "mock_coach_profiles" if has_known else "unknown_coach_fallback",
    }
