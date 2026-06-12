"""Specialisti direzionali per coppie lega→lega (opzionali)."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from src.config import FIXTURES_DIR
from src.players.general_transfer_adapter import TransferEstimate
from src.players.player_skill import clamp01

PAIR_SPECIALISTS_PATH = FIXTURES_DIR / "pair_transfer_specialists.json"

MIN_SPECIALIST_SAMPLE_SIZE = 20
MIN_SPECIALIST_RELIABILITY = 0.55


@dataclass(frozen=True)
class PairSpecialist:
    source_league_id: int
    target_league_id: int
    role: str | None
    sample_size: int
    reliability: float
    rating_multiplier: float
    confidence_multiplier: float
    learned_version: str
    notes: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return (
            self.sample_size >= MIN_SPECIALIST_SAMPLE_SIZE
            and self.reliability >= MIN_SPECIALIST_RELIABILITY
        )


def specialist_key(
    source_league_id: int,
    target_league_id: int,
    role: str | None = None,
) -> str:
    role_part = role or "any"
    return f"{source_league_id}->{target_league_id}:{role_part}"


def _specialist_from_dict(data: dict) -> PairSpecialist:
    role = data.get("role")
    return PairSpecialist(
        source_league_id=int(data["source_league_id"]),
        target_league_id=int(data["target_league_id"]),
        role=str(role).lower() if role is not None else None,
        sample_size=int(data["sample_size"]),
        reliability=float(data["reliability"]),
        rating_multiplier=float(data["rating_multiplier"]),
        confidence_multiplier=float(data["confidence_multiplier"]),
        learned_version=str(data.get("learned_version", "unknown")),
        notes=tuple(data.get("notes", ())),
    )


def load_pair_specialists(*, path: Path | None = None) -> dict[str, PairSpecialist]:
    source = path or PAIR_SPECIALISTS_PATH
    if not source.exists():
        return {}
    payload = json.loads(source.read_text(encoding="utf-8"))
    result: dict[str, PairSpecialist] = {}
    for item in payload.get("specialists", ()):
        specialist = _specialist_from_dict(item)
        key = specialist_key(
            specialist.source_league_id,
            specialist.target_league_id,
            specialist.role,
        )
        result[key] = specialist
    return result


def find_best_specialist(
    source_league_id: int,
    target_league_id: int,
    role: str | None = None,
    *,
    specialists: dict[str, PairSpecialist] | None = None,
) -> PairSpecialist | None:
    registry = specialists if specialists is not None else load_pair_specialists()
    candidates: list[PairSpecialist] = []
    if role is not None:
        key = specialist_key(source_league_id, target_league_id, role)
        candidate = registry.get(key)
        if candidate is not None and candidate.is_valid:
            candidates.append(candidate)
    general_key = specialist_key(source_league_id, target_league_id, None)
    general = registry.get(general_key)
    if general is not None and general.is_valid:
        candidates.append(general)
    if not candidates:
        return None
    # Role-specific wins over general when both valid.
    if role is not None:
        role_key = specialist_key(source_league_id, target_league_id, role)
        role_spec = registry.get(role_key)
        if role_spec is not None and role_spec.is_valid:
            return role_spec
    return general


def apply_pair_specialist(
    base_estimate: TransferEstimate,
    specialist: PairSpecialist,
) -> TransferEstimate:
    rating = clamp01(base_estimate.rating * specialist.rating_multiplier, 0.0) or 0.0
    confidence = clamp01(
        base_estimate.confidence * specialist.confidence_multiplier,
        0.0,
    ) or 0.0
    key = specialist_key(
        specialist.source_league_id,
        specialist.target_league_id,
        specialist.role,
    )
    notes = base_estimate.notes + (
        "pair_specialist",
        f"specialist_key={key}",
        f"learned_version={specialist.learned_version}",
        f"sample_size={specialist.sample_size}",
        f"reliability={specialist.reliability:.3f}",
    )
    return replace(
        base_estimate,
        rating=rating,
        confidence=confidence,
        adapter_type="pair_specialist",
        specialist_key=key,
        notes=notes,
    )


def save_pair_specialists(
    specialists: dict[str, PairSpecialist],
    path: Path,
) -> Path:
    """Salva specialisti su JSON — solo chiamata esplicita, non automatica."""
    payload = {
        "specialists": [
            {
                "source_league_id": s.source_league_id,
                "target_league_id": s.target_league_id,
                "role": s.role,
                "sample_size": s.sample_size,
                "reliability": s.reliability,
                "rating_multiplier": s.rating_multiplier,
                "confidence_multiplier": s.confidence_multiplier,
                "learned_version": s.learned_version,
                "notes": list(s.notes),
            }
            for s in specialists.values()
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
