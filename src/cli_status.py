"""Comando status — riepilogo stato dataset e feature."""

from __future__ import annotations

import sys
from pathlib import Path

from src.config import FIXTURES_DIR, PROCESSED_DIR, Settings
from src.data_pipeline.sync import load_dataset
from src.features.data_sources import companion_fixture_status
from src.features.match_context import build_match_context


def _distinct_teams(matches) -> int:
    team_ids: set[int] = set()
    for match in matches:
        for participant in match.participants:
            team_ids.add(participant.team_id)
    return len(team_ids)


def print_status(settings: Settings, league_id: int) -> int:
    processed_path = PROCESSED_DIR / f"league_{league_id}_dataset.json"
    offline_matches = FIXTURES_DIR / f"league_{league_id}_matches.json"

    if settings.can_sync_api:
        mode = "API Sportmonks"
    elif settings.is_offline:
        mode = "offline"
    else:
        mode = "offline"

    if not processed_path.exists():
        print(f"Dataset processato non trovato: {processed_path}", file=sys.stderr)
        print(
            f"Esegui: python -m src.cli sync --league {league_id}",
            file=sys.stderr,
        )
        if offline_matches.exists():
            print(f"(Fixture offline disponibile: {offline_matches})", file=sys.stderr)
        return 1

    try:
        dataset = load_dataset(settings, league_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print(
            f"Esegui: python -m src.cli sync --league {league_id}",
            file=sys.stderr,
        )
        return 1

    finished = [m for m in dataset.matches if m.is_finished]
    future = [m for m in dataset.matches if not m.is_finished]
    companions = companion_fixture_status(league_id)

    sample = next((m for m in dataset.matches if not m.is_finished), None)
    feature_count = 0
    sample_label = "n/d"
    if sample:
        ctx = build_match_context(dataset, sample, settings)
        feature_count = len(ctx.feature_vector)
        sample_label = (
            f"{sample.home.team_name} vs {sample.away.team_name} (id={sample.id})"
        )

    print(f"Modalità:           {mode}")
    print(f"Lega default:       {settings.default_league_id}")
    print(f"Lega richiesta:     {league_id}")
    print(f"Dataset processato: {processed_path}")
    print(f"Partite totali:     {len(dataset.matches)}")
    print(f"Partite finite:     {len(finished)}")
    print(f"Partite future:     {len(future)}")
    print(f"Squadre distinte:   {_distinct_teams(dataset.matches)}")
    print("Fixture companion:")
    for name, available in companions.items():
        status = "OK" if available else "mancante"
        path = FIXTURES_DIR / f"league_{league_id}_{name}.json"
        print(f"  {name:<10} {status:<8} {path.name}")
    print(f"Feature attive (esempio futuro): {feature_count}")
    if sample:
        print(f"  Partita esempio: {sample_label}")
    return 0
