"""Feature aggregate transfer-aware sulle formazioni (gruppo player_lineup)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from src.domain.match import Match
from src.features.lineup_features import get_fixture_lineup_row
from src.players.player_value import resolve_player_value_for_league
from src.players.unknown_player_policy import DEFAULT_POLICY

EXPECTED_STARTING_XI = 11
NEUTRAL_RATING = DEFAULT_POLICY.neutral_rating
NEUTRAL_CONFIDENCE = DEFAULT_POLICY.default_confidence

TRANSFER_LINEUP_FEATURE_KEYS: frozenset[str] = frozenset(
    {
        "home_lineup_transfer_avg_rating",
        "away_lineup_transfer_avg_rating",
        "home_lineup_transfer_avg_confidence",
        "away_lineup_transfer_avg_confidence",
        "home_lineup_unknown_player_share",
        "away_lineup_unknown_player_share",
        "home_lineup_low_sample_player_share",
        "away_lineup_low_sample_player_share",
        "home_lineup_cross_league_player_share",
        "away_lineup_cross_league_player_share",
        "home_lineup_pair_specialist_share",
        "away_lineup_pair_specialist_share",
        "home_lineup_general_adapter_share",
        "away_lineup_general_adapter_share",
        "home_lineup_unknown_league_share",
        "away_lineup_unknown_league_share",
        "home_lineup_unknown_role_share",
        "away_lineup_unknown_role_share",
        "home_lineup_transfer_missing_player_share",
        "away_lineup_transfer_missing_player_share",
        "lineup_transfer_rating_diff",
        "lineup_transfer_confidence_diff",
        "lineup_unknown_player_share_diff",
        "lineup_low_sample_player_share_diff",
        "lineup_cross_league_player_share_diff",
        "lineup_pair_specialist_share_diff",
        "lineup_general_adapter_share_diff",
    }
)


def _clamp01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(float(value), 1.0))


def _clamp_diff(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(-1.0, min(float(value), 1.0))


def extract_lineup_player_ids(lineup_row: dict | None, side: str) -> list[int]:
    """Estrae player_id dall'XI mock (campo opzionale starting_xi_player_ids)."""
    if not lineup_row:
        return []
    block = lineup_row.get(f"{side}_player")
    if not isinstance(block, dict):
        return []
    raw = block.get("starting_xi_player_ids")
    if not isinstance(raw, list):
        return []
    ids: list[int] = []
    for item in raw:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


@dataclass(frozen=True)
class SideLineupTransferStats:
    avg_rating: float
    avg_confidence: float
    unknown_player_share: float
    low_sample_player_share: float
    cross_league_player_share: float
    pair_specialist_share: float
    general_adapter_share: float
    unknown_league_share: float
    unknown_role_share: float
    missing_player_share: float
    evaluated_count: int


def _share(count: int, evaluated: int) -> float:
    if evaluated <= 0:
        return 0.0
    return _clamp01(count / evaluated)


def _aggregate_side(
    player_ids: list[int],
    target_league_id: int,
    *,
    resolve: Callable[..., dict] | None = None,
) -> SideLineupTransferStats:
    resolver = resolve or resolve_player_value_for_league
    evaluated = len(player_ids)
    missing = max(0, EXPECTED_STARTING_XI - evaluated)
    missing_share = _clamp01(missing / EXPECTED_STARTING_XI)

    if evaluated == 0:
        return SideLineupTransferStats(
            avg_rating=NEUTRAL_RATING,
            avg_confidence=NEUTRAL_CONFIDENCE,
            unknown_player_share=0.0,
            low_sample_player_share=0.0,
            cross_league_player_share=0.0,
            pair_specialist_share=0.0,
            general_adapter_share=0.0,
            unknown_league_share=0.0,
            unknown_role_share=0.0,
            missing_player_share=missing_share if missing else 1.0,
            evaluated_count=0,
        )

    ratings: list[float] = []
    confidences: list[float] = []
    unknown = low_sample = cross_league = pair_spec = general = unknown_league = unknown_role = 0

    for player_id in player_ids:
        value = resolver(player_id, target_league_id)
        ratings.append(_clamp01(float(value.get("rating", NEUTRAL_RATING))))
        confidences.append(_clamp01(float(value.get("confidence", NEUTRAL_CONFIDENCE))))
        source = str(value.get("source", ""))
        notes = [str(n) for n in value.get("notes", ())]
        source_league_id = value.get("source_league_id")

        if source == "unknown_player":
            unknown += 1
        if any(n in notes for n in ("low_sample_minutes", "low_sample_confidence", "low_sample_player")):
            low_sample += 1
        if source == "pair_specialist":
            pair_spec += 1
        if source == "general_adapter":
            general += 1
        if source_league_id is not None and source_league_id != target_league_id and source != "unknown_player":
            cross_league += 1
        if "unknown_source_league" in notes or (
            "fallback_league_profile" in notes and source != "same_league"
        ):
            unknown_league += 1
        if "unknown_role" in notes:
            unknown_role += 1

    return SideLineupTransferStats(
        avg_rating=_clamp01(sum(ratings) / len(ratings)),
        avg_confidence=_clamp01(sum(confidences) / len(confidences)),
        unknown_player_share=_share(unknown, evaluated),
        low_sample_player_share=_share(low_sample, evaluated),
        cross_league_player_share=_share(cross_league, evaluated),
        pair_specialist_share=_share(pair_spec, evaluated),
        general_adapter_share=_share(general, evaluated),
        unknown_league_share=_share(unknown_league, evaluated),
        unknown_role_share=_share(unknown_role, evaluated),
        missing_player_share=missing_share,
        evaluated_count=evaluated,
    )


def _side_to_prefix(prefix: str, stats: SideLineupTransferStats) -> dict[str, float]:
    return {
        f"{prefix}_lineup_transfer_avg_rating": stats.avg_rating,
        f"{prefix}_lineup_transfer_avg_confidence": stats.avg_confidence,
        f"{prefix}_lineup_unknown_player_share": stats.unknown_player_share,
        f"{prefix}_lineup_low_sample_player_share": stats.low_sample_player_share,
        f"{prefix}_lineup_cross_league_player_share": stats.cross_league_player_share,
        f"{prefix}_lineup_pair_specialist_share": stats.pair_specialist_share,
        f"{prefix}_lineup_general_adapter_share": stats.general_adapter_share,
        f"{prefix}_lineup_unknown_league_share": stats.unknown_league_share,
        f"{prefix}_lineup_unknown_role_share": stats.unknown_role_share,
        f"{prefix}_lineup_transfer_missing_player_share": stats.missing_player_share,
    }


def build_transfer_lineup_features(
    match: Match,
    *,
    home_player_ids: list[int] | None = None,
    away_player_ids: list[int] | None = None,
    resolve: Callable[..., dict] | None = None,
) -> dict[str, float]:
    """Costruisce feature numeriche aggregate transfer-aware per home/away."""
    lineup_row = get_fixture_lineup_row(match.league_id, match.id)
    home_ids = (
        home_player_ids
        if home_player_ids is not None
        else extract_lineup_player_ids(lineup_row, "home")
    )
    away_ids = (
        away_player_ids
        if away_player_ids is not None
        else extract_lineup_player_ids(lineup_row, "away")
    )

    home = _aggregate_side(home_ids, match.league_id, resolve=resolve)
    away = _aggregate_side(away_ids, match.league_id, resolve=resolve)

    features: dict[str, float] = {}
    features.update(_side_to_prefix("home", home))
    features.update(_side_to_prefix("away", away))
    features["lineup_transfer_rating_diff"] = _clamp_diff(home.avg_rating - away.avg_rating)
    features["lineup_transfer_confidence_diff"] = _clamp_diff(
        home.avg_confidence - away.avg_confidence
    )
    features["lineup_unknown_player_share_diff"] = _clamp_diff(
        home.unknown_player_share - away.unknown_player_share
    )
    features["lineup_low_sample_player_share_diff"] = _clamp_diff(
        home.low_sample_player_share - away.low_sample_player_share
    )
    features["lineup_cross_league_player_share_diff"] = _clamp_diff(
        home.cross_league_player_share - away.cross_league_player_share
    )
    features["lineup_pair_specialist_share_diff"] = _clamp_diff(
        home.pair_specialist_share - away.pair_specialist_share
    )
    features["lineup_general_adapter_share_diff"] = _clamp_diff(
        home.general_adapter_share - away.general_adapter_share
    )
    return features


def build_transfer_lineup_summary(
    match: Match,
    *,
    home_player_ids: list[int] | None = None,
    away_player_ids: list[int] | None = None,
    resolve: Callable[..., dict] | None = None,
) -> dict:
    """Sintesi per explain — non entra nel feature vector numerico."""
    lineup_row = get_fixture_lineup_row(match.league_id, match.id)
    home_ids = (
        home_player_ids
        if home_player_ids is not None
        else extract_lineup_player_ids(lineup_row, "home")
    )
    away_ids = (
        away_player_ids
        if away_player_ids is not None
        else extract_lineup_player_ids(lineup_row, "away")
    )
    home = _aggregate_side(home_ids, match.league_id, resolve=resolve)
    away = _aggregate_side(away_ids, match.league_id, resolve=resolve)

    def side_dict(stats: SideLineupTransferStats) -> dict:
        return {
            "avg_rating": round(stats.avg_rating, 4),
            "avg_confidence": round(stats.avg_confidence, 4),
            "unknown_share": round(stats.unknown_player_share, 4),
            "low_sample_share": round(stats.low_sample_player_share, 4),
            "cross_league_share": round(stats.cross_league_player_share, 4),
            "pair_specialist_share": round(stats.pair_specialist_share, 4),
            "general_adapter_share": round(stats.general_adapter_share, 4),
            "missing_player_share": round(stats.missing_player_share, 4),
            "evaluated_players": stats.evaluated_count,
        }

    return {
        "home": side_dict(home),
        "away": side_dict(away),
        "source": "mock_player_career_registry",
    }
