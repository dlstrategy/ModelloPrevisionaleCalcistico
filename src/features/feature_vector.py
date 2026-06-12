"""Assemblaggio feature_vector da tutti i moduli feature."""

from __future__ import annotations

from src.features.advanced_strength import advanced_strength_to_features
from src.features.fatigue_features import fatigue_to_features
from src.features.lineup_features import (
    PlayerLineupSnapshot,
    default_player_lineup_snapshot,
    player_lineup_to_features,
)
from src.features.motivation_features import motivation_to_features
from src.features.schedule_strength import schedule_strength_to_features
from src.features.shots_features import shots_profile_to_features
from src.features.tactical_features import tactical_to_features
from src.features.transfer_lineup_features import build_transfer_lineup_features
from src.features.xg_features import xg_profile_to_features


def build_full_feature_vector(context) -> dict[str, float]:
    """Costruisce il vettore feature completo da MatchContext."""
    hs = context.home_strength
    aws = context.away_strength
    hst = context.home_standings
    ast = context.away_standings

    vec: dict[str, float] = {
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

    vec.update(advanced_strength_to_features("home", context.home_advanced))
    vec.update(advanced_strength_to_features("away", context.away_advanced))
    vec.update(xg_profile_to_features("home", context.home_xg_profile))
    vec.update(xg_profile_to_features("away", context.away_xg_profile))
    vec.update(shots_profile_to_features("home", context.home_shots))
    vec.update(shots_profile_to_features("away", context.away_shots))
    vec.update(schedule_strength_to_features("home", context.home_sos))
    vec.update(schedule_strength_to_features("away", context.away_sos))
    vec.update(motivation_to_features("home", context.home_motivation))
    vec.update(motivation_to_features("away", context.away_motivation))
    vec.update(fatigue_to_features(context.home_fatigue, context.away_fatigue))

    player_snap: PlayerLineupSnapshot = context.player_lineup or default_player_lineup_snapshot(
        context.match.id
    )
    vec.update(player_lineup_to_features(player_snap))
    vec.update(build_transfer_lineup_features(context.match))
    vec.update(tactical_to_features(context.tactical))

    return vec


def summarize_feature_groups(feature_vector: dict[str, float]) -> dict[str, int]:
    from src.features.feature_groups import FEATURE_GROUPS

    summary: dict[str, int] = {}
    for group, keys in FEATURE_GROUPS.items():
        summary[group] = sum(1 for key in keys if key in feature_vector)
    return summary
