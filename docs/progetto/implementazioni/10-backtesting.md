# 10 — Backtesting e valutazione

## Moduli

| Modulo | Funzione |
|--------|----------|
| `backtest.py` | Walk-forward multi-modello |
| `ablation.py` | Ablation test gruppi feature |
| `metrics.py` | Metriche estese |
| `reports.py` | Report JSON/CSV |

---

## Backtest standard

```bash
python -m src.cli backtest --league 384 --model ensemble --rounds 5
python -m src.cli backtest --league 384 --all-models --rounds 5
```

Walk-forward su partite finite, `as_of = match.starting_at`, no leakage.

---

## Metriche (`BacktestMetrics`)

| Metrica | Formula / significato |
|---------|----------------------|
| `accuracy` | Pick corretti / totale |
| `brier_score` | Media (p - y)² su one-hot |
| `log_loss` | -log(p_actual) |
| `brier_skill_score` | 1 - brier_model / brier_baseline |
| `overconfidence_rate` | conf > hit + 5% |
| `underconfidence_rate` | conf < hit - 5% |
| `calibration_bins` | Confidence vs hit rate |

Baseline Brier = probabilità marginali empiriche (freq. 1/X/2 nel campione).

---

## Ablation test

Vedi [14-ablation-e-valutazione.md](14-ablation-e-valutazione.md).

```bash
python -m src.cli ablation --league 384 --rounds 5
```

Output: `data/backtests/ablation_*.json`

---

## Output report

```
data/backtests/
  backtest_{model}_{timestamp}.json
  backtest_{model}_{timestamp}.csv
  backtest_comparison_{timestamp}.json
  ablation_{timestamp}.json
```

---

## Test

- `tests/test_backtest_no_leakage.py`
- `tests/test_backtest_all_models.py`
- `tests/test_ablation.py`

---

## Fase di sviluppo

Fase 1 (accuracy, Brier) → Fase 2 (log-loss, calibration) → Fase 2c (Brier skill, ablation, over/underconf)
