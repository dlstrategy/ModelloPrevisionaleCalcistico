"""Motivazione e contesto classifica (top4, retrocessione, fine stagione)."""

from __future__ import annotations

from dataclasses import dataclass

from src.features.standings_features import TeamStandingsSnapshot


@dataclass(frozen=True)
class MotivationSnapshot:
    team_id: int
    points_gap_to_top4: float
    points_gap_to_relegation: float
    title_race_pressure: float
    european_spot_pressure: float
    relegation_pressure: float
    mid_table_low_motivation: float
    end_season_motivation_score: float


def compute_motivation(
    standings: TeamStandingsSnapshot,
    *,
    total_teams: int = 20,
    top4_cutoff: int = 4,
    relegation_cutoff: int = 18,
    rounds_remaining: int = 20,
) -> MotivationSnapshot:
    pos = standings.position
    pts = standings.points

    # Stime mock: 4° posto ~2.1 pt/partita, zona retro ~0.9 pt/partita
    top4_target = max(0, (top4_cutoff - 1) * 2.1 * (38 - rounds_remaining) / 38 * 38)
    rel_target = max(0, (relegation_cutoff - 1) * 0.9 * 30)

    gap_top4 = top4_target - pts if pos > top4_cutoff else max(0.0, 3 - (top4_cutoff - pos))
    gap_relegation = pts - rel_target if pos >= relegation_cutoff else max(0.0, relegation_cutoff - pos)

    title_pressure = max(0.0, 1.0 - (pos - 1) / 5.0) if pos <= 5 else 0.0
    european_pressure = max(0.0, 1.0 - abs(pos - 6) / 4.0) if 4 <= pos <= 10 else 0.0
    relegation_pressure = max(0.0, 1.0 - (relegation_cutoff - pos) / 4.0) if pos >= relegation_cutoff - 3 else 0.0
    mid_table = 1.0 if 8 <= pos <= 14 else 0.0

    end_season = (
        title_pressure * 0.35
        + european_pressure * 0.25
        + relegation_pressure * 0.35
        - mid_table * 0.15
    )
    end_season = max(0.0, min(1.0, end_season + 0.3))

    return MotivationSnapshot(
        team_id=standings.team_id,
        points_gap_to_top4=gap_top4,
        points_gap_to_relegation=gap_relegation,
        title_race_pressure=title_pressure,
        european_spot_pressure=european_pressure,
        relegation_pressure=relegation_pressure,
        mid_table_low_motivation=mid_table,
        end_season_motivation_score=end_season,
    )


def motivation_to_features(prefix: str, snap: MotivationSnapshot) -> dict[str, float]:
    return {
        f"{prefix}_points_gap_to_top4": snap.points_gap_to_top4,
        f"{prefix}_points_gap_to_relegation": snap.points_gap_to_relegation,
        f"{prefix}_title_race_pressure": snap.title_race_pressure,
        f"{prefix}_european_spot_pressure": snap.european_spot_pressure,
        f"{prefix}_relegation_pressure": snap.relegation_pressure,
        f"{prefix}_mid_table_low_motivation": snap.mid_table_low_motivation,
        f"{prefix}_end_season_motivation_score": snap.end_season_motivation_score,
    }
