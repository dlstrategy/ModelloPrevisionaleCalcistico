# 11 — Interfaccia CLI

## Cosa è stato fatto

Interfaccia a riga di comando unificata per sync, predizione e backtest. Entry point: `python -m src.cli`.

## File

| File | Ruolo |
|------|-------|
| `src/cli.py` | Parser argparse + comandi |
| `src/__main__.py` | `python -m src` → cli |

## Comandi

### `sync`

```bash
python -m src.cli sync --league 384
```

- Carica dataset (offline o API)
- Salva `data/processed/league_{id}_matches.json`
- Logga modalità usata (offline fixtures vs API)

### `predict`

```bash
python -m src.cli predict --date YYYY-MM-DD [--model NAME] [--explain] [--league ID]
```

| Flag | Default | Descrizione |
|------|---------|-------------|
| `--date` | obbligatorio | Giornata da predire |
| `--model` | `ensemble` | poisson, dixon_coles, elo, feature, ensemble |
| `--explain` | off | Aggiunge breakdown feature |
| `--league` | 384 | ID lega Sportmonks |

Output: `data/predictions/predictions_{date}.json`

### `backtest`

```bash
python -m src.cli backtest --league 384 [--model NAME | --all-models] [--rounds N]
```

| Flag | Descrizione |
|------|-------------|
| `--model` | Singolo modello da valutare |
| `--all-models` | Confronta tutti i modelli |
| `--rounds` | Numero giornate da includere |

Mutuamente esclusivi: `--model` o `--all-models`.

## Flusso interno CLI

```
parse_args()
    ↓
load_settings()
setup_logging()
    ↓
┌─ sync  → sync_dataset()
├─ predict → load dataset → predict_round()
└─ backtest → load dataset → run_backtest() / run_all_models_backtest()
```

## Collegamenti

```
cli.py
  → config.load_settings()
  → data_pipeline.sync / dataset_builder
  → prediction.predict_round
  → backtesting.backtest
  → models.registry.get_model_by_name
```

## Estensioni future

- `calibrate` — ottimizza pesi/temperature da backtest
- `report` — genera report HTML
- `ingest` — import manuale CSV partite

## Fase di sviluppo

Fase 1: sync, predict, backtest base
Fase 2: --all-models, --explain, modelli multipli
