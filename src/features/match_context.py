"""Contesto partita arricchito per tutti i modelli."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.match import Match
from src.features.advanced_strength import AdvancedTeamStrength, compute_advanced_strength
from src.features.fatigue_features import FatigueSnapshot, compute_fatigue_snapshot
from src.features.feature_groups import ALL_GROUPS, filter_feature_vector
from src.features.feature_vector import build_full_feature_vector
from src.features.home_away import ScheduleSnapshot, compute_schedule_snapshot
from src.features.lineup_features import (
    LineupImpact,
    PlayerLineupSnapshot,
    get_lineup_impact,
    get_player_lineup_snapshot,
)
from src.features.motivation_features import MotivationSnapshot, compute_motivation
from src.features.recent_form import TeamFormSnapshot, compute_team_form
from src.features.schedule_strength import ScheduleStrengthSnapshot, compute_schedule_strength
from src.features.shots_features import TeamShotsProfile, get_team_shots_profile
from src.features.standings_features import TeamStandingsSnapshot, get_team_standings
from src.features.tactical_features import TacticalMatchup, get_tactical_matchup
from src.features.team_strength import TeamStrength, compute_team_strengths
from src.features.xg_features import TeamXgProfile, TeamXgSnapshot, get_team_xg, get_team_xg_profile


@dataclass(frozen=True)
class MatchContext:
    match: Match
    as_of: datetime
    home_strength: TeamStrength
    away_strength: TeamStrength
    home_advantage: float
    home_form: TeamFormSnapshot
    away_form: TeamFormSnapshot
    home_standings: TeamStandingsSnapshot
    away_standings: TeamStandingsSnapshot
    home_schedule: ScheduleSnapshot
    away_schedule: ScheduleSnapshot
    home_advanced: AdvancedTeamStrength
    away_advanced: AdvancedTeamStrength
    home_xg_profile: TeamXgProfile
    away_xg_profile: TeamXgProfile
    home_shots: TeamShotsProfile
    away_shots: TeamShotsProfile
    home_sos: ScheduleStrengthSnapshot
    away_sos: ScheduleStrengthSnapshot
    home_motivation: MotivationSnapshot
    away_motivation: MotivationSnapshot
    home_fatigue: FatigueSnapshot
    away_fatigue: FatigueSnapshot
    tactical: TacticalMatchup
    home_xg: TeamXgSnapshot | None = None
    away_xg: TeamXgSnapshot | None = None
    lineup_impact: LineupImpact | None = None
    player_lineup: PlayerLineupSnapshot | None = None
    feature_vector: dict[str, float] = field(default_factory=dict)
    enabled_feature_groups: frozenset[str] = ALL_GROUPS


def build_match_context(
    dataset: MatchDataset,
    match: Match,
    settings: Settings,
    as_of: datetime | None = None,
    *,
    enabled_feature_groups: frozenset[str] | None = None,
) -> MatchContext:
    cutoff = as_of or match.starting_at
    home_id = match.home.team_id
    away_id = match.away.team_id
    league_id = match.league_id
    groups = enabled_feature_groups or ALL_GROUPS

    lineup = get_lineup_impact(league_id, match.id)
    player_lineup = get_player_lineup_snapshot(league_id, match.id)
    tactical = get_tactical_matchup(league_id, match.id, lineup)

    partial = MatchContext(
        match=match,
        as_of=cutoff,
        home_strength=compute_team_strengths(dataset, home_id, cutoff, settings),
        away_strength=compute_team_strengths(dataset, away_id, cutoff, settings),
        home_advantage=settings.home_advantage,
        home_form=compute_team_form(dataset, home_id, cutoff, settings),
        away_form=compute_team_form(dataset, away_id, cutoff, settings),
        home_standings=get_team_standings(dataset, home_id, cutoff),
        away_standings=get_team_standings(dataset, away_id, cutoff),
        home_schedule=compute_schedule_snapshot(dataset, home_id, cutoff),
        away_schedule=compute_schedule_snapshot(dataset, away_id, cutoff),
        home_advanced=compute_advanced_strength(dataset, home_id, cutoff, settings),
        away_advanced=compute_advanced_strength(dataset, away_id, cutoff, settings),
        home_xg_profile=get_team_xg_profile(dataset, home_id, cutoff, league_id),
        away_xg_profile=get_team_xg_profile(dataset, away_id, cutoff, league_id),
        home_shots=get_team_shots_profile(dataset, home_id, cutoff, league_id),
        away_shots=get_team_shots_profile(dataset, away_id, cutoff, league_id),
        home_sos=compute_schedule_strength(dataset, home_id, cutoff, settings, league_id),
        away_sos=compute_schedule_strength(dataset, away_id, cutoff, settings, league_id),
        home_motivation=compute_motivation(get_team_standings(dataset, home_id, cutoff)),
        away_motivation=compute_motivation(get_team_standings(dataset, away_id, cutoff)),
        home_fatigue=compute_fatigue_snapshot(dataset, home_id, cutoff, league_id),
        away_fatigue=compute_fatigue_snapshot(dataset, away_id, cutoff, league_id),
        tactical=tactical,
        home_xg=get_team_xg(league_id, home_id),
        away_xg=get_team_xg(league_id, away_id),
        lineup_impact=lineup,
        player_lineup=player_lineup,
        enabled_feature_groups=groups,
    )

    full_vector = build_full_feature_vector(partial)
    filtered = filter_feature_vector(full_vector, groups)

    return MatchContext(
        match=partial.match,
        as_of=partial.as_of,
        home_strength=partial.home_strength,
        away_strength=partial.away_strength,
        home_advantage=partial.home_advantage,
        home_form=partial.home_form,
        away_form=partial.away_form,
        home_standings=partial.home_standings,
        away_standings=partial.away_standings,
        home_schedule=partial.home_schedule,
        away_schedule=partial.away_schedule,
        home_advanced=partial.home_advanced,
        away_advanced=partial.away_advanced,
        home_xg_profile=partial.home_xg_profile,
        away_xg_profile=partial.away_xg_profile,
        home_shots=partial.home_shots,
        away_shots=partial.away_shots,
        home_sos=partial.home_sos,
        away_sos=partial.away_sos,
        home_motivation=partial.home_motivation,
        away_motivation=partial.away_motivation,
        home_fatigue=partial.home_fatigue,
        away_fatigue=partial.away_fatigue,
        tactical=partial.tactical,
        home_xg=partial.home_xg,
        away_xg=partial.away_xg,
        lineup_impact=partial.lineup_impact,
        player_lineup=partial.player_lineup,
        feature_vector=filtered,
        enabled_feature_groups=groups,
    )
