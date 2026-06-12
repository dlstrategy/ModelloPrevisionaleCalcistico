"""Selezione deterministica feature per feature_trained (full vs compact)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.features.feature_groups import FEATURE_GROUPS, keys_for_groups
from src.training.dataset import TrainingSample

VALID_POLICIES = frozenset({"full", "compact"})

COMPACT_GROUPS = frozenset(
    {
        "base",
        "advanced_strength",
        "strength_of_schedule",
        "calendar",
        "motivation",
    }
)

COMPACT_XG_FEATURES = frozenset(
    {
        "home_xg_for_avg",
        "home_xg_against_avg",
        "away_xg_for_avg",
        "away_xg_against_avg",
        "home_xg_diff_avg",
        "away_xg_diff_avg",
        "home_goals_minus_xg",
        "away_goals_minus_xg",
    }
)

COMPACT_SHOTS_FEATURES = frozenset(
    {
        "home_shots_for_avg",
        "home_shots_against_avg",
        "away_shots_for_avg",
        "away_shots_against_avg",
        "home_xg_per_shot",
        "away_xg_per_shot",
        "home_shot_conversion_rate",
        "away_shot_conversion_rate",
    }
)

COMPACT_LINEUP_LEGACY = frozenset(
    {
        "home_starting_xi_attack_rating",
        "away_starting_xi_attack_rating",
        "home_starting_xi_defense_rating",
        "away_starting_xi_defense_rating",
        "home_missing_starters_count",
        "away_missing_starters_count",
        "home_lineup_continuity",
        "away_lineup_continuity",
    }
)

COMPACT_TRANSFER_DIFF = frozenset(
    {
        "lineup_transfer_rating_diff",
        "lineup_transfer_confidence_diff",
        "lineup_unknown_player_share_diff",
        "lineup_low_sample_player_share_diff",
        "lineup_cross_league_player_share_diff",
    }
)


def _compact_allowlist() -> frozenset[str]:
    return (
        keys_for_groups(COMPACT_GROUPS)
        | COMPACT_XG_FEATURES
        | COMPACT_SHOTS_FEATURES
        | COMPACT_LINEUP_LEGACY
        | COMPACT_TRANSFER_DIFF
    )


@dataclass(frozen=True)
class FeaturePolicy:
    name: str
    description: str
    allowed_groups: frozenset[str] | None
    allowed_feature_prefixes: tuple[str, ...]
    blocked_feature_prefixes: tuple[str, ...]
    max_features: int | None
    min_non_zero_ratio: float | None
    variance_threshold: float | None
    default_clip_value: float | None
    default_l2: float


POLICY_FULL = FeaturePolicy(
    name="full",
    description="Tutte le feature disponibili nei sample (comportamento legacy).",
    allowed_groups=None,
    allowed_feature_prefixes=(),
    blocked_feature_prefixes=(),
    max_features=None,
    min_non_zero_ratio=None,
    variance_threshold=None,
    default_clip_value=None,
    default_l2=0.001,
)

POLICY_COMPACT = FeaturePolicy(
    name="compact",
    description=(
        "Feature robuste e aggregate; transfer-aware lineup ridotte ai soli diff principali."
    ),
    allowed_groups=COMPACT_GROUPS,
    allowed_feature_prefixes=(),
    blocked_feature_prefixes=(
        "home_lineup_transfer_",
        "away_lineup_transfer_",
        "home_lineup_unknown_",
        "away_lineup_unknown_",
        "home_lineup_low_sample_",
        "away_lineup_low_sample_",
        "home_lineup_cross_league_",
        "away_lineup_cross_league_",
        "home_lineup_pair_specialist_",
        "away_lineup_pair_specialist_",
        "home_lineup_general_adapter_",
        "away_lineup_general_adapter_",
        "lineup_pair_specialist_share_diff",
        "lineup_general_adapter_share_diff",
    ),
    max_features=None,
    min_non_zero_ratio=0.05,
    variance_threshold=1e-8,
    default_clip_value=5.0,
    default_l2=0.005,
)

_POLICIES: dict[str, FeaturePolicy] = {
    "full": POLICY_FULL,
    "compact": POLICY_COMPACT,
}


def parse_feature_policy(name: str | None) -> FeaturePolicy:
    policy_name = (name or "full").strip().lower()
    if policy_name not in _POLICIES:
        valid = ", ".join(sorted(_POLICIES))
        raise ValueError(f"Feature policy non valida: {name!r}. Valori ammessi: {valid}")
    return _POLICIES[policy_name]


def available_feature_policies() -> dict[str, FeaturePolicy]:
    return dict(_POLICIES)


def collect_feature_names(samples: list[TrainingSample]) -> list[str]:
    names: set[str] = set()
    for sample in samples:
        names.update(sample.features.keys())
    return sorted(names)


def _passes_prefix_rules(name: str, policy: FeaturePolicy) -> bool:
    if policy.blocked_feature_prefixes:
        for prefix in policy.blocked_feature_prefixes:
            if name.startswith(prefix):
                return False
    if policy.allowed_feature_prefixes:
        return any(name.startswith(prefix) for prefix in policy.allowed_feature_prefixes)
    return True


def _candidate_names(samples: list[TrainingSample], policy: FeaturePolicy) -> list[str]:
    available = collect_feature_names(samples)
    if policy.name == "full":
        return available
    allowlist = _compact_allowlist()
    return sorted(name for name in available if name in allowlist and _passes_prefix_rules(name, policy))


def _non_zero_ratio(samples: list[TrainingSample], feature_name: str) -> float:
    if not samples:
        return 0.0
    non_zero = sum(1 for s in samples if abs(s.features.get(feature_name, 0.0)) > 1e-12)
    return non_zero / len(samples)


def _variance(samples: list[TrainingSample], feature_name: str) -> float:
    if len(samples) < 2:
        return 0.0
    values = [float(s.features.get(feature_name, 0.0)) for s in samples]
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def select_features_for_policy(
    samples: list[TrainingSample],
    policy: FeaturePolicy,
) -> tuple[list[str], list[str]]:
    """Seleziona feature names e warnings — solo sui training samples forniti."""
    warnings: list[str] = []
    original_count = len(collect_feature_names(samples))
    candidates = _candidate_names(samples, policy)

    if policy.name == "full":
        if not candidates:
            raise ValueError("Nessuna feature disponibile nei sample di training.")
        return candidates, warnings

    selected: list[str] = []
    for name in candidates:
        if policy.min_non_zero_ratio is not None:
            ratio = _non_zero_ratio(samples, name)
            if ratio < policy.min_non_zero_ratio:
                warnings.append(f"excluded_sparse:{name}:non_zero_ratio={ratio:.3f}")
                continue
        if policy.variance_threshold is not None:
            var = _variance(samples, name)
            if var < policy.variance_threshold:
                warnings.append(f"excluded_low_variance:{name}:var={var:.2e}")
                continue
        selected.append(name)

    if policy.max_features is not None and len(selected) > policy.max_features:
        selected = selected[: policy.max_features]
        warnings.append(f"truncated_to_max_features:{policy.max_features}")

    if not selected:
        raise ValueError(
            f"Feature policy {policy.name!r} non ha selezionato alcuna feature "
            f"(candidati={len(candidates)}, originali={original_count})."
        )

    if len(selected) < original_count:
        warnings.append(
            f"compact_reduced_features:{len(selected)}/{original_count}"
        )
    return selected, warnings


def apply_feature_policy_to_sample(
    sample: TrainingSample,
    selected_feature_names: list[str],
) -> TrainingSample:
    return TrainingSample(
        fixture_id=sample.fixture_id,
        as_of=sample.as_of,
        label=sample.label,
        features={name: float(sample.features.get(name, 0.0)) for name in selected_feature_names},
    )


def compact_transfer_diff_features() -> frozenset[str]:
    return COMPACT_TRANSFER_DIFF


def count_features_for_policy(samples: list[TrainingSample], policy_name: str) -> tuple[int, int]:
    """Ritorna (selected_count, original_count) senza side effects."""
    policy = parse_feature_policy(policy_name)
    original = len(collect_feature_names(samples))
    selected, _ = select_features_for_policy(samples, policy)
    return len(selected), original
