# Guida operativa

## Requisiti

- Python 3.10+
- Dipendenze: `pip install -r requirements.txt`

## Setup iniziale

```bash
cd "C:\Users\lucac\Desktop\Modello previsionale calcstico"
pip install -r requirements.txt
cp .env.example .env
```

Senza modifiche a `.env` il sistema gira in **modalità offline** (default).

---

## Configurazione (`.env`)

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `SPORTMONKS_API_TOKEN` | vuoto | Token API (Fase 3) |
| `ENABLE_SPORTMONKS_SYNC` | `false` | Abilita sync API reale |
| `OFFLINE_MODE` | `auto` | `auto` / `true` / `false` |
| `DEFAULT_LEAGUE_ID` | `384` | Serie A |
| `ENSEMBLE_WEIGHT_POISSON` | `0.25` | Peso Poisson nell'ensemble |
| `ENSEMBLE_WEIGHT_DIXON_COLES` | `0.30` | Peso Dixon-Coles |
| `ENSEMBLE_WEIGHT_ELO` | `0.20` | Peso Elo |
| `ENSEMBLE_WEIGHT_FEATURE` | `0.25` | Peso Feature model |
| `DIXON_COLES_RHO` | `-0.13` | Correzione low-score |
| `ELO_K` | `20` | Fattore K Elo |
| `ELO_HOME_ADVANTAGE` | `65` | Bonus Elo casa |
| `CALIBRATION_TEMPERATURE` | `1.0` | Temperature scaling (>1 appiattisce) |

### Logica offline vs API

```
can_sync_api = token presente AND ENABLE_SPORTMONKS_SYNC=true
is_offline   = OFFLINE_MODE=true OR (auto AND NOT can_sync_api)
```

Se `is_offline=True`, `sync` legge `tests/fixtures/league_{id}_matches.json`.

---

## Comandi CLI

### Sync dati

```bash
python -m src.cli sync --league 384
```

Output: `data/processed/league_384_matches.json`

### Predizioni

```bash
# Ensemble (consigliato)
python -m src.cli predict --date 2025-09-20 --model ensemble

# Singolo modello con spiegazione
python -m src.cli predict --date 2025-09-20 --model poisson --explain

# Modelli disponibili: poisson, dixon_coles, elo, feature, ensemble
```

Output: `data/predictions/predictions_YYYY-MM-DD.json`

### Backtest

```bash
# Singolo modello
python -m src.cli backtest --league 384 --model dixon_coles --rounds 5

# Confronto tutti i modelli
python -m src.cli backtest --league 384 --all-models --rounds 5
```

Output: `data/backtests/backtest_{model}_{timestamp}.json`

---

## Test

```bash
python -m pytest -q
```

Risultato atteso: 15 passed, 1 skipped (`test_client` quando offline).

---

## Aggiornare documentazione Sportmonks

```bash
# Download completo (367 pagine) + bundle + catalogo
python scripts/fetch_sportmonks_docs.py

# Solo catalogo da file locali (senza re-download)
python scripts/fetch_sportmonks_docs.py --catalog-only
```

Output:

- `docs/sportmonks-football-v3-docs.md` — bundle unico
- `docs/sportmonks-football-v3-pagine.md` — elenco completo pagine per categoria
- `docs/sportmonks-llms-index.md` — indice `llms.txt`

---

## Attivare Fase 3 (API live)

1. Ottenere token da [Sportmonks](https://www.sportmonks.com/)
2. In `.env`:

```env
SPORTMONKS_API_TOKEN=il_tuo_token
ENABLE_SPORTMONKS_SYNC=true
```

3. Eseguire sync:

```bash
python -m src.cli sync --league 384
```

4. Verificare log: deve comparire sync API, non "offline fixtures".

Vedi [implementazioni/13-fase-3-sportmonks-api.md](implementazioni/13-fase-3-sportmonks-api.md).

---

## Troubleshooting

| Sintomo | Causa probabile | Soluzione |
|---------|-----------------|-----------|
| "No matches found" | Data senza partite in dataset | Cambiare `--date` o aggiungere fixture |
| Sync sempre offline | `ENABLE_SPORTMONKS_SYNC=false` | Impostare `true` + token |
| Test client skipped | Normale in offline | Attivare Fase 3 per test API |
| `pytest` non trovato | Non in PATH | `python -m pytest` |
| Errori SSL fetch docs | Ambiente Windows | Script usa già `urllib`+`certifi` |

---

## Struttura output

```
data/
  processed/league_384_matches.json    # Dataset normalizzato
  predictions/predictions_*.json       # Predizioni giornata
  backtests/backtest_*.json            # Report valutazione
  cache.db                             # Cache API (Fase 3)
```

---

## Riferimenti

- [ARCHITETTURA.md](ARCHITETTURA.md) — Come i moduli si collegano
- [CRONOSTORIA.md](CRONOSTORIA.md) — Timeline sviluppo
- [implementazioni/](implementazioni/) — Dettaglio per modulo
