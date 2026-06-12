# Guida operativa

## Requisiti

- Python 3.10+
- `pip install -r requirements.txt`

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Modalità **offline** di default (nessun token richiesto).

---

## Comandi CLI

### Sync dati

```bash
python -m src.cli sync --league 384
```

### Stato sistema

```bash
python -m src.cli status --league 384
```

Mostra modalità offline/API, conteggi partite, fixture companion e feature attive su una partita futura di esempio. Se manca il dataset processato, suggerisce di eseguire `sync`.

### Predizioni

```bash
python -m src.cli predict --date 2025-10-18 --model ensemble
python -m src.cli predict --date 2025-10-18 --model ensemble --explain
```

Modelli: `ensemble`, `poisson`, `dixon_coles`, `elo`, `feature`

### Backtest

```bash
python -m src.cli backtest --league 384 --model ensemble --rounds 5
python -m src.cli backtest --league 384 --all-models --rounds 5
```

### Feature engineering

```bash
python -m src.cli features --league 384
```

Mostra gruppi feature attivi, conteggio per gruppo, esempio feature vector.

### Ablation test

```bash
python -m src.cli ablation --league 384 --rounds 5
```

Esegue 7 varianti cumulative e salva report in `data/backtests/ablation_*.json`.

Varianti: `base`, `base+xg`, `base+shots`, `base+player_lineup`, `base+tactical`, `base+calendar`, `full`

---

## Rigenerare fixture mock

```bash
python scripts/generate_fixtures.py
```

Genera 50 partite (10 squadre, 8+2 giornate) e tutti i file companion in `tests/fixtures/`. Lineup e tactical usano le squadre reali di ogni fixture; le partite finite hanno `data_availability: known_pre_match`, le future `forecast`.

---

## Test

```bash
python -m pytest -q
```

Risultato atteso: **53 passed**.

CI automatica su GitHub Actions (`.github/workflows/ci.yml`).

---

## Configurazione (`.env`)

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `ENABLE_SPORTMONKS_SYNC` | `false` | Abilita API reale |
| `SPORTMONKS_API_TOKEN` | vuoto | Token API |
| `FORM_WINDOW_MATCHES` | `5` | Finestra forma recente |
| `ENSEMBLE_WEIGHT_*` | vedi `.env.example` | Pesi ensemble |
| `MIN_CONFIDENCE_THRESHOLD` | `0.38` | Soglia confidenza bassa |

---

## Output

```
data/
  processed/league_384_dataset.json
  predictions/predictions_YYYY-MM-DD.json
  backtests/backtest_*.json
  backtests/ablation_*.json
```

---

## Fase 3 — API live

```env
SPORTMONKS_API_TOKEN=il_tuo_token
ENABLE_SPORTMONKS_SYNC=true
```

Sync scarica partite passate (180gg) + future (30gg).

---

## Riferimenti

- [ARCHITETTURA.md](ARCHITETTURA.md)
- [CRONOSTORIA.md](CRONOSTORIA.md)
- [06-feature-engineering.md](implementazioni/06-feature-engineering.md)
- [14-ablation-e-valutazione.md](implementazioni/14-ablation-e-valutazione.md)
- [16-hardening-feature-anti-leakage.md](implementazioni/16-hardening-feature-anti-leakage.md)
