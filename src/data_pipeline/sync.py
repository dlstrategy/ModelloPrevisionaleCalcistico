"""Sincronizzazione dati — Fase 3: API Sportmonks (gated). Fase 2: fixture offline."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.config import CACHE_DB_PATH, FIXTURES_DIR, PROCESSED_DIR, Settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_pipeline.normalize import normalize_fixtures_response
from src.sportmonks.cache import ResponseCache
from src.sportmonks.client import SportmonksClient
from src.sportmonks import fixtures as fixtures_api
from src.sportmonks import leagues as leagues_api

logger = logging.getLogger(__name__)


def _offline_fixture_path(league_id: int) -> Path:
    return FIXTURES_DIR / f"league_{league_id}_matches.json"


def load_offline_dataset(league_id: int) -> MatchDataset:
    path = _offline_fixture_path(league_id)
    if not path.exists():
        raise FileNotFoundError(
            f"Fixture offline non trovata: {path}. "
            "Aggiungi dati in tests/fixtures/ oppure abilita Fase 3 (ENABLE_SPORTMONKS_SYNC=true)."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = normalize_fixtures_response(payload)
    season_id = matches[0].season_id if matches else None
    return MatchDataset(league_id=league_id, season_id=season_id, matches=matches)


def _resolve_season_id(client: SportmonksClient, league_id: int, ttl: int) -> int | None:
    response = leagues_api.fetch_league(client, league_id, ttl=ttl)
    data = response.get("data") or {}
    current = data.get("currentseason") or data.get("currentSeason")
    if isinstance(current, dict) and current.get("id"):
        return int(current["id"])
    return None


def _sync_from_api(settings: Settings, league_id: int) -> MatchDataset:
    """Fase 3 — richiede token + ENABLE_SPORTMONKS_SYNC=true."""
    cache = ResponseCache(CACHE_DB_PATH)
    client = SportmonksClient(settings, cache=cache)
    ttl = settings.cache_ttl_fixtures

    season_id = _resolve_season_id(client, league_id, settings.cache_ttl_standings)
    end = datetime.utcnow().date()
    start = end - timedelta(days=180)
    response = fixtures_api.fetch_fixtures_between(
        client,
        start.isoformat(),
        end.isoformat(),
        league_id=league_id,
        includes="participants;scores;state",
        ttl=ttl,
    )
    matches = normalize_fixtures_response(response)
    return MatchDataset(league_id=league_id, season_id=season_id, matches=matches)


def sync_league_data(settings: Settings, league_id: int) -> MatchDataset:
    processed_path = PROCESSED_DIR / f"league_{league_id}_dataset.json"

    if settings.can_sync_api:
        logger.info("Fase 3: sync API Sportmonks per lega %s", league_id)
        dataset = _sync_from_api(settings, league_id)
    else:
        logger.info("Fase 2 offline: caricamento fixture locali per lega %s", league_id)
        dataset = load_offline_dataset(league_id)

    dataset.save(processed_path)
    logger.info("Dataset salvato: %d partite -> %s", len(dataset.matches), processed_path)
    return dataset


def load_dataset(settings: Settings, league_id: int, *, refresh: bool = False) -> MatchDataset:
    processed_path = PROCESSED_DIR / f"league_{league_id}_dataset.json"
    if processed_path.exists() and not refresh:
        return MatchDataset.load(processed_path)
    return sync_league_data(settings, league_id)
