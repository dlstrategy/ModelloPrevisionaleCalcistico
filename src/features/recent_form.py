"""Forma recente squadra."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.config import Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import ParticipantLocation


@dataclass(frozen=True)
class TeamFormSnapshot:
    team_id: int
    matches_played: int
    goals_for: float
    goals_against: float
    goals_for_home: float
    goals_against_home: float
    goals_for_away: float
    goals_against_away: float


def compute_team_form(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    settings: Settings,
) -> TeamFormSnapshot:
    history = dataset.team_history(team_id, as_of)
    recent = history[-settings.form_window_matches :]

    gf = ga = gfh = gah = gfa = gaa = 0.0
    home_n = away_n = 0

    for match in recent:
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

    n = max(len(recent), 1)
    return TeamFormSnapshot(
        team_id=team_id,
        matches_played=len(recent),
        goals_for=gf / n,
        goals_against=ga / n,
        goals_for_home=gfh / max(home_n, 1),
        goals_against_home=gah / max(home_n, 1),
        goals_for_away=gfa / max(away_n, 1),
        goals_against_away=gaa / max(away_n, 1),
    )
