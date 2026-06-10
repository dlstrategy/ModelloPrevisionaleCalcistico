"""Contesto partita arricchito per tutti i modelli."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.match import Match
from src.features.home_away import ScheduleSnapshot, compute_schedule_snapshot
from src.features.lineup_features import LineupImpact, get_lineup_impact
from src.features.recent_form import TeamFormSnapshot, compute_team_form
from src.features.standings_features import TeamStandingsSnapshot, get_team_standings
from src.features.tactical_features import tactical_edge_score
from src.features.team_strength import TeamStrength, compute_team_strengths
from src.features.xg_features import TeamXgSnapshot, get_team_xg


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
    home_xg: TeamXgSnapshot | None = None
    away_xg: TeamXgSnapshot | None = None
    lineup_impact: LineupImpact | None = None
    feature_vector: dict[str, float] = field(default_factory=dict)


def _build_feature_vector(context: MatchContext) -> dict[str, float]:
    hs = context.home_strength
    aws = context.away_strength
    hst = context.home_standings
    ast = context.away_standings
    vec = {
        "home_attack": hs.attack_home,
        "home_defense": hs.defense_home,
        "away_attack": aws.attack_away,
        "away_defense": aws.defense_away,
        "home_form_gf": context.home_form.goals_for,
        "away_form_gf": context.away_form.goals_for,
        "home_form_ga": context.home_form.goals_against,
        "away_form_ga": context.away_form.goals_against,
        "home_position": float(hst.position),
        "away_position": float(ast.position),
        "home_points": float(hst.points),
        "away_points": float(ast.points),
        "position_gap": float(ast.position - hst.position),
        "points_gap": float(hst.points - ast.points),
        "home_rest_days": context.home_schedule.days_since_last_match or 7.0,
        "away_rest_days": context.away_schedule.days_since_last_match or 7.0,
        "home_congestion": float(context.home_schedule.matches_last_14_days),
        "away_congestion": float(context.away_schedule.matches_last_14_days),
        "home_win_streak": float(hst.win_streak),
        "away_win_streak": float(ast.win_streak),
    }
    if context.home_xg:
        vec["home_xg_for"] = context.home_xg.xg_for
        vec["home_xg_against"] = context.home_xg.xg_against
    if context.away_xg:
        vec["away_xg_for"] = context.away_xg.xg_for
        vec["away_xg_against"] = context.away_xg.xg_against
    if context.lineup_impact:
        li = context.lineup_impact
        vec["home_lineup_attack"] = li.home_offensive_quality
        vec["away_lineup_attack"] = li.away_offensive_quality
        vec["home_lineup_defense"] = li.home_defensive_quality
        vec["away_lineup_defense"] = li.away_defensive_quality
        vec["tactical_edge"] = tactical_edge_score(li)
    return vec


def build_match_context(
    dataset: MatchDataset,
    match: Match,
    settings: Settings,
    as_of: datetime | None = None,
) -> MatchContext:
    cutoff = as_of or match.starting_at
    home_id = match.home.team_id
    away_id = match.away.team_id

    context = MatchContext(
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
        home_xg=get_team_xg(match.league_id, home_id),
        away_xg=get_team_xg(match.league_id, away_id),
        lineup_impact=get_lineup_impact(match.league_id, match.id),
    )
    return MatchContext(
        match=context.match,
        as_of=context.as_of,
        home_strength=context.home_strength,
        away_strength=context.away_strength,
        home_advantage=context.home_advantage,
        home_form=context.home_form,
        away_form=context.away_form,
        home_standings=context.home_standings,
        away_standings=context.away_standings,
        home_schedule=context.home_schedule,
        away_schedule=context.away_schedule,
        home_xg=context.home_xg,
        away_xg=context.away_xg,
        lineup_impact=context.lineup_impact,
        feature_vector=_build_feature_vector(context),
    )
