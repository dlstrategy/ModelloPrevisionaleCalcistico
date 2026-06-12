# 14 — Ablation e valutazione feature

## Obiettivo

Misurare il valore incrementale di ogni gruppo feature con **ablation test** — nessuna feature aggiunta senza evidenza quantitativa.

---

## Varianti ablation

Varianti **cumulative** (ogni step aggiunge un gruppo):

| Variante | Gruppi abilitati |
|----------|------------------|
| `base` | base + advanced_strength + strength_of_schedule + motivation |
| `base+xg` | + xg |
| `base+shots` | + shots |
| `base+player_lineup` | + player_lineup |
| `base+tactical` | + tactical |
| `base+calendar` | + calendar |
| `full` | tutti i 9 gruppi |

Definite in `src/features/feature_groups.py` → `ABLATION_VARIANTS`.

---

## Engine

**File:** `src/backtesting/ablation.py`

```python
run_ablation_study(dataset, settings, max_matches=N)
run_ablation_variant(dataset, settings, variant="base+xg")
save_ablation_report(results, output_dir)
```

- Modello valutato: **FeatureModel** con `enabled_groups` per variante
- Context: `build_match_context(..., enabled_feature_groups=groups)`
- Walk-forward senza leakage (come backtest standard)

---

## Metriche salvate

| Metrica | Descrizione |
|---------|-------------|
| `accuracy` | % pick corretti |
| `brier_score` | Errore quadratico probabilità |
| `log_loss` | Penalità probabilità calibrate |
| `brier_skill_score` | `1 - brier / brier_baseline` (baseline = freq. marginali) |
| `calibration_bins` | Confidence vs hit rate per bin |
| `overconfidence_rate` | % volte confidenza > hit + 5% |
| `underconfidence_rate` | % volte confidenza < hit - 5% |

Implementate in `src/backtesting/metrics.py`.

---

## CLI

```bash
python -m src.cli ablation --league 384 --rounds 5
```

Output console + `data/backtests/ablation_YYYYMMDD_HHMMSS.json`.

---

## Interpretazione

- **Brier skill > 0** — modello migliore del baseline naive
- **Delta Brier tra varianti** — valore marginale del gruppo aggiunto
- **Overconfidence alto** — modello troppo sicuro → calibrare temperature
- **Calibration gap** — probabilità non allineate alla frequenza reale

---

## Test

`tests/test_ablation.py` — verifica 7 varianti, conteggio feature crescente.

---

## Evoluzione

- Auto-selezione gruppi con lift significativo
- Training pesi FeatureModel da risultati ablation
- Cross-validation stagionale
