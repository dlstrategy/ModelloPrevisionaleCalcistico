# 04 — Data pipeline

## Cosa è stato fatto

Pipeline che porta i dati grezzi (JSON fixture offline o risposta API) fino a un `MatchDataset` interrogabile con filtri temporali anti-leakage.

## Moduli

| Modulo | File | Funzione |
|--------|------|----------|
| Sync | `src/data_pipeline/sync.py` | Entry point caricamento dati |
| Normalize | `src/data_pipeline/normalize.py` | JSON → `Match` |
| Dataset builder | `src/data_pipeline/dataset_builder.py` | `MatchDataset` |
| Validators | `src/data_pipeline/validators.py` | Controlli integrità |

## Flusso sync

```
sync(league_id, settings)
    │
    ├─ is_offline / NOT can_sync_api
    │       → load_offline_dataset()
    │       → legge tests/fixtures/league_{id}_matches.json
    │
    └─ can_sync_api (Fase 3)
            → SportmonksClient + cache
            → resolve season_id da leagues API
            → fetch fixtures/between passate (today-180 → today)
            → fetch fixtures/between future (today → today+30)
            → _merge_matches() dedup per id
            → normalize_fixtures_response()
    │
    → salva data/processed/league_{id}_matches.json
    → ritorna MatchDataset
```

## Normalizzazione

`normalize_fixtures_response(payload)` estrae da ogni fixture Sportmonks:

- `id`, `starting_at`, `state`
- Partecipanti (home/away) con `team_id`, nome
- Score finale (`home_score`, `away_score`)
- `league_id`, `season_id`

**Datetime:** supporta formato Sportmonks (`YYYY-MM-DD HH:MM:SS`), ISO con timezone e solo data. Vedi Fase 2b in [15-hardening-foundation.md](15-hardening-foundation.md).

Output: lista di oggetti `Match` del dominio.

## MatchDataset

Classe centrale per query temporali:

| Metodo | Uso |
|--------|-----|
| `finished_before(as_of)` | Storico per feature/backtest |
| `upcoming_on(date)` | Partite da predire |
| `team_matches(team_id, before)` | Storico singola squadra |
| `all_matches` | Lista completa |

### Anti-leakage

`finished_before(as_of)` restituisce solo partite con `starting_at < as_of` e stato concluso. Usato da feature engineering e backtest.

## Output persistito

`data/processed/league_384_matches.json` — JSON normalizzato riutilizzabile senza ri-sync.

## Collegamenti

```
sync.py ──→ normalize.py ──→ MatchDataset
                                  ↓
                    features/match_context.py
                    models/elo.py (rating storico)
                    backtesting/backtest.py
```

## Fase di sviluppo

Fase 1 (base) — sync offline  
Fase 2b — sync API passate + future, normalize ISO  
Fase 3 — attivazione API live
