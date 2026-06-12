# Modulo 26 — Model Evaluation Report & Promotion Gate

Fase **2k** — giudizio tecnico motivato su candidato vs baseline (senza auto-promozione in production).

## Obiettivo

Dopo walk-forward refit e policy full/compact, serve un gate decisionale che risponda:

- **promoted** — candidato non peggiore su metriche probabilistiche (con sample sufficiente)
- **rejected** — peggioramento chiaro su Brier/log-loss/calibrazione
- **inconclusive** — sample piccolo, poche finestre, metriche miste

Il gate **non** cambia quale modello usa `predict`.

## Perché accuracy non basta

L'accuracy ignora la calibrazione delle probabilità. Un modello può azzeccare più pick con probabilità mal calibrate. Il gate privilegia:

1. **Brier score**
2. **Log-loss**
3. **Calibration gap**
4. Accuracy solo come segnale secondario (e mai da sola)

## Soglie default (`PromotionThresholds`)

| Parametro | Default | Significato |
|-----------|---------|-------------|
| min_tested_matches | 50 | Sotto questa soglia → max inconclusive |
| min_windows | 3 | Finestre walk-forward minime |
| max_brier_delta | 0.0 | Candidato Brier ≤ baseline |
| max_logloss_delta | 0.0 | Candidato log-loss ≤ baseline |
| max_calibration_gap_delta | 0.02 | Gap calibrazione non peggiora oltre tolleranza |
| max_pick_overconfidence_rate | 0.65 | Warning overconfidence |

Regressioni chiare: Brier +0.03, log-loss +0.05 → rejected.

## Confronti

**Principale:** `feature_trained/full` (baseline) vs `feature_trained/compact` (candidate) — entrambi walk-forward refit.

**Informativo:** `ensemble` walk-forward (no refit) — non equivalente metodologicamente, non usato per promozione automatica.

## CLI

```bash
python -m src.cli evaluate-models --league 384 --profile advanced
python -m src.cli evaluate-models --league 384 --profile advanced --include-ensemble-baseline
python -m src.cli evaluate-models --league 384 --profile advanced --json
```

Report JSON: `data/backtests/model_evaluation_{timestamp}.json`

## Esempio output (mock)

Su ~30 match testati (< 50):

```
Decision: INCONCLUSIVE
Reasons:
  - Match testati insufficienti per promozione (30 < 50)
Warnings:
  - dataset_small_for_promotion
```

## Perché spesso inconclusive sul mock

- ~40 match totali, ~30 in walk-forward test
- Varianza alta su metriche
- Transfer lineup sparse
- Gate conservativo by design

## Nessun effetto su prediction

- Nessun cambio modello default
- Nessun cambio ensemble
- Nessun cambio artifact salvato da evaluate-models

## Prossimo step

- Rivalutare con dataset reale (>100 match test)
- Soglie calibrate out-of-sample
- Gate multi-baseline (Poisson, feature statico) solo informativo
