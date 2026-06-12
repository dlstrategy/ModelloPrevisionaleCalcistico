#!/usr/bin/env python3
"""Genera fixture offline estese per Serie A mock (10 squadre, 8+2 giornate)."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

TEAMS = {
    1: "Inter",
    2: "Genoa",
    3: "Milan",
    4: "Torino",
    5: "Juventus",
    6: "Napoli",
    7: "Roma",
    8: "Lazio",
    9: "Atalanta",
    10: "Fiorentina",
}

STRENGTH = {
    1: 1.85, 2: 0.95, 3: 1.75, 4: 1.05, 5: 1.70,
    6: 1.65, 7: 1.55, 8: 1.45, 9: 1.40, 10: 1.25,
}

FORMATIONS = ["4-3-3", "4-4-2", "3-5-2", "4-2-3-1", "3-4-3"]


def _pairings(round_num: int) -> list[tuple[int, int]]:
    ids = list(TEAMS.keys())
    random.seed(round_num * 42)
    random.shuffle(ids)
    return [(ids[i], ids[i + 1]) for i in range(0, 10, 2)]


def _simulate_score(home: int, away: int) -> tuple[int, int, float, float]:
    hs, aws = STRENGTH[home], STRENGTH[away]
    random.seed(home * 100 + away)
    hxg = max(0.3, random.gauss(hs * 1.1, 0.35))
    axg = max(0.3, random.gauss(aws * 0.95, 0.35))
    hg = max(0, int(round(hxg + random.uniform(-0.4, 0.4))))
    ag = max(0, int(round(axg + random.uniform(-0.4, 0.4))))
    return hg, ag, round(hxg, 2), round(axg, 2)


def generate_matches() -> dict:
    data = []
    match_id = 1001
    xg_history: dict = {}
    shots_history: dict = {}
    season_start = datetime(2025, 8, 23)

    for round_num in range(1, 11):
        round_date = season_start + timedelta(days=(round_num - 1) * 7)
        finished = round_num <= 8
        for idx, (home, away) in enumerate(_pairings(round_num)):
            kickoff = round_date.replace(hour=15 if idx % 2 else 20, minute=0 if idx % 2 == 0 else 45)
            starting = kickoff.strftime("%Y-%m-%d %H:%M:%S")
            scores = []
            hg = ag = hxg = axg = 0
            if finished:
                hg, ag, hxg, axg = _simulate_score(home, away)
                scores = [
                    {"description": "CURRENT", "score": {"participant": "home", "goals": hg}},
                    {"description": "CURRENT", "score": {"participant": "away", "goals": ag}},
                ]
            data.append({
                "id": match_id,
                "league_id": 384,
                "season_id": 25000,
                "round_id": round_num,
                "state_id": 5 if finished else 1,
                "starting_at": starting,
                "participants": [
                    {"id": home, "name": TEAMS[home], "meta": {"location": "home"}},
                    {"id": away, "name": TEAMS[away], "meta": {"location": "away"}},
                ],
                "scores": scores,
            })
            if finished:
                hs = max(6, int(hxg * 9 + random.uniform(0, 4)))
                aws = max(6, int(axg * 9 + random.uniform(0, 4)))
                xg_history[str(match_id)] = {
                    "home_xg": hxg, "away_xg": axg,
                    "home_xga": axg, "away_xga": hxg,
                    "home_goals": hg, "away_goals": ag,
                    "home_goals_against": ag, "away_goals_against": hg,
                }
                shots_history[str(match_id)] = {
                    "home_shots": hs, "away_shots": aws,
                    "home_sot": max(2, int(hs * 0.35)),
                    "away_sot": max(2, int(aws * 0.35)),
                    "home_xg": hxg, "away_xg": axg,
                    "home_goals": hg, "away_goals": ag,
                    "home_big_chances": max(1, int(hxg)),
                    "away_big_chances": max(1, int(axg)),
                }
            match_id += 1

    return {"data": data}, xg_history, shots_history


def generate_xg(xg_history: dict) -> dict:
    teams = {}
    for tid, strength in STRENGTH.items():
        teams[str(tid)] = {
            "xg_for": round(strength * 1.2, 2),
            "xg_against": round(2.2 - strength * 0.5, 2),
            "clean_sheet_rate": round(min(0.45, 0.15 + strength * 0.1), 2),
        }
    return {"teams": teams, "match_history": xg_history}


def generate_shots(shots_history: dict) -> dict:
    teams = {}
    for tid, strength in STRENGTH.items():
        teams[str(tid)] = {
            "shots_for": round(10 + strength * 4, 1),
            "shots_against": round(14 - strength * 2, 1),
            "sot_for": round(3.5 + strength * 1.5, 1),
            "sot_against": round(4.5 - strength * 0.5, 1),
            "xg_per_shot": round(0.08 + strength * 0.02, 3),
            "xga_per_shot": round(0.12 - strength * 0.01, 3),
            "conversion_rate": round(0.08 + strength * 0.015, 3),
            "big_chances_for": round(1.5 + strength, 1),
            "big_chances_against": round(2.5 - strength * 0.3, 1),
        }
    return {"teams": teams, "match_history": shots_history}


def generate_lineups(match_ids_future: list[int]) -> dict:
    fixtures = {}
    for fid in match_ids_future:
        random.seed(fid)
        h, a = _pairings(fid)[0]
        hf = random.choice(FORMATIONS)
        af = random.choice(FORMATIONS)
        fixtures[str(fid)] = {
            "home_offensive_quality": round(STRENGTH[h], 2),
            "home_defensive_quality": round(1.5 - STRENGTH[h] * 0.2, 2),
            "away_offensive_quality": round(STRENGTH[a], 2),
            "away_defensive_quality": round(1.5 - STRENGTH[a] * 0.2, 2),
            "home_absences": random.randint(0, 2),
            "away_absences": random.randint(0, 2),
            "home_formation": hf,
            "away_formation": af,
            "duel_edges": {
                "wing": round(random.uniform(-0.3, 0.3), 2),
                "midfield": round(random.uniform(-0.3, 0.3), 2),
                "aerial": round(random.uniform(-0.2, 0.2), 2),
                "pressing": round(random.uniform(-0.25, 0.25), 2),
                "defensive_line": round(random.uniform(0, 0.3), 2),
            },
            "home_player": {
                "starting_xi_attack_rating": round(STRENGTH[h], 2),
                "starting_xi_defense_rating": round(1.4 - STRENGTH[h] * 0.15, 2),
                "starting_xi_midfield_rating": round(STRENGTH[h] * 0.95, 2),
                "goalkeeper_rating": round(0.7 + random.uniform(0, 0.2), 2),
                "missing_starters_count": random.randint(0, 2),
                "missing_minutes_share": round(random.uniform(0, 0.15), 2),
                "missing_goals_share": round(random.uniform(0, 0.1), 2),
                "missing_xg_share": round(random.uniform(0, 0.12), 2),
                "bench_strength": round(0.55 + STRENGTH[h] * 0.08, 2),
                "lineup_continuity": round(random.uniform(0.65, 0.95), 2),
            },
            "away_player": {
                "starting_xi_attack_rating": round(STRENGTH[a], 2),
                "starting_xi_defense_rating": round(1.4 - STRENGTH[a] * 0.15, 2),
                "starting_xi_midfield_rating": round(STRENGTH[a] * 0.95, 2),
                "goalkeeper_rating": round(0.7 + random.uniform(0, 0.2), 2),
                "missing_starters_count": random.randint(0, 2),
                "missing_minutes_share": round(random.uniform(0, 0.15), 2),
                "missing_goals_share": round(random.uniform(0, 0.1), 2),
                "missing_xg_share": round(random.uniform(0, 0.12), 2),
                "bench_strength": round(0.55 + STRENGTH[a] * 0.08, 2),
                "lineup_continuity": round(random.uniform(0.65, 0.95), 2),
            },
        }
    return {"fixtures": fixtures}


def generate_tactical(future_ids: list[int]) -> dict:
    fixtures = {}
    for fid in future_ids:
        random.seed(fid + 7)
        fixtures[str(fid)] = {
            "home_formation": random.choice(FORMATIONS),
            "away_formation": random.choice(FORMATIONS),
            "wing_advantage": round(random.uniform(-0.35, 0.35), 2),
            "midfield_advantage": round(random.uniform(-0.35, 0.35), 2),
            "aerial_advantage": round(random.uniform(-0.2, 0.2), 2),
            "pressing_mismatch": round(random.uniform(-0.3, 0.3), 2),
            "defensive_line_risk": round(random.uniform(0, 0.35), 2),
        }
    return {"fixtures": fixtures}


def generate_calendar() -> dict:
    teams = {}
    for tid in TEAMS:
        random.seed(tid)
        teams[str(tid)] = {
            "played_midweek": round(random.choice([0.0, 0.0, 1.0]), 1),
            "rotation_risk": round(random.uniform(0.05, 0.35), 2),
        }
    return {"teams": teams}


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    matches, xg_hist, shots_hist = generate_matches()
    future_ids = [m["id"] for m in matches["data"] if not m["scores"]]

    (FIXTURES / "league_384_matches.json").write_text(
        json.dumps(matches, indent=2), encoding="utf-8"
    )
    (FIXTURES / "league_384_xg.json").write_text(
        json.dumps(generate_xg(xg_hist), indent=2), encoding="utf-8"
    )
    (FIXTURES / "league_384_shots.json").write_text(
        json.dumps(generate_shots(shots_hist), indent=2), encoding="utf-8"
    )
    (FIXTURES / "league_384_lineups.json").write_text(
        json.dumps(generate_lineups(future_ids), indent=2), encoding="utf-8"
    )
    (FIXTURES / "league_384_tactical.json").write_text(
        json.dumps(generate_tactical(future_ids), indent=2), encoding="utf-8"
    )
    (FIXTURES / "league_384_calendar.json").write_text(
        json.dumps(generate_calendar(), indent=2), encoding="utf-8"
    )
    finished = sum(1 for m in matches["data"] if m["scores"])
    print(f"Generated {len(matches['data'])} matches ({finished} finished, {len(future_ids)} future)")


if __name__ == "__main__":
    main()
