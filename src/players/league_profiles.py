"""Profili mock delle leghe per adattamento trasferimenti (placeholder offline)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from src.config import FIXTURES_DIR

LEAGUE_PROFILES_PATH = FIXTURES_DIR / "league_profiles.json"

# Valori placeholder — da calibrare con dati reali in futuro.


@dataclass(frozen=True)
class LeagueProfile:
    league_id: int
    name: str
    strength_index: float
    pace_index: float
    physicality_index: float
    tactical_complexity_index: float
    defensive_intensity_index: float
    scoring_environment_index: float
    data_quality: float
    confidence: float


FALLBACK_PROFILE = LeagueProfile(
    league_id=-1,
    name="Unknown league (fallback)",
    strength_index=0.50,
    pace_index=0.50,
    physicality_index=0.50,
    tactical_complexity_index=0.50,
    defensive_intensity_index=0.50,
    scoring_environment_index=0.50,
    data_quality=0.40,
    confidence=0.35,
)


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(float(value), 1.0))


def _profile_from_dict(data: dict) -> LeagueProfile:
    return LeagueProfile(
        league_id=int(data["league_id"]),
        name=str(data["name"]),
        strength_index=_clamp01(float(data["strength_index"])),
        pace_index=_clamp01(float(data["pace_index"])),
        physicality_index=_clamp01(float(data["physicality_index"])),
        tactical_complexity_index=_clamp01(float(data["tactical_complexity_index"])),
        defensive_intensity_index=_clamp01(float(data["defensive_intensity_index"])),
        scoring_environment_index=_clamp01(float(data["scoring_environment_index"])),
        data_quality=_clamp01(float(data["data_quality"])),
        confidence=_clamp01(float(data["confidence"])),
    )


def load_league_profiles(*, path: Path | None = None) -> dict[int, LeagueProfile]:
    source = path or LEAGUE_PROFILES_PATH
    if not source.exists():
        return {}
    payload = json.loads(source.read_text(encoding="utf-8"))
    return {
        int(item["league_id"]): _profile_from_dict(item)
        for item in payload.get("leagues", ())
    }


def get_league_profile(
    league_id: int,
    *,
    profiles: dict[int, LeagueProfile] | None = None,
) -> LeagueProfile:
    registry = profiles if profiles is not None else load_league_profiles()
    profile = registry.get(league_id)
    if profile is None:
        return LeagueProfile(
            league_id=league_id,
            name=f"Unknown league {league_id} (fallback)",
            strength_index=FALLBACK_PROFILE.strength_index,
            pace_index=FALLBACK_PROFILE.pace_index,
            physicality_index=FALLBACK_PROFILE.physicality_index,
            tactical_complexity_index=FALLBACK_PROFILE.tactical_complexity_index,
            defensive_intensity_index=FALLBACK_PROFILE.defensive_intensity_index,
            scoring_environment_index=FALLBACK_PROFILE.scoring_environment_index,
            data_quality=FALLBACK_PROFILE.data_quality,
            confidence=FALLBACK_PROFILE.confidence,
        )
    return profile
