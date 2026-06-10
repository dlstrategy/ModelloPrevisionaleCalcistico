"""Forza attacco/difesa squadra."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import ParticipantLocation
from src.features.recent_form import compute_team_form


@dataclass(frozen=True)
class TeamStrength:
    team_id: int
    attack: float
    defense: float
    attack_home: float
    defense_home: float
    attack_away: float
    defense_away: float


def _season_rates(dataset: MatchDataset, team_id: int, as_of: datetime) -> tuple[float, float, float, float, float, float]:
    history = dataset.team_history(team_id, as_of)
    if not history:
        return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0

    gf = ga = gfh = gah = gfa = gaa = 0.0
    home_n = away_n = 0
    for match in history:
        scored, conceded = dataset.team_goals(team_id, match)
        gf += scored
        ga += conceded
        for participant in match.participants:
            if participant.team_id != team_id:
                continue
            if participant.location == ParticipantLocation.HOME:
                gfh += scored
                gah += conceded
                home_n += 1
            else:
                gfa += scored
                gaa += conceded
                away_n += 1

    n = len(history)
    return (
        gf / n,
        ga / n,
        gfh / max(home_n, 1),
        gah / max(home_n, 1),
        gfa / max(away_n, 1),
        gaa / max(away_n, 1),
    )


def compute_team_strengths(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    settings: Settings,
    league_avg_attack: float = 1.35,
    league_avg_defense: float = 1.35,
) -> TeamStrength:
    form = compute_team_form(dataset, team_id, as_of, settings)
    s_gf, s_ga, s_gfh, s_gah, s_gfa, s_gaa = _season_rates(dataset, team_id, as_of)

    attack = settings.form_weight * form.goals_for + settings.season_weight * s_gf
    defense = settings.form_weight * form.goals_against + settings.season_weight * s_ga
    attack_home = settings.form_weight * form.goals_for_home + settings.season_weight * s_gfh
    defense_home = settings.form_weight * form.goals_against_home + settings.season_weight * s_gah
    attack_away = settings.form_weight * form.goals_for_away + settings.season_weight * s_gfa
    defense_away = settings.form_weight * form.goals_against_away + settings.season_weight * s_gaa

    return TeamStrength(
        team_id=team_id,
        attack=max(attack / league_avg_attack, 0.05),
        defense=max(defense / league_avg_defense, 0.05),
        attack_home=max(attack_home / league_avg_attack, 0.05),
        defense_home=max(defense_home / league_avg_defense, 0.05),
        attack_away=max(attack_away / league_avg_attack, 0.05),
        defense_away=max(defense_away / league_avg_defense, 0.05),
    )
