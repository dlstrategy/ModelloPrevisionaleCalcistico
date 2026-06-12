"""Controlli data quality su dataset, fixture companion e feature vector."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import FIXTURES_DIR, Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_quality.report import QualityIssue
from src.domain.enums import ParticipantLocation
from src.domain.match import Match, Score
from src.data_capabilities.capabilities import DataCapability
from src.data_capabilities.profiles import profile_capabilities
from src.data_capabilities.resolver import parse_data_profile
from src.features.lineup_features import FORECAST, KNOWN_PRE_MATCH
from src.features.match_context import build_match_context
from src.models.registry import get_model_by_name

FINISHED_STATE_IDS = {5, 6, 7, 8}
FUTURE_STATE_IDS = {1, 2, 3, 4}

COMPANION_FILES = {
    "xg": "league_{league_id}_xg.json",
    "shots": "league_{league_id}_shots.json",
    "lineups": "league_{league_id}_lineups.json",
    "tactical": "league_{league_id}_tactical.json",
    "calendar": "league_{league_id}_calendar.json",
}

PROB_SUM_TOLERANCE = 1e-4


class IssueCollector:
    def __init__(self) -> None:
        self.issues: list[QualityIssue] = []

    def add(
        self,
        severity: str,
        area: str,
        code: str,
        message: str,
        *,
        fixture_id: int | None = None,
    ) -> None:
        self.issues.append(
            QualityIssue(
                severity=severity,
                area=area,
                code=code,
                message=message,
                fixture_id=fixture_id,
            )
        )


def _is_bad_number(value: Any) -> bool:
    if not isinstance(value, (int, float)):
        return True
    return math.isnan(float(value)) or math.isinf(float(value))


def _check_numeric(
    collector: IssueCollector,
    area: str,
    code_prefix: str,
    value: Any,
    *,
    fixture_id: int | None,
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
    warn_max: float | None = None,
) -> None:
    if _is_bad_number(value):
        collector.add(
            "error",
            area,
            f"{code_prefix}_nan_inf",
            f"{label} non numerico o NaN/inf: {value!r}",
            fixture_id=fixture_id,
        )
        return
    number = float(value)
    if min_value is not None and number < min_value:
        collector.add(
            "error",
            area,
            f"{code_prefix}_below_min",
            f"{label}={number} < minimo {min_value}",
            fixture_id=fixture_id,
        )
    if max_value is not None and number > max_value:
        collector.add(
            "error",
            area,
            f"{code_prefix}_above_max",
            f"{label}={number} > massimo {max_value}",
            fixture_id=fixture_id,
        )
    if warn_max is not None and number > warn_max:
        collector.add(
            "warning",
            area,
            f"{code_prefix}_high",
            f"{label}={number} sopra soglia attesa {warn_max}",
            fixture_id=fixture_id,
        )


def _check_numeric_ideal_range(
    collector: IssueCollector,
    area: str,
    code_prefix: str,
    value: Any,
    *,
    fixture_id: int | None,
    label: str,
    ideal_min: float,
    ideal_max: float,
) -> None:
    """NaN/inf/non numerico = error; fuori range ideale = warning."""
    if _is_bad_number(value):
        collector.add(
            "error",
            area,
            f"{code_prefix}_nan_inf",
            f"{label} non numerico o NaN/inf: {value!r}",
            fixture_id=fixture_id,
        )
        return
    number = float(value)
    if number < ideal_min or number > ideal_max:
        collector.add(
            "warning",
            area,
            f"{code_prefix}_out_of_range",
            f"{label}={number} fuori range ideale [{ideal_min}, {ideal_max}]",
            fixture_id=fixture_id,
        )


def _check_tactical_numeric_fields(
    collector: IssueCollector,
    fixture_id: int,
    row: dict,
) -> None:
    """Validazione numerica campi tactical — error su NaN/inf, warning fuori range."""
    edge_fields = (
        "wing_advantage",
        "midfield_advantage",
        "aerial_advantage",
        "pressing_mismatch",
    )
    for field in edge_fields:
        _check_numeric_ideal_range(
            collector,
            "tactical",
            "tactical",
            row.get(field),
            fixture_id=fixture_id,
            label=field,
            ideal_min=-1.0,
            ideal_max=1.0,
        )
    _check_numeric_ideal_range(
        collector,
        "tactical",
        "tactical",
        row.get("defensive_line_risk"),
        fixture_id=fixture_id,
        label="defensive_line_risk",
        ideal_min=0.0,
        ideal_max=1.0,
    )


def _dataset_summary(dataset: MatchDataset) -> dict[str, int]:
    finished = [m for m in dataset.matches if m.is_finished]
    future = [m for m in dataset.matches if not m.is_finished]
    team_ids: set[int] = set()
    for match in dataset.matches:
        for participant in match.participants:
            team_ids.add(participant.team_id)
    return {
        "matches": len(dataset.matches),
        "finished": len(finished),
        "future": len(future),
        "teams": len(team_ids),
    }


def check_matches(dataset: MatchDataset, collector: IssueCollector) -> None:
    seen_ids: dict[int, int] = {}
    for match in dataset.matches:
        if match.id in seen_ids:
            collector.add(
                "error",
                "matches",
                "duplicate_fixture_id",
                f"Fixture id {match.id} duplicato",
                fixture_id=match.id,
            )
        seen_ids[match.id] = match.id

        if match.league_id != dataset.league_id:
            collector.add(
                "error",
                "matches",
                "league_id_mismatch",
                f"Match {match.id} league_id={match.league_id}, atteso {dataset.league_id}",
                fixture_id=match.id,
            )

        if not isinstance(match.starting_at, datetime):
            collector.add(
                "error",
                "matches",
                "invalid_starting_at",
                f"Match {match.id} starting_at mancante o non valido",
                fixture_id=match.id,
            )

        homes = [p for p in match.participants if p.location == ParticipantLocation.HOME]
        aways = [p for p in match.participants if p.location == ParticipantLocation.AWAY]

        if len(homes) == 0:
            collector.add(
                "error",
                "matches",
                "missing_home",
                f"Match {match.id} senza partecipante home",
                fixture_id=match.id,
            )
        elif len(homes) > 1:
            collector.add(
                "error",
                "matches",
                "multiple_home",
                f"Match {match.id} con più di una home",
                fixture_id=match.id,
            )

        if len(aways) == 0:
            collector.add(
                "error",
                "matches",
                "missing_away",
                f"Match {match.id} senza partecipante away",
                fixture_id=match.id,
            )
        elif len(aways) > 1:
            collector.add(
                "error",
                "matches",
                "multiple_away",
                f"Match {match.id} con più di una away",
                fixture_id=match.id,
            )

        for participant in match.participants:
            if not participant.team_id:
                collector.add(
                    "error",
                    "matches",
                    "missing_team_id",
                    f"Match {match.id} partecipante senza team_id",
                    fixture_id=match.id,
                )
            if not participant.team_name or not str(participant.team_name).strip():
                collector.add(
                    "error",
                    "matches",
                    "missing_team_name",
                    f"Match {match.id} partecipante senza team_name",
                    fixture_id=match.id,
                )

        state_id = match.state_id
        has_score = match.score is not None
        if state_id in FINISHED_STATE_IDS and not has_score:
            collector.add(
                "error",
                "scores",
                "finished_without_score",
                f"Match {match.id} finito (state_id={state_id}) senza risultato",
                fixture_id=match.id,
            )
        if state_id in FUTURE_STATE_IDS and has_score:
            collector.add(
                "error",
                "scores",
                "future_with_score",
                f"Match {match.id} futuro (state_id={state_id}) con score già presente",
                fixture_id=match.id,
            )
        if has_score and state_id in FUTURE_STATE_IDS:
            pass  # già coperto
        elif has_score and state_id in FINISHED_STATE_IDS:
            pass
        elif has_score and state_id not in FINISHED_STATE_IDS:
            collector.add(
                "warning",
                "matches",
                "state_score_mismatch",
                f"Match {match.id} con score ma state_id={state_id} non tipico di finito",
                fixture_id=match.id,
            )
        elif not has_score and state_id in FINISHED_STATE_IDS:
            pass  # già error scores
        elif not has_score and state_id not in FUTURE_STATE_IDS and state_id is not None:
            collector.add(
                "warning",
                "matches",
                "state_id_unusual",
                f"Match {match.id} state_id={state_id} non classificato come futuro/finito",
                fixture_id=match.id,
            )

        check_scores(match, collector)


def check_scores(match: Match, collector: IssueCollector) -> None:
    if match.score is None:
        return
    score = match.score
    for label, value in (("home", score.home), ("away", score.away)):
        if not isinstance(value, int):
            collector.add(
                "error",
                "scores",
                "score_not_numeric",
                f"Match {match.id} goal {label} non numerico: {value!r}",
                fixture_id=match.id,
            )
        elif value < 0:
            collector.add(
                "error",
                "scores",
                "negative_score",
                f"Match {match.id} goal {label} negativo: {value}",
                fixture_id=match.id,
            )


def _load_companion(path: Path, area: str, collector: IssueCollector) -> dict | None:
    if not path.exists():
        collector.add(
            "warning",
            area,
            "companion_missing",
            f"File companion mancante: {path.name}",
        )
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        collector.add(
            "error",
            area,
            "companion_invalid_json",
            f"JSON non valido in {path.name}: {exc}",
        )
        return None


def _match_lookup(dataset: MatchDataset) -> dict[int, Match]:
    return {match.id: match for match in dataset.matches}


def check_xg_companion(
    dataset: MatchDataset,
    league_id: int,
    collector: IssueCollector,
) -> None:
    path = FIXTURES_DIR / COMPANION_FILES["xg"].format(league_id=league_id)
    payload = _load_companion(path, "xg", collector)
    if payload is None:
        return

    match_ids = set(_match_lookup(dataset))
    for fixture_id_str in payload.get("match_history", {}):
        fid = int(fixture_id_str)
        if fid not in match_ids:
            collector.add(
                "warning",
                "xg",
                "orphan_fixture",
                f"xG match_history contiene fixture {fid} assente nel dataset",
                fixture_id=fid,
            )

    for team_id, row in payload.get("teams", {}).items():
        if not isinstance(row, dict):
            continue
        _check_numeric(collector, "xg", "xg", row.get("xg_for"), fixture_id=None, label=f"team {team_id} xg_for", min_value=0.0)
        _check_numeric(collector, "xg", "xg", row.get("xg_against"), fixture_id=None, label=f"team {team_id} xg_against", min_value=0.0)

    for fixture_id_str, row in payload.get("match_history", {}).items():
        if not isinstance(row, dict):
            continue
        fid = int(fixture_id_str)
        for key in ("home_xg", "away_xg", "home_xga", "away_xga"):
            _check_numeric(collector, "xg", "xg", row.get(key), fixture_id=fid, label=key, min_value=0.0)


def check_shots_companion(
    dataset: MatchDataset,
    league_id: int,
    collector: IssueCollector,
) -> None:
    path = FIXTURES_DIR / COMPANION_FILES["shots"].format(league_id=league_id)
    payload = _load_companion(path, "shots", collector)
    if payload is None:
        return

    match_ids = set(_match_lookup(dataset))
    for fixture_id_str in payload.get("match_history", {}):
        fid = int(fixture_id_str)
        if fid not in match_ids:
            collector.add(
                "warning",
                "shots",
                "orphan_fixture",
                f"Shots match_history contiene fixture {fid} assente nel dataset",
                fixture_id=fid,
            )

    for team_id, row in payload.get("teams", {}).items():
        if not isinstance(row, dict):
            continue
        _check_numeric(collector, "shots", "shots", row.get("shots_for"), fixture_id=None, label=f"team {team_id} shots_for", min_value=0.0)
        _check_numeric(collector, "shots", "shots", row.get("shots_against"), fixture_id=None, label=f"team {team_id} shots_against", min_value=0.0)
        _check_numeric(collector, "shots", "shots", row.get("xg_per_shot"), fixture_id=None, label=f"team {team_id} xg_per_shot", min_value=0.0, max_value=1.0)
        _check_numeric(collector, "shots", "shots", row.get("conversion_rate"), fixture_id=None, label=f"team {team_id} conversion_rate", min_value=0.0, max_value=1.0)

    for fixture_id_str, row in payload.get("match_history", {}).items():
        if not isinstance(row, dict):
            continue
        fid = int(fixture_id_str)
        for key in ("home_shots", "away_shots", "home_sot", "away_sot"):
            _check_numeric(collector, "shots", "shots", row.get(key), fixture_id=fid, label=key, min_value=0.0)


def _check_lineup_tactical_row(
    dataset: MatchDataset,
    area: str,
    fixture_id: int,
    row: dict,
    collector: IssueCollector,
) -> None:
    matches = _match_lookup(dataset)
    match = matches.get(fixture_id)
    if match is None:
        collector.add(
            "warning",
            area,
            "orphan_fixture",
            f"{area} contiene fixture {fixture_id} assente nel dataset",
            fixture_id=fixture_id,
        )
        return

    home_id = row.get("home_id")
    away_id = row.get("away_id")
    if home_id is not None and int(home_id) != match.home.team_id:
        collector.add(
            "error",
            area,
            "home_id_mismatch",
            f"Fixture {fixture_id} home_id={home_id}, atteso {match.home.team_id}",
            fixture_id=fixture_id,
        )
    if away_id is not None and int(away_id) != match.away.team_id:
        collector.add(
            "error",
            area,
            "away_id_mismatch",
            f"Fixture {fixture_id} away_id={away_id}, atteso {match.away.team_id}",
            fixture_id=fixture_id,
        )

    availability = row.get("data_availability")
    if not availability:
        collector.add(
            "warning",
            area,
            "missing_data_availability",
            f"Fixture {fixture_id} senza data_availability",
            fixture_id=fixture_id,
        )
    elif match.is_finished and availability == FORECAST:
        collector.add(
            "error",
            area,
            "finished_with_forecast",
            f"Match finito {fixture_id} con data_availability=forecast",
            fixture_id=fixture_id,
        )
    elif not match.is_finished and availability == KNOWN_PRE_MATCH:
        collector.add(
            "error",
            area,
            "future_with_known_pre_match",
            f"Match futuro {fixture_id} con data_availability=known_pre_match",
            fixture_id=fixture_id,
        )

    if area == "lineups":
        for side in ("home_player", "away_player"):
            block = row.get(side, {})
            if not isinstance(block, dict):
                continue
            _check_numeric(
                collector,
                "lineups",
                "lineup",
                block.get("missing_minutes_share"),
                fixture_id=fixture_id,
                label=f"{side}.missing_minutes_share",
                min_value=0.0,
                max_value=1.0,
            )
            _check_numeric(
                collector,
                "lineups",
                "lineup",
                block.get("missing_goals_share"),
                fixture_id=fixture_id,
                label=f"{side}.missing_goals_share",
                min_value=0.0,
                max_value=1.0,
            )
            _check_numeric(
                collector,
                "lineups",
                "lineup",
                block.get("missing_xg_share"),
                fixture_id=fixture_id,
                label=f"{side}.missing_xg_share",
                min_value=0.0,
                max_value=1.0,
            )
            _check_numeric(
                collector,
                "lineups",
                "lineup",
                block.get("lineup_continuity"),
                fixture_id=fixture_id,
                label=f"{side}.lineup_continuity",
                min_value=0.0,
                max_value=1.0,
            )
            _check_numeric(
                collector,
                "lineups",
                "lineup",
                block.get("bench_strength"),
                fixture_id=fixture_id,
                label=f"{side}.bench_strength",
                min_value=0.0,
            )

    if area == "tactical":
        _check_tactical_numeric_fields(collector, fixture_id, row)


def check_lineups_companion(
    dataset: MatchDataset,
    league_id: int,
    collector: IssueCollector,
) -> None:
    path = FIXTURES_DIR / COMPANION_FILES["lineups"].format(league_id=league_id)
    payload = _load_companion(path, "lineups", collector)
    if payload is None:
        return
    for fixture_id_str, row in payload.get("fixtures", {}).items():
        if isinstance(row, dict):
            _check_lineup_tactical_row(dataset, "lineups", int(fixture_id_str), row, collector)


def check_tactical_companion(
    dataset: MatchDataset,
    league_id: int,
    collector: IssueCollector,
) -> None:
    path = FIXTURES_DIR / COMPANION_FILES["tactical"].format(league_id=league_id)
    payload = _load_companion(path, "tactical", collector)
    if payload is None:
        return
    for fixture_id_str, row in payload.get("fixtures", {}).items():
        if isinstance(row, dict):
            _check_lineup_tactical_row(dataset, "tactical", int(fixture_id_str), row, collector)


def check_calendar_companion(
    dataset: MatchDataset,
    league_id: int,
    collector: IssueCollector,
) -> None:
    path = FIXTURES_DIR / COMPANION_FILES["calendar"].format(league_id=league_id)
    payload = _load_companion(path, "calendar", collector)
    if payload is None:
        return
    team_ids = {str(p.team_id) for m in dataset.matches for p in m.participants}
    for team_id, row in payload.get("teams", {}).items():
        if team_id not in team_ids:
            collector.add(
                "warning",
                "calendar",
                "orphan_team",
                f"Calendar contiene team {team_id} assente nel dataset",
            )
        if isinstance(row, dict):
            _check_numeric(
                collector,
                "calendar",
                "calendar",
                row.get("rotation_risk"),
                fixture_id=None,
                label=f"team {team_id} rotation_risk",
                min_value=0.0,
                max_value=1.0,
            )


def check_features(
    dataset: MatchDataset,
    settings: Settings,
    collector: IssueCollector,
) -> None:
    samples = []
    finished = next((m for m in dataset.matches if m.is_finished), None)
    future = next((m for m in dataset.matches if not m.is_finished), None)
    if finished:
        samples.append(finished)
    if future:
        samples.append(future)
    if not samples:
        collector.add("error", "features", "no_sample_match", "Nessuna partita campione disponibile")
        return

    model = get_model_by_name("ensemble", settings, dataset)
    for match in samples:
        ctx = build_match_context(dataset, match, settings, as_of=match.starting_at)
        if not ctx.feature_vector:
            collector.add(
                "error",
                "features",
                "empty_feature_vector",
                f"Feature vector vuoto per match {match.id}",
                fixture_id=match.id,
            )
        for key, value in ctx.feature_vector.items():
            if _is_bad_number(value):
                collector.add(
                    "error",
                    "features",
                    "feature_nan_inf",
                    f"Feature {key}={value!r} NaN/inf per match {match.id}",
                    fixture_id=match.id,
                )

        probs = model.predict(ctx)
        total = probs.home + probs.draw + probs.away
        if abs(total - 1.0) > PROB_SUM_TOLERANCE:
            collector.add(
                "error",
                "features",
                "prob_not_normalized",
                f"Probabilità somma {total:.6f} != 1.0 per match {match.id}",
                fixture_id=match.id,
            )
        for label, value in (("home", probs.home), ("draw", probs.draw), ("away", probs.away)):
            if value < 0:
                collector.add(
                    "error",
                    "features",
                    "negative_probability",
                    f"P({label})={value} negativa per match {match.id}",
                    fixture_id=match.id,
                )


def run_all_checks(
    dataset: MatchDataset,
    settings: Settings,
    league_id: int,
    *,
    profile: str | None = None,
) -> tuple[list[QualityIssue], dict[str, int]]:
    profile_name = parse_data_profile(profile or settings.data_profile)
    profile_caps = profile_capabilities(profile_name)

    collector = IssueCollector()
    check_matches(dataset, collector)
    if DataCapability.XG in profile_caps:
        check_xg_companion(dataset, league_id, collector)
    if DataCapability.SHOTS in profile_caps:
        check_shots_companion(dataset, league_id, collector)
    if DataCapability.LINEUPS_CONFIRMED in profile_caps:
        check_lineups_companion(dataset, league_id, collector)
    if DataCapability.TACTICAL_DATA in profile_caps:
        check_tactical_companion(dataset, league_id, collector)
    if DataCapability.CALENDAR in profile_caps:
        check_calendar_companion(dataset, league_id, collector)
    check_features(dataset, settings, collector)
    return collector.issues, _dataset_summary(dataset)


# Helpers per test — mutazioni dataset
def copy_match(match: Match, **kwargs: Any) -> Match:
    return replace(match, **kwargs)


def copy_dataset(dataset: MatchDataset, matches: list[Match] | None = None) -> MatchDataset:
    return MatchDataset(
        league_id=dataset.league_id,
        season_id=dataset.season_id,
        matches=list(matches if matches is not None else dataset.matches),
    )
