# 01 — Setup repository e configurazione

## Cosa è stato fatto

- Struttura progetto Python modulare sotto `src/`
- Repository GitHub: `dlstrategy/ModelloPrevisionaleCalcistico`
- File di configurazione: `.env.example`, `requirements.txt`, `pyproject.toml`
- Percorsi dati centralizzati in `src/config.py`

## File chiave

| File | Ruolo |
|------|-------|
| `src/config.py` | `Settings` da variabili ambiente |
| `src/logging_config.py` | Configurazione logger |
| `.env.example` | Template variabili |
| `requirements.txt` | Dipendenze Python |

## Percorsi definiti in config

```python
PROJECT_ROOT
DATA_DIR / raw | processed | predictions | backtests
CACHE_DB_PATH = data/cache.db
FIXTURES_DIR = tests/fixtures
SERIE_A_LEAGUE_ID = 384
```

## Logica `Settings`

La classe `Settings` è immutabile (`frozen=True`) e espone tre proprietà critiche:

1. **`is_offline`** — Determina se usare fixture locali
2. **`has_api_token`** — Token presente in `.env`
3. **`can_sync_api`** — Token + `ENABLE_SPORTMONKS_SYNC=true`

Questa triade governa tutto il comportamento sync/prediction senza if sparsi nel codice.

## Collegamenti

```
.env → load_settings() → Settings
                              ↓
        cli.py, sync.py, models/, features/
```

## Parametri principali

- **Modelli:** `poisson_max_goals`, `dixon_coles_rho`, `elo_*`, `ensemble_weight_*`
- **Feature:** `form_window_matches`, `home_advantage`
- **Calibrazione:** `calibration_temperature`, `min_confidence_threshold`
- **Cache TTL:** `cache_ttl_fixtures`, `cache_ttl_standings`, `cache_ttl_teams`

## Fase di sviluppo

Fase 0 — Setup iniziale (vedi [CRONOSTORIA.md](../CRONOSTORIA.md))
