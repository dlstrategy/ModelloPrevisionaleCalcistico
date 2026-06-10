# 08 — Ensemble e calibrazione

## Cosa è stato fatto

Combinazione pesata dei quattro modelli base in un unico output, con temperature scaling per calibrare le probabilità finali.

## Ensemble (`ensemble.py`)

### Logica

1. Per ogni modello base: `probs_i = model.predict(context)`
2. Media pesata:
   ```
   P(1) = Σ w_i * P_i(1)
   P(X) = Σ w_i * P_i(X)
   P(2) = Σ w_i * P_i(2)
   ```
3. Normalizzazione (somma = 1)
4. Passaggio attraverso calibrazione

### Pesi (da `.env`)

| Variabile | Default |
|-----------|---------|
| `ENSEMBLE_WEIGHT_POISSON` | 0.25 |
| `ENSEMBLE_WEIGHT_DIXON_COLES` | 0.30 |
| `ENSEMBLE_WEIGHT_ELO` | 0.20 |
| `ENSEMBLE_WEIGHT_FEATURE` | 0.25 |

Factory: `EnsembleModel.from_settings(settings, base_models)`

## Calibrazione (`calibration.py`)

### Temperature scaling

Dato vettore log-probabilità `[log P(1), log P(X), log P(2)]`:

```
scaled = softmax(log_probs / temperature)
```

| `temperature` | Effetto |
|---------------|---------|
| = 1.0 | Nessuna modifica |
| > 1.0 | Probabilità più uniformi (meno confidenti) |
| < 1.0 | Probabilità più peaked (più confidenti) |

Parametro: `CALIBRATION_TEMPERATURE` (default 1.0)

### Evoluzione futura

- Isotonic regression su backtest
- Reliability curves per bin di confidenza
- Ottimizzazione temperature da dati storici

## Flusso completo

```
context
  → Poisson     ─┐
  → Dixon-Coles ─┤
  → Elo         ─┼→ weighted average → normalize → temperature_scale
  → Feature     ─┘
                        ↓
              OutcomeProbabilities (ensemble)
```

## Uso in CLI

```bash
python -m src.cli predict --date 2025-09-20 --model ensemble
```

`ensemble` è il modello consigliato per produzione.

## Collegamenti

```
registry.build_ensemble()
        ↓
EnsembleModel.predict(context)
        ↓
calibration.apply_temperature_scaling()
        ↓
predict_match.py → Prediction
```

## Metriche calibrazione nel backtest

`backtesting/metrics.py` calcola **calibration bins**: per ogni fascia di confidenza, confronta frequenza predetta vs frequenza osservata.

## Fase di sviluppo

Fase 2 — multi-modello avanzato
