"""Policy prudente per allenatori sconosciuti o con dati insufficienti."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnknownCoachPolicy:
    neutral_signal: float = 0.50
    default_confidence: float = 0.10
    low_sample_matches_threshold: int = 10
    low_career_matches_threshold: int = 30
    low_sample_confidence_cap: float = 0.30
    unknown_origin_confidence_cap: float = 0.25
    cross_country_new_coach_confidence_cap: float = 0.35
    max_new_manager_bounce_signal: float = 0.20
    recent_change_matches_threshold: int = 5


DEFAULT_COACH_POLICY = UnknownCoachPolicy()
