"""Advanced team strength ratings con rolling e opponent adjustment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import ParticipantLocation
from src.features.team_strength import compute_team_strengths


@dataclass(frozen=True)
class AdvancedTeamStrength:
    team_id: int
    attack_rating: float
    defense_rating: float
    home_attack_rating: float
    home_defense_rating: float
    away_attack_rating: float
    away_defense_rating: float
    opponent_adjusted_strength: float
    rolling_5_strength: float
    rolling_10_strength: float
    season_strength: float


def _opponent_id(match, team_id: int) -> int:
    for participant in match.participants:
        if participant.team_id != team_id:
            return participant.team_id
    raise ValueError(f"Opponent not found for team {team_id}")


def _match_strength_delta(dataset: MatchDataset, match, team_id: int) -> float:
    scored, conceded = dataset.team_goals(team_id, match)
    return (scored - conceded) / 3.0


def compute_advanced_strength(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    settings: Settings,
) -> AdvancedTeamStrength:
    base = compute_team_strengths(dataset, team_id, as_of, settings)
    history = dataset.team_history(team_id, as_of)

    rolling_5 = history[-5:]
    rolling_10 = history[-10:]
    r5 = sum(_match_strength_delta(dataset, m, team_id) for m in rolling_5) / max(len(rolling_5), 1)
    r10 = sum(_match_strength_delta(dataset, m, team_id) for m in rolling_10) / max(len(rolling_10), 1)
    season = sum(_match_strength_delta(dataset, m, team_id) for m in history) / max(len(history), 1)

    opp_adj_total = 0.0
    opp_count = 0
    for match in history:
        opp_id = _opponent_id(match, team_id)
        opp_strength = compute_team_strengths(dataset, opp_id, match.starting_at, settings)
        delta = _match_strength_delta(dataset, match, team_id)
        opp_factor = (opp_strength.attack + opp_strength.defense) / 2.0
        opp_adj_total += delta + opp_factor * 0.25
        opp_count += 1
    opponent_adjusted = opp_adj_total / max(opp_count, 1)

    season_strength = (base.attack - base.defense + season) / 2.0

    return AdvancedTeamStrength(
        team_id=team_id,
        attack_rating=base.attack,
        defense_rating=base.defense,
        home_attack_rating=base.attack_home,
        home_defense_rating=base.defense_home,
        away_attack_rating=base.attack_away,
        away_defense_rating=base.defense_away,
        opponent_adjusted_strength=opponent_adjusted,
        rolling_5_strength=r5,
        rolling_10_strength=r10,
        season_strength=season_strength,
    )


def advanced_strength_to_features(prefix: str, strength: AdvancedTeamStrength) -> dict[str, float]:
    return {
        f"{prefix}_attack_rating": strength.attack_rating,
        f"{prefix}_defense_rating": strength.defense_rating,
        f"{prefix}_attack_home_rating": strength.home_attack_rating,
        f"{prefix}_defense_home_rating": strength.home_defense_rating,
        f"{prefix}_attack_away_rating": strength.away_attack_rating,
        f"{prefix}_defense_away_rating": strength.away_defense_rating,
        f"{prefix}_opponent_adjusted_strength": strength.opponent_adjusted_strength,
        f"{prefix}_rolling_5_strength": strength.rolling_5_strength,
        f"{prefix}_rolling_10_strength": strength.rolling_10_strength,
        f"{prefix}_season_strength": strength.season_strength,
    }
