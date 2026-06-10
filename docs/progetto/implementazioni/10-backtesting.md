# 10 — Backtesting

## Cosa è stato fatto

Sistema di valutazione walk-forward su partite già concluse, con metriche multi-dimensionali e report comparativo tra modelli.

## Moduli

| Modulo | File | Funzione |
|--------|------|----------|
| Engine | `backtest.py` | Loop valutazione |
| Metriche | `metrics.py` | Accuracy, Brier, log-loss, calibration |
| Report | `reports.py` | Export JSON confronto |

## Logica walk-forward

```python
finished = dataset.finished_matches_ordered()
# Ultimi N "rounds" (gruppi per data)

for match in evaluation_set:
    as_of = match.starting_at
    context = build_match_context(match, dataset, settings)
    probs = model.predict(context)
    actual = outcome_from_score(match)  # 1, X, o 2
    record_prediction(probs, actual, pick, confidence)
```

**Anti-leakage:** `build_match_context` usa `finished_before(as_of)` — il risultato della partita valutata non è mai nelle feature.

## Metriche (`metrics.py`)

| Metrica | Formula / significato |
|---------|----------------------|
| **Accuracy** | % pick corretti |
| **Brier score** | Media (p - actual)² su one-hot |
| **Log-loss** | -log(p_actual) |
| **Calibration bins** | Per fascia confidenza, freq. predetta vs osservata |

Brier e log-loss penalizzano probabilità mal calibrate, non solo pick sbagliati.

## Modalità CLI

```bash
# Singolo modello
python -m src.cli backtest --league 384 --model elo --rounds 5

# Tutti i modelli
python -m src.cli backtest --league 384 --all-models --rounds 5
```

`--rounds N` limita alle ultime N giornate con partite finite nel dataset.

## Report (`reports.py`)

Con `--all-models`, genera JSON con:

- Metriche per ogni modello
- Ranking per accuracy / Brier
- Timestamp e parametri league

Output: `data/backtests/backtest_{model}_{timestamp}.json`

## Collegamenti

```
CLI backtest
    ↓
backtest.run_backtest(model, dataset, settings, rounds)
    ├→ build_match_context (no leakage)
    ├→ model.predict
    └→ metrics.compute_all()
    ↓
reports.write_backtest_report()
```

## Limitazioni attuali

- Dataset mock: 10 partite — metriche indicative, non statisticamente robuste
- Nessuna cross-validation stagionale automatica
- ρ Dixon-Coles e temperature non ottimizzati da backtest

## Fase di sviluppo

Fase 1: backtest base, accuracy, Brier
Fase 2: multi-modello, log-loss, calibration bins, report comparativo
