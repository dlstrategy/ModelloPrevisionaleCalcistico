# 12 — Test e fixture offline

## Cosa è stato fatto

Suite di test automatici e dati mock per sviluppo senza API Sportmonks.

## Fixture

| File | Contenuto |
|------|-----------|
| `tests/fixtures/league_384_matches.json` | 10 partite Serie A (formato Sportmonks) |
| `tests/fixtures/league_384_xg.json` | xG per squadra |
| `tests/fixtures/league_384_lineups.json` | Lineup e metriche duelli |

Formato matches: risposta API `fixtures` con `data[]` annidato, usato da `normalize.py` e `load_offline_dataset()`.

## Test suite

| File test | Cosa verifica |
|-----------|---------------|
| `test_domain.py` | OutcomeProbabilities, normalizzazione |
| `test_poisson.py` | Modello Poisson, somma prob = 1 |
| `test_dixon_coles.py` | Correzione tau, probabilità valide |
| `test_elo.py` | Rating e predizioni |
| `test_ensemble.py` | Media pesata ensemble |
| `test_dataset.py` | finished_before, upcoming_on |
| `test_standings.py` | Classifica dinamica |
| `test_cache.py` | Cache SQLite hit/miss/TTL |
| `test_sync.py` | Sync offline carica fixture |
| `test_backtest.py` | Backtest end-to-end |
| `test_client.py` | Client API (skipped offline) |

## Esecuzione

```bash
python -m pytest -q
```

Risultato atteso: **15 passed, 1 skipped**.

## Test client skipped

`test_client.py` richiede token e `ENABLE_SPORTMONKS_SYNC=true`. In modalità offline viene skipped automaticamente — comportamento corretto.

## Cache test su Windows

`test_cache.py` usa database `:memory:` con connessione persistente per evitare errori di lock file su Windows.

## Collegamenti

```
tests/fixtures/*.json
        ↓
sync.load_offline_dataset()
        ↓
normalize → MatchDataset
        ↓
tutti i test di feature, modelli, backtest
```

## Aggiungere fixture

1. Copiare struttura JSON da risposta Sportmonks documentata
2. Salvare in `tests/fixtures/league_{id}_matches.json`
3. Eseguire `python -m src.cli sync --league {id}`

## Fase di sviluppo

Fase 1: test base
Fase 2: test modelli avanzati, fixture xG/lineup
