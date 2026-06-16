# 11 — Interfaccia CLI

**Entry point:** `python -m src.cli`

---

## Comandi

| Comando | Descrizione |
|---------|-------------|
| `sync` | Carica dataset (offline o API) |
| `status` | Stato dataset, companion e feature attive |
| `predict` | Predizioni per data |
| `backtest` | Valutazione modelli |
| `features` | Riepilogo feature engineering |
| `ablation` | Ablation test gruppi feature |
| `validate` | Data quality su dataset e fixture |
| `walk-forward` | Backtest walk-forward nel tempo |

---

### `sync`

```bash
python -m src.cli sync --league 384
```

Offline: legge `tests/fixtures/league_384_matches.json`  
API (Fase 3): passate 180gg + future 30gg

Salva in `data/processed/league_{id}_dataset.json`.

---

### `status`

```bash
python -m src.cli status --league 384
```

**File:** `src/cli_status.py`

Stampa:
- Modalità (offline / API Sportmonks)
- Lega default e richiesta
- Partite totali / finite / future
- Squadre distinte
- Fixture companion (xg, shots, lineups, tactical, calendar)
- Feature attive su partita futura di esempio

Se il dataset processato non esiste, esce con codice 1 e suggerisce `python -m src.cli sync --league {id}`.

**Test:** `tests/test_status.py`

---

### `predict`

```bash
python -m src.cli predict --date 2025-10-18 --model ensemble [--explain]
```

| Flag | Default |
|------|---------|
| `--date` | obbligatorio |
| `--model` | `ensemble` |
| `--league` | 384 |
| `--explain` | off — JSON explain per **ogni** partita predetta |

Output: `data/predictions/predictions_{date}.json`

---

### `backtest`

```bash
python -m src.cli backtest --league 384 [--model X | --all-models] [--rounds N]
```

Mostra accuracy, Brier, log-loss, Brier skill, mean calibration gap, pick over/underconfidence.

---

### `features`

```bash
python -m src.cli features --league 384
```

Mostra:
- Partita esempio (prima upcoming)
- Conteggio feature per gruppo
- Sample feature vector

---

### `ablation`

```bash
python -m src.cli ablation --league 384 --rounds 5
```

Tabella comparativa 8 varianti (con CalGap, PickOver, PickUnder) + report JSON.

---

### `validate`

```bash
python -m src.cli validate --league 384
```

Exit code 1 se errori, 0 se passed (anche con warning). Report in `data/quality/`.

---

### `walk-forward`

```bash
python -m src.cli walk-forward --league 384 --model ensemble
```

Parametri: `--min-train-matches`, `--test-window-size`, `--step-size`. Report in `data/backtests/walk_forward_*.json`.

---

## Modelli disponibili

`ensemble`, `poisson`, `dixon_coles`, `elo`, `feature`

---

## Fase di sviluppo

Fase 1 (sync, predict, backtest) → Fase 2c (features, ablation) → Fase 2d (status) → Fase 2e (validate, walk-forward)
