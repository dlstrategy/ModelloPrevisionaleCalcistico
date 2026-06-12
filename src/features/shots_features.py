"""Shot profile mock — volume, qualità e conversione."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.config import FIXTURES_DIR
from src.data_pipeline.dataset_builder import MatchDataset
from src.domain.enums import ParticipantLocation


@dataclass(frozen=True)
class TeamShotsProfile:
    team_id: int
    shots_for_avg: float
    shots_against_avg: float
    shots_on_target_for_avg: float
    shots_on_target_against_avg: float
    xg_per_shot: float
    xga_per_shot_against: float
    shot_conversion_rate: float
    big_chances_for: float
    big_chances_against: float


def _shots_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_shots.json"


def _load_shots_payload(league_id: int) -> dict:
    path = _shots_fixture_path(league_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _match_shots_row(payload: dict, match_id: int) -> dict | None:
    history = payload.get("match_history", {})
    return history.get(str(match_id)) or history.get(match_id)


def get_team_shots_profile(
    dataset: MatchDataset,
    team_id: int,
    as_of: datetime,
    league_id: int,
) -> TeamShotsProfile:
    payload = _load_shots_payload(league_id)
    defaults = payload.get("teams", {}).get(str(team_id), {})
    history = dataset.team_history(team_id, as_of)

    sf: list[float] = []
    sa: list[float] = []
    sotf: list[float] = []
    sota: list[float] = []
    xgps: list[float] = []
    xgaps: list[float] = []
    conv: list[float] = []
    bcf: list[float] = []
    bca: list[float] = []

    for match in history:
        row = _match_shots_row(payload, match.id)
        if row is None:
            sf.append(float(defaults.get("shots_for", 12.0)))
            sa.append(float(defaults.get("shots_against", 12.0)))
            sotf.append(float(defaults.get("sot_for", 4.0)))
            sota.append(float(defaults.get("sot_against", 4.0)))
            continue
        for participant in match.participants:
            if participant.team_id != team_id:
                continue
            side = "home" if participant.location == ParticipantLocation.HOME else "away"
            shots = float(row.get(f"{side}_shots", defaults.get("shots_for", 12.0)))
            sot = float(row.get(f"{side}_sot", defaults.get("sot_for", 4.0)))
            xg = float(row.get(f"{side}_xg", 1.3))
            goals = float(row.get(f"{side}_goals", 0))
            opp = "away" if side == "home" else "home"
            opp_shots = float(row.get(f"{opp}_shots", defaults.get("shots_against", 12.0)))
            opp_sot = float(row.get(f"{opp}_sot", defaults.get("sot_against", 4.0)))
            opp_xg = float(row.get(f"{opp}_xg", 1.3))
            sf.append(shots)
            sa.append(opp_shots)
            sotf.append(sot)
            sota.append(opp_sot)
            xgps.append(xg / max(shots, 1.0))
            xgaps.append(opp_xg / max(opp_shots, 1.0))
            conv.append(goals / max(shots, 1.0))
            bcf.append(float(row.get(f"{side}_big_chances", defaults.get("big_chances_for", 2.0))))
            bca.append(float(row.get(f"{opp}_big_chances", defaults.get("big_chances_against", 2.0))))

    def avg(values: list[float], default: float) -> float:
        return sum(values) / len(values) if values else default

    shots_for = avg(sf, float(defaults.get("shots_for", 12.0)))
    shots_against = avg(sa, float(defaults.get("shots_against", 12.0)))

    return TeamShotsProfile(
        team_id=team_id,
        shots_for_avg=shots_for,
        shots_against_avg=shots_against,
        shots_on_target_for_avg=avg(sotf, float(defaults.get("sot_for", 4.0))),
        shots_on_target_against_avg=avg(sota, float(defaults.get("sot_against", 4.0))),
        xg_per_shot=avg(xgps, float(defaults.get("xg_per_shot", 0.11))),
        xga_per_shot_against=avg(xgaps, float(defaults.get("xga_per_shot", 0.11))),
        shot_conversion_rate=avg(conv, float(defaults.get("conversion_rate", 0.10))),
        big_chances_for=avg(bcf, float(defaults.get("big_chances_for", 2.0))),
        big_chances_against=avg(bca, float(defaults.get("big_chances_against", 2.0))),
    )


def shots_profile_to_features(prefix: str, profile: TeamShotsProfile) -> dict[str, float]:
    return {
        f"{prefix}_shots_for_avg": profile.shots_for_avg,
        f"{prefix}_shots_against_avg": profile.shots_against_avg,
        f"{prefix}_shots_on_target_for_avg": profile.shots_on_target_for_avg,
        f"{prefix}_shots_on_target_against_avg": profile.shots_on_target_against_avg,
        f"{prefix}_xg_per_shot": profile.xg_per_shot,
        f"{prefix}_xga_per_shot_against": profile.xga_per_shot_against,
        f"{prefix}_shot_conversion_rate": profile.shot_conversion_rate,
        f"{prefix}_big_chances_for": profile.big_chances_for,
        f"{prefix}_big_chances_against": profile.big_chances_against,
    }
