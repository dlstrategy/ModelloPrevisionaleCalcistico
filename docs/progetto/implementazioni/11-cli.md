# 11 — Interfaccia CLI

**Entry point:** `python -m src.cli`

---

## Comandi

| Comando | Descrizione |
|---------|-------------|
| `sync` | Carica dataset (offline o API) |
| `predict` | Predizioni per data |
| `backtest` | Valutazione modelli |
| `features` | Riepilogo feature engineering |
| `ablation` | Ablation test gruppi feature |

---

### `sync`

```bash
python -m src.cli sync --league 384
```

Offline: legge `tests/fixtures/league_384_matches.json`  
API (Fase 3): passate 180gg + future 30gg

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
| `--explain` | off |

Output: `data/predictions/predictions_{date}.json`

---

### `backtest`

```bash
python -m src.cli backtest --league 384 [--model X | --all-models] [--rounds N]
```

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

Tabella comparativa 7 varianti + report JSON.

---

## Modelli disponibili

`ensemble`, `poisson`, `dixon_coles`, `elo`, `feature`

---

## Fase di sviluppo

Fase 1 (sync, predict, backtest) → Fase 2c (features, ablation, explain multi-match)
