# 13 — Fase 3: collegamento API Sportmonks

## Stato

**Predisposto ma non attivato.** Tutto il codice esiste; la sync usa fixture offline finché non si abilita esplicitamente l'API.

## Prerequisiti

1. Account Sportmonks con subscription Football API v3
2. Token API valido
3. Variabili in `.env`:

```env
SPORTMONKS_API_TOKEN=il_tuo_token
ENABLE_SPORTMONKS_SYNC=true
OFFLINE_MODE=auto
```

## Cosa cambia all'attivazione

### `sync.py`

Branch `_sync_from_api()`:

1. Crea `SportmonksClient` + `ResponseCache`
2. `leagues_api.fetch_league(384)` → `currentSeason.id`
3. `fixtures_api.fetch_fixtures_between(start, end, league_id=384)`
4. `normalize_fixtures_response()` → `MatchDataset`
5. Salva in `data/processed/`

Finestra default: ultimi **180 giorni** fino a oggi.

### Cache

Prima chiamata → API. Chiamate successive entro TTL → SQLite `data/cache.db`.

### Feature da API (da completare)

| Feature | Modulo | Endpoint previsto |
|---------|--------|-------------------|
| Standings ufficiali | `standings.py` | `/standings/seasons/{id}` |
| xG partita | `xg_features.py` | Statistics fixture |
| Lineup | `lineup_features.py` | `/fixtures/{id}` + include lineups |
| Infortuni | `injuries.py` | Endpoint injuries documentato |
| Giocatori | `player_features.py` | `/players/{id}` + statistics |
| Coach | `coach_registry.py` | `/coaches/{id}` + `statistics.details`; fixture `include=coaches`; filtri `coachStatisticSeasons` |

Moduli scheletro vanno completati seguendo `docs/sportmonks-football-v3-docs.md` (sezione Coaches, Coach statistics).

## Coach — mapping Sportmonks (prep Fase 2l-b)

**Stato:** documentato, non attivato. Dettaglio completo: [28-sportmonks-coach-mapping-prep.md](28-sportmonks-coach-mapping-prep.md).

### Endpoint e include

- Coaches: all, by id, by country, search, last updated
- `include=coaches` su fixture e team
- `include=statistics.details` su coach (MATCHES, WIN/DRAW/LOST, AVERAGE_POINTS_PER_GAME, SUBSTITUTIONS)
- `include=teams`, `include=latest` per storico e tenure

### Campi CoachProfile

| Tipo | Esempi |
|------|--------|
| **Diretti** | `coach_id`, `coach_name`, country |
| **Derivati** | `matches_in_charge`, PPG, prior league, `data_confidence` |
| **Non nativi** | xG/style deltas, formation changes, `appointed_at` esatto |

### Anti-leakage

- Tutti i calcoli coach **as_of `match.starting_at`**
- PPG/deltas/tenure solo su partite precedenti alla predizione
- Nessuna statistica future del coach o della squadra

### Moduli interni (invariati in Fase 3)

`coach_registry.py` → popola `CoachProfile`; `coach_adaptation.py` e `coach_features.py` restano la logica di feature/summary.

## Cosa NON cambia

- Output: solo P(1), P(X), P(2)
- Pipeline: normalize → features → modelli → prediction
- Nessun uso add-on Predictions Sportmonks
- Auth: solo header `Authorization`

## Verifica attivazione

```bash
python -m src.cli sync --league 384
```

Log atteso (Fase 3):

```
Sync API Sportmonks league_id=384 ...
```

Log offline (Fase 2):

```
Caricamento fixture offline ...
```

## Test API

Con token attivo, `test_client.py` non viene più skipped:

```bash
python -m pytest tests/test_client.py -v
```

## Checklist implementazione Fase 3

- [ ] Token e flag in `.env`
- [ ] Sync produzione dati reali in `data/processed/`
- [ ] Completare `standings.py` per classifica ufficiale
- [ ] Collegare `xg_features.py` a statistics API
- [ ] Collegare `lineup_features.py` a lineups API
- [ ] Collegare `coach_registry.py` a coaches API + statistiche (MATCHES, WIN/DRAW/LOST, AVERAGE_POINTS_PER_GAME, SUBSTITUTIONS)
- [ ] Valutare `injuries.py` e `player_features.py`
- [ ] Backtest su stagione completa
- [ ] Calibrare pesi ensemble e temperature

## Collegamenti

```
.env (token + flag)
    ↓
config.can_sync_api = True
    ↓
sync._sync_from_api()
    ↓
sportmonks/client + cache + fixtures + leagues
    ↓
normalize → MatchDataset (stesso path offline)
    ↓
features + models (invariati)
```

## Fase di sviluppo

Fase 3 — milestone futura M5 (vedi [CRONOSTORIA.md](../CRONOSTORIA.md))
