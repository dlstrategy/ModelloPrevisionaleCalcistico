"""Apprendimento offline pair specialist da osservazioni storiche."""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

from src.config import FIXTURES_DIR
from src.players.pair_specialists import PairSpecialist, specialist_key

TRANSFER_OUTCOMES_PATH = FIXTURES_DIR / "transfer_outcomes.json"
LEARNED_VERSION = "2h-b.1"

MIN_MATCHES_OBSERVED = 5
MIN_MINUTES_OBSERVED = 300
RATING_MULTIPLIER_MIN = 0.75
RATING_MULTIPLIER_MAX = 1.15


@dataclass(frozen=True)
class TransferOutcomeObservation:
    player_id: int
    source_league_id: int
    target_league_id: int
    role: str | None
    predicted_rating: float
    observed_rating_after_transfer: float
    matches_observed: int
    minutes_observed: int

    @property
    def is_sufficient(self) -> bool:
        return (
            self.matches_observed >= MIN_MATCHES_OBSERVED
            or self.minutes_observed >= MIN_MINUTES_OBSERVED
        )


def _observation_from_dict(data: dict) -> TransferOutcomeObservation:
    role = data.get("role")
    return TransferOutcomeObservation(
        player_id=int(data["player_id"]),
        source_league_id=int(data["source_league_id"]),
        target_league_id=int(data["target_league_id"]),
        role=str(role).lower() if role is not None else None,
        predicted_rating=float(data["predicted_rating"]),
        observed_rating_after_transfer=float(data["observed_rating_after_transfer"]),
        matches_observed=int(data["matches_observed"]),
        minutes_observed=int(data["minutes_observed"]),
    )


def load_transfer_outcomes(*, path: Path | None = None) -> list[TransferOutcomeObservation]:
    source = path or TRANSFER_OUTCOMES_PATH
    if not source.exists():
        return []
    payload = json.loads(source.read_text(encoding="utf-8"))
    return [_observation_from_dict(item) for item in payload.get("observations", ())]


def compute_transfer_error(observation: TransferOutcomeObservation) -> float:
    if observation.predicted_rating == 0:
        return 0.0
    return observation.observed_rating_after_transfer - observation.predicted_rating


def aggregate_observations(
    observations: list[TransferOutcomeObservation],
) -> dict[str, list[TransferOutcomeObservation]]:
    buckets: dict[str, list[TransferOutcomeObservation]] = {}
    for obs in observations:
        if not obs.is_sufficient:
            continue
        key = specialist_key(obs.source_league_id, obs.target_league_id, obs.role)
        buckets.setdefault(key, []).append(obs)
    return buckets


def _clamp_multiplier(value: float) -> float:
    if not math.isfinite(value):
        return 1.0
    return max(RATING_MULTIPLIER_MIN, min(value, RATING_MULTIPLIER_MAX))


def learn_pair_specialist_from_observations(
    source_league_id: int,
    target_league_id: int,
    role: str | None,
    observations: list[TransferOutcomeObservation],
) -> PairSpecialist | None:
    filtered = [
        o
        for o in observations
        if o.is_sufficient
        and o.source_league_id == source_league_id
        and o.target_league_id == target_league_id
        and o.role == role
    ]
    if not filtered:
        return None

    ratios: list[float] = []
    for obs in filtered:
        if obs.predicted_rating <= 0:
            continue
        ratios.append(obs.observed_rating_after_transfer / obs.predicted_rating)

    if not ratios:
        return None

    sample_size = len(filtered)
    mean_ratio = statistics.mean(ratios)
    rating_multiplier = _clamp_multiplier(mean_ratio)

    if len(ratios) > 1:
        stdev = statistics.pstdev(ratios)
        variance_penalty = min(stdev * 2.0, 0.35)
    else:
        variance_penalty = 0.20

    reliability = max(0.0, min(1.0, 0.45 + sample_size * 0.02 - variance_penalty))
    confidence_multiplier = max(0.75, min(1.15, 0.85 + reliability * 0.25))

    return PairSpecialist(
        source_league_id=source_league_id,
        target_league_id=target_league_id,
        role=role,
        sample_size=sample_size,
        reliability=reliability,
        rating_multiplier=rating_multiplier,
        confidence_multiplier=confidence_multiplier,
        learned_version=LEARNED_VERSION,
        notes=(
            "learned_from_observations",
            f"mean_ratio={mean_ratio:.3f}",
            f"sample_size={sample_size}",
        ),
    )
