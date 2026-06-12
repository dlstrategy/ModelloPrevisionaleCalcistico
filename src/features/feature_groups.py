"""Gruppi di feature per ablation test e FeatureModel."""

from __future__ import annotations

# Chiavi per gruppo — usate per filtrare feature_vector in ablation
FEATURE_GROUPS: dict[str, frozenset[str]] = {
    "base": frozenset(
        {
            "home_attack",
            "home_defense",
            "away_attack",
            "away_defense",
            "home_form_gf",
            "away_form_gf",
            "home_form_ga",
            "away_form_ga",
            "home_position",
            "away_position",
            "home_points",
            "away_points",
            "position_gap",
            "points_gap",
            "home_rest_days",
            "away_rest_days",
            "home_congestion",
            "away_congestion",
            "home_win_streak",
            "away_win_streak",
        }
    ),
    "advanced_strength": frozenset(
        {
            "home_attack_rating",
            "home_defense_rating",
            "away_attack_rating",
            "away_defense_rating",
            "home_attack_home_rating",
            "home_defense_home_rating",
            "away_attack_away_rating",
            "away_defense_away_rating",
            "home_opponent_adjusted_strength",
            "away_opponent_adjusted_strength",
            "home_rolling_5_strength",
            "away_rolling_5_strength",
            "home_rolling_10_strength",
            "away_rolling_10_strength",
            "home_season_strength",
            "away_season_strength",
        }
    ),
    "xg": frozenset(
        {
            "home_xg_for_avg",
            "home_xg_against_avg",
            "away_xg_for_avg",
            "away_xg_against_avg",
            "home_xg_diff_avg",
            "away_xg_diff_avg",
            "home_xg_for_home",
            "home_xg_against_home",
            "away_xg_for_away",
            "away_xg_against_away",
            "home_rolling_xg_for_5",
            "home_rolling_xg_against_5",
            "home_rolling_xg_diff_5",
            "away_rolling_xg_for_5",
            "away_rolling_xg_against_5",
            "away_rolling_xg_diff_5",
            "home_goals_minus_xg",
            "away_goals_minus_xg",
            "home_goals_against_minus_xga",
            "away_goals_against_minus_xga",
        }
    ),
    "shots": frozenset(
        {
            "home_shots_for_avg",
            "home_shots_against_avg",
            "away_shots_for_avg",
            "away_shots_against_avg",
            "home_shots_on_target_for_avg",
            "home_shots_on_target_against_avg",
            "away_shots_on_target_for_avg",
            "away_shots_on_target_against_avg",
            "home_xg_per_shot",
            "away_xg_per_shot",
            "home_xga_per_shot_against",
            "away_xga_per_shot_against",
            "home_shot_conversion_rate",
            "away_shot_conversion_rate",
            "home_big_chances_for",
            "home_big_chances_against",
            "away_big_chances_for",
            "away_big_chances_against",
        }
    ),
    "strength_of_schedule": frozenset(
        {
            "home_avg_opponent_rating_last_5",
            "away_avg_opponent_rating_last_5",
            "home_avg_opponent_rating_last_10",
            "away_avg_opponent_rating_last_10",
            "home_points_vs_expected_last_5",
            "away_points_vs_expected_last_5",
            "home_xg_diff_vs_opponent_strength",
            "away_xg_diff_vs_opponent_strength",
        }
    ),
    "player_lineup": frozenset(
        {
            "home_starting_xi_attack_rating",
            "away_starting_xi_attack_rating",
            "home_starting_xi_defense_rating",
            "away_starting_xi_defense_rating",
            "home_starting_xi_midfield_rating",
            "away_starting_xi_midfield_rating",
            "home_goalkeeper_rating",
            "away_goalkeeper_rating",
            "home_missing_starters_count",
            "away_missing_starters_count",
            "home_missing_minutes_share",
            "away_missing_minutes_share",
            "home_missing_goals_share",
            "away_missing_goals_share",
            "home_missing_xg_share",
            "away_missing_xg_share",
            "home_bench_strength",
            "away_bench_strength",
            "home_lineup_continuity",
            "away_lineup_continuity",
        }
    ),
    "tactical": frozenset(
        {
            "home_formation_code",
            "away_formation_code",
            "formation_matchup_score",
            "wing_advantage",
            "midfield_advantage",
            "aerial_advantage",
            "pressing_mismatch",
            "defensive_line_risk",
        }
    ),
    "calendar": frozenset(
        {
            "days_rest_home",
            "days_rest_away",
            "rest_difference",
            "matches_last_7_days_home",
            "matches_last_7_days_away",
            "matches_last_14_days_home",
            "matches_last_14_days_away",
            "played_midweek_home",
            "played_midweek_away",
            "rotation_risk_home",
            "rotation_risk_away",
            "fatigue_score_home",
            "fatigue_score_away",
        }
    ),
    "motivation": frozenset(
        {
            "home_points_gap_to_top4",
            "away_points_gap_to_top4",
            "home_points_gap_to_relegation",
            "away_points_gap_to_relegation",
            "home_title_race_pressure",
            "away_title_race_pressure",
            "home_european_spot_pressure",
            "away_european_spot_pressure",
            "home_relegation_pressure",
            "away_relegation_pressure",
            "home_mid_table_low_motivation",
            "away_mid_table_low_motivation",
            "home_end_season_motivation_score",
            "away_end_season_motivation_score",
        }
    ),
}

ALL_GROUPS = frozenset(FEATURE_GROUPS.keys())

ABLATION_VARIANTS: dict[str, frozenset[str]] = {
    "base": frozenset({"base", "advanced_strength", "strength_of_schedule", "motivation"}),
    "base+xg": frozenset({"base", "advanced_strength", "strength_of_schedule", "motivation", "xg"}),
    "base+shots": frozenset(
        {"base", "advanced_strength", "strength_of_schedule", "motivation", "xg", "shots"}
    ),
    "base+player_lineup": frozenset(
        {
            "base",
            "advanced_strength",
            "strength_of_schedule",
            "motivation",
            "xg",
            "shots",
            "player_lineup",
        }
    ),
    "base+tactical": frozenset(
        {
            "base",
            "advanced_strength",
            "strength_of_schedule",
            "motivation",
            "xg",
            "shots",
            "player_lineup",
            "tactical",
        }
    ),
    "base+calendar": frozenset(
        {
            "base",
            "advanced_strength",
            "strength_of_schedule",
            "motivation",
            "xg",
            "shots",
            "player_lineup",
            "tactical",
            "calendar",
        }
    ),
    "full": ALL_GROUPS,
}


def keys_for_groups(groups: frozenset[str]) -> frozenset[str]:
    keys: set[str] = set()
    for group in groups:
        keys.update(FEATURE_GROUPS.get(group, ()))
    return frozenset(keys)


def filter_feature_vector(
    feature_vector: dict[str, float],
    enabled_groups: frozenset[str],
) -> dict[str, float]:
    allowed = keys_for_groups(enabled_groups)
    return {k: v for k, v in feature_vector.items() if k in allowed}
