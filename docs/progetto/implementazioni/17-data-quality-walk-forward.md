# 17 — Data quality e walk-forward (Fase 2e)

## Obiettivo

Solidificare il motore prima della Fase 3 Sportmonks: controlli automatici su dataset/fixture, CLI `validate` e backtest walk-forward realistico.

---

## Moduli

| Modulo | Ruolo |
|--------|-------|
| `src/data_quality/checks.py` | Controlli su match, score, companion, feature |
| `src/data_quality/report.py` | `QualityIssue`, `QualityReport`, JSON/CSV |
| `src/cli_validate.py` | Output console comando `validate` |
| `src/backtesting/walk_forward.py` | Backtest temporale a finestre |

---

## Data quality layer

### Aree controllate

| Area | Controlli principali |
|------|---------------------|
| `matches` | Duplicati, home/away, starting_at, league_id, state_id |
| `scores` | Finito senza score, futuro con score, goal negativi |
| `xg` / `shots` | JSON valido, orphan fixture, range numerici |
| `lineups` / `tactical` | home/away id, data_availability, NaN/inf |
| `calendar` | Team orphan, rotation_risk |
| `features` | Vector non vuoto, no NaN/inf, probabilità normalizzate |

### Regole severity

- File companion **mancante** → `warning`
- JSON **non valido** → `error`
- Lineup home/away **sbagliato** → `error`
- Match finito con `forecast` → `error`
- Match futuro con `known_pre_match` → `error`

`passed = True` solo se `errors == 0`. Solo warning → exit code 0.

### Output

```
data/quality/quality_{league_id}_latest.json
data/quality/quality_{league_id}_latest.csv
```

---

## CLI validate

```bash
python -m src.cli validate --league 384
```

Exit code `1` se errori, `0` se passed ( anche con warning ).

---

## Walk-forward backtest

Simula uso reale: per ogni finestra usa storico `min_train_matches` e testa `test_window_size` partite successive, avanzando di `step_size`.

Default: train=10, window=5, step=5 → 6 finestre, 30 partite testate (su 40 finite mock).

Ogni prediction usa `as_of = match.starting_at`. I modelli non vengono ri-addestrati (struttura pronta per modelli trainabili futuri).

### Output

```
data/backtests/walk_forward_{model}_{league_id}.json
data/backtests/walk_forward_{model}_{league_id}.csv
```

CSV colonne: `window_index`, `fixture_id`, `starting_at`, `home_team`, `away_team`, `p_home`, `p_draw`, `p_away`, `pick`, `confidence`, `actual`, `correct`.

---

## CLI walk-forward

```bash
python -m src.cli walk-forward --league 384 --model ensemble
python -m src.cli walk-forward --league 384 --model poisson --min-train-matches 10 --test-window-size 5 --step-size 5
```

---

## Test

| File | Copertura |
|------|-----------|
| `tests/test_data_quality.py` | Controlli, errori/warning, report |
| `tests/test_validate_cli.py` | CLI validate, JSON/CSV |
| `tests/test_walk_forward.py` | Finestre, anti-leakage, report |

**Suite totale:** 74 passed.

---

## Fase di sviluppo

Fase 2e — dopo 2d, prima di Fase 3 API live.
