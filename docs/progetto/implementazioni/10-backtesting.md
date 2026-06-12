# 10 — Backtesting e valutazione

## Moduli

| Modulo | Funzione |
|--------|----------|
| `backtest.py` | Walk-forward multi-modello |
| `walk_forward.py` | Backtest walk-forward a finestre |
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
| `pick_overconfidence_rate` | Frazione pick con conf > hit binario (0/1) + 5% |
| `pick_underconfidence_rate` | Frazione pick con conf < hit binario - 5% |
| `mean_calibration_gap` | Media pesata `\|avg_confidence - hit_rate\|` sui bin |
| `calibration_bins` | Confidence vs hit rate + `gap` per bin |

> **Nota:** `pick_overconfidence_rate` e `pick_underconfidence_rate` sono metriche **grezze** basate su hit binario 0/1 del pick vs confidence. Alias retrocompatibili: `overconfidence_rate`, `underconfidence_rate`.

Baseline Brier = probabilità marginali empiriche (freq. 1/X/2 nel campione).

---

## Ablation test

Vedi [14-ablation-e-valutazione.md](14-ablation-e-valutazione.md).

```bash
python -m src.cli ablation --league 384 --rounds 5
```

Output tabella con `CalGap`, `PickOver`, `PickUnder` + `data/backtests/ablation_*.json`.

---

## Walk-forward backtest

```bash
python -m src.cli walk-forward --league 384 --model ensemble
```

Vedi [17-data-quality-walk-forward.md](17-data-quality-walk-forward.md).

---

## Output report

```
data/backtests/
  backtest_{model}_{timestamp}.json
  backtest_{model}_{timestamp}.csv
  backtest_comparison_{timestamp}.json
  walk_forward_{model}_{league_id}.json
  walk_forward_{model}_{league_id}.csv
  ablation_{timestamp}.json
```

---

## Test

- `tests/test_backtest_no_leakage.py`
- `tests/test_backtest_all_models.py`
- `tests/test_ablation.py`
- `tests/test_anti_leakage.py`
- `tests/test_walk_forward.py`

---

## Fase di sviluppo

Fase 1 (accuracy, Brier) → Fase 2c (ablation) → Fase 2d (metriche calibrazione) → Fase 2e (walk-forward)
