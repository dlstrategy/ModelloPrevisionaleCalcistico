"""Costruzione dataset di training da match finiti."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import Settings
from src.data_capabilities.resolver import parse_data_profile
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import MatchOutcome
from src.features.match_context import build_match_context

_OUTCOME_LABEL = {
    MatchOutcome.HOME: "HOME",
    MatchOutcome.DRAW: "DRAW",
    MatchOutcome.AWAY: "AWAY",
}


@dataclass(frozen=True)
class TrainingSample:
    fixture_id: int
    as_of: str
    label: str  # HOME | DRAW | AWAY
    features: dict[str, float]


def build_training_samples(
    dataset: MatchDataset,
    settings: Settings,
    *,
    profile: str | None = None,
    min_finished_matches: int = 10,
) -> list[TrainingSample]:
    profile_name = parse_data_profile(profile or settings.data_profile)
    samples: list[TrainingSample] = []

    for match in dataset.matches:
        if not match.is_finished:
            continue
        outcome = match.actual_outcome
        if outcome is None:
            continue

        ctx = build_match_context(
            dataset,
            match,
            settings,
            as_of=match.starting_at,
            profile=profile_name,
        )
        if not ctx.feature_vector:
            continue

        samples.append(
            TrainingSample(
                fixture_id=match.id,
                as_of=match.starting_at.isoformat(),
                label=_OUTCOME_LABEL[outcome],
                features=dict(ctx.feature_vector),
            )
        )

    return samples
