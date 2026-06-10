# 03 — Client Sportmonks e cache

## Cosa è stato fatto

Layer di accesso all'API Sportmonks Football v3 con caching SQLite, rate limiting e moduli per endpoint specifici. Predisposto per Fase 3; in Fase 2 non viene invocato se offline.

## Moduli

| Modulo | File | Stato |
|--------|------|-------|
| Client HTTP | `src/sportmonks/client.py` | Implementato |
| Cache SQLite | `src/sportmonks/cache.py` | Implementato |
| Endpoint constants | `src/sportmonks/endpoints.py` | Implementato |
| Leagues | `src/sportmonks/leagues.py` | Implementato |
| Fixtures | `src/sportmonks/fixtures.py` | Implementato |
| Teams | `src/sportmonks/teams.py` | Implementato |
| Standings | `src/sportmonks/standings.py` | Predisposto |
| Players | `src/sportmonks/players.py` | Scheletro |
| Lineups | `src/sportmonks/lineups.py` | Scheletro |
| Injuries | `src/sportmonks/injuries.py` | Scheletro |
| Statistics | `src/sportmonks/statistics.py` | Scheletro |

## Client (`SportmonksClient`)

Responsabilità:

- Costruisce URL da `settings.base_url` + path endpoint
- Aggiunge header `Authorization: {token}`
- Gestisce retry su errori transienti
- Interroga `ResponseCache` prima di ogni GET

## Cache (`ResponseCache`)

- Database: `data/cache.db`
- Chiave: URL + parametri query
- TTL configurabile per tipo dato (fixtures, standings, teams)
- Riduce chiamate API e rispetta rate limit

## Logica di gating

```python
# sync.py
if settings.can_sync_api:
    dataset = _sync_from_api(settings, league_id)
else:
    dataset = load_offline_dataset(league_id)
```

`can_sync_api` richiede **entrambi** token e flag `ENABLE_SPORTMONKS_SYNC=true`.

## Collegamenti

```
Settings → SportmonksClient → fixtures_api / leagues_api
                ↓
         ResponseCache (SQLite)
                ↓
         normalize.py → MatchDataset
```

## Endpoint usati in Fase 3

| Operazione | Endpoint documentato |
|------------|---------------------|
| Season corrente | `GET /leagues/{id}` + `currentSeason` |
| Partite periodo | `GET /fixtures/between/{start}/{end}` |

Altri endpoint (standings, xG, lineups) sono predisposti nei moduli scheletro.

## Test

- `tests/test_cache.py` — Cache in-memory (`:memory:`) per evitare lock Windows
- `tests/test_client.py` — Skipped quando `is_offline=True`

## Fase di sviluppo

Fase 1 (foundation) + estensioni Fase 2/3
