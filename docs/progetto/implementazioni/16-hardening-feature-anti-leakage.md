# 16 — Hardening feature, anti-leakage e status

## Obiettivo

Hardening mirato **prima di nuove feature**: CLI diagnostica, fixture lineup coerenti, gate pre-match, test anti-leakage, explain con tracciamento fonti dati, metriche calibrazione migliorate.

---

## 1. Comando CLI `status`

**File:** `src/cli_status.py` — registrato in `src/cli.py`

```bash
python -m src.cli status --league 384
```

Stampa:
- Modalità attiva (offline / API)
- Lega default e richiesta
- Partite totali / finite / future
- Squadre distinte
- Fixture companion (xg, shots, lineups, tactical, calendar)
- Feature attive su partita futura di esempio

Se manca `data/processed/league_{id}_dataset.json`, esce con errore leggibile e suggerisce `python -m src.cli sync --league {id}`.

**Test:** `tests/test_status.py`

---

## 2. Fix generatore fixture

**File:** `scripts/generate_fixtures.py`

- `generate_lineups()` e `generate_tactical()` usano `MatchRef(fixture_id, home_id, away_id, finished)` — **non** più `_pairings(fid)[0]`
- Rating offensive/defensive derivati da `STRENGTH[home_id]` / `STRENGTH[away_id]`
- Lineup/tactical generati per **tutte** le 50 partite

---

## 3. Convenzione pre-match vs post-match

**File:** `src/features/lineup_features.py`, `tactical_features.py`

| Valore `data_availability` | Uso |
|----------------------------|-----|
| `known_pre_match` | Partite **finite** — snapshot pre-kickoff valido in backtest |
| `forecast` | Partite **future** — proiezione valida in predict |
| altro / assente | Non usato → fallback default |

API pubblica:
- `resolve_lineup_for_match(league_id, match)` → `ResolvedLineup(lineup, player_lineup, source)`
- `resolve_tactical_for_match(league_id, match, lineup)` → `ResolvedTactical(tactical, source)`
- `is_pre_match_fixture_row_usable(row, match)` — gate generico pre-match (lineup, tactical, …)
- `is_pre_match_lineup_usable(row, match)` — wrapper retrocompatibile

`MatchContext` espone `lineup_source` e `tactical_source` (`mock_fixture` | `default_fallback`).

---

## 4. Tracciamento fonti dati (explain)

**File:** `src/features/data_sources.py`, `src/prediction/explain.py`

`build_data_sources(context, settings)` mappa ogni gruppo feature alla fonte effettiva:
- `historical` / `api_base` — storico partite (base, strength, motivation)
- `mock_fixture_historical` — xG/shots offline
- `api_not_connected_yet` — companion non ancora collegati in Fase 3
- `mock_fixture_not_api` — lineup/tactical mock con API sync attiva
- `default_fallback` — valori neutri

Explain JSON include:
- `data_sources` — per gruppo feature
- `warnings` — fallback lineup/tactical, confidenza bassa, assenze

---

## 5. Metriche migliorate

**File:** `src/backtesting/metrics.py`

| Metrica | Descrizione |
|---------|-------------|
| `pick_overconfidence_rate` | Frazione pick con confidence > hit binario (0/1) + margin |
| `pick_underconfidence_rate` | Frazione pick con confidence < hit binario - margin |
| `mean_calibration_gap` | Media pesata `\|avg_confidence - hit_rate\|` sui bin |
| `calibration_bins[].gap` | Gap per singolo bin |

Alias retrocompatibili: `overconfidence_rate`, `underconfidence_rate`.

CLI ablation/backtest mostra `CalGap`, `PickOver`, `PickUnder`.

**Test:** `tests/test_metrics.py`

---

## 6. Test anti-leakage

**File:** `tests/test_anti_leakage.py`

Verifica esplicitamente per match di backtest:
- Nessuna partita con `starting_at >= as_of` in storico form/xG/shots/SOS
- Il match corrente non contribuisce alle proprie feature
- Lineup/tactical solo se marcati pre-match
- Coerenza rating lineup ↔ squadre home/away reali in `league_384_lineups.json`

---

## Fase di sviluppo

**Fase 2d** — dopo Fase 2c, prima di Fase 3 e nuove feature.

**Test suite:** 53 passed.
