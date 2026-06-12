"""Skill vector normalizzato del giocatore (0..1)."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from src.players.global_registry import PlayerLeagueSnapshot

ROLE_ALIASES: dict[str, str] = {
    "FW": "forward",
    "ST": "forward",
    "CF": "forward",
    "AM": "midfielder",
    "CM": "midfielder",
    "DM": "midfielder",
    "MF": "midfielder",
    "CB": "defender",
    "FB": "defender",
    "DF": "defender",
    "GK": "goalkeeper",
}


def clamp01(value: float | None, default: float | None = None) -> float | None:
    if value is None:
        return default
    if not math.isfinite(value):
        return default if default is not None else 0.0
    return max(0.0, min(float(value), 1.0))


def normalize_role(position: str | None) -> str | None:
    if position is None:
        return None
    key = position.strip().upper()
    if key.lower() in {"forward", "midfielder", "defender", "goalkeeper"}:
        return key.lower()
    return ROLE_ALIASES.get(key, key.lower() if key else None)


@dataclass(frozen=True)
class PlayerSkillVector:
    player_id: int
    role: str | None
    overall: float
    finishing: float | None = None
    chance_creation: float | None = None
    progressive_passing: float | None = None
    duels: float | None = None
    aerial: float | None = None
    pressing: float | None = None
    defensive_actions: float | None = None
    availability: float | None = None
    sample_confidence: float = 0.5

    def sanitized(self) -> PlayerSkillVector:
        return PlayerSkillVector(
            player_id=self.player_id,
            role=self.role,
            overall=clamp01(self.overall, 0.0) or 0.0,
            finishing=clamp01(self.finishing),
            chance_creation=clamp01(self.chance_creation),
            progressive_passing=clamp01(self.progressive_passing),
            duels=clamp01(self.duels),
            aerial=clamp01(self.aerial),
            pressing=clamp01(self.pressing),
            defensive_actions=clamp01(self.defensive_actions),
            availability=clamp01(self.availability),
            sample_confidence=clamp01(self.sample_confidence, 0.0) or 0.0,
        )


def _derive_role_skills(role: str | None, base: float, percentile: float) -> dict[str, float | None]:
    """Deriva skill mock da overall e percentile (placeholder offline)."""
    if role == "forward":
        return {
            "finishing": clamp01(base * 1.05 + percentile * 0.05),
            "chance_creation": clamp01(base * 0.85),
            "progressive_passing": clamp01(base * 0.75),
            "duels": clamp01(base * 0.80),
            "aerial": clamp01(base * 0.70 + percentile * 0.05),
            "pressing": clamp01(base * 0.65),
            "defensive_actions": clamp01(base * 0.45),
            "availability": clamp01(percentile * 0.9),
        }
    if role == "midfielder":
        return {
            "finishing": clamp01(base * 0.75),
            "chance_creation": clamp01(base * 0.95 + percentile * 0.05),
            "progressive_passing": clamp01(base * 1.0 + percentile * 0.05),
            "duels": clamp01(base * 0.85),
            "aerial": clamp01(base * 0.65),
            "pressing": clamp01(base * 0.90),
            "defensive_actions": clamp01(base * 0.80),
            "availability": clamp01(percentile * 0.88),
        }
    if role == "defender":
        return {
            "finishing": clamp01(base * 0.45),
            "chance_creation": clamp01(base * 0.55),
            "progressive_passing": clamp01(base * 0.70),
            "duels": clamp01(base * 0.95),
            "aerial": clamp01(base * 0.90 + percentile * 0.05),
            "pressing": clamp01(base * 0.75),
            "defensive_actions": clamp01(base * 1.0 + percentile * 0.05),
            "availability": clamp01(percentile * 0.85),
        }
    if role == "goalkeeper":
        return {
            "finishing": None,
            "chance_creation": None,
            "progressive_passing": clamp01(base * 0.55),
            "duels": clamp01(base * 0.60),
            "aerial": clamp01(base * 0.85),
            "pressing": None,
            "defensive_actions": clamp01(base * 1.0),
            "availability": clamp01(percentile * 0.90),
        }
    return {
        "finishing": clamp01(base * 0.85),
        "chance_creation": clamp01(base * 0.85),
        "progressive_passing": clamp01(base * 0.85),
        "duels": clamp01(base * 0.85),
        "aerial": clamp01(base * 0.80),
        "pressing": clamp01(base * 0.80),
        "defensive_actions": clamp01(base * 0.80),
        "availability": clamp01(percentile * 0.85),
    }


def skill_from_snapshot(snapshot: PlayerLeagueSnapshot) -> PlayerSkillVector:
    """Converte snapshot lega in skill vector normalizzato 0..1."""
    role = normalize_role(snapshot.position)
    overall = clamp01(snapshot.rating / 10.0, 0.0) or 0.0
    percentile = clamp01(snapshot.rating_percentile, 0.5) or 0.5
    minutes_factor = clamp01(snapshot.minutes / 3000.0, 0.0) or 0.0
    confidence = clamp01(
        snapshot.sample_confidence * (0.6 + 0.4 * minutes_factor),
        0.0,
    ) or 0.0
    skills = _derive_role_skills(role, overall, percentile)
    return PlayerSkillVector(
        player_id=snapshot.player_id,
        role=role,
        overall=overall,
        sample_confidence=confidence,
        **skills,
    ).sanitized()


def blend_skill_vectors(
    a: PlayerSkillVector,
    b: PlayerSkillVector,
    weight_b: float,
) -> PlayerSkillVector:
    w = clamp01(weight_b, 0.0) or 0.0

    def blend(x: float | None, y: float | None) -> float | None:
        if x is None and y is None:
            return None
        if x is None:
            return y
        if y is None:
            return x
        return clamp01((1.0 - w) * x + w * y)

    return PlayerSkillVector(
        player_id=a.player_id,
        role=b.role or a.role,
        overall=blend(a.overall, b.overall) or 0.0,
        finishing=blend(a.finishing, b.finishing),
        chance_creation=blend(a.chance_creation, b.chance_creation),
        progressive_passing=blend(a.progressive_passing, b.progressive_passing),
        duels=blend(a.duels, b.duels),
        aerial=blend(a.aerial, b.aerial),
        pressing=blend(a.pressing, b.pressing),
        defensive_actions=blend(a.defensive_actions, b.defensive_actions),
        availability=blend(a.availability, b.availability),
        sample_confidence=blend(a.sample_confidence, b.sample_confidence) or 0.0,
    ).sanitized()
