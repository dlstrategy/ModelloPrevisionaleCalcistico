# 19 — FeatureTrainedModel offline (Fase 2g)

## Scopo

Primo modello **trainabile offline** basato sul feature vector esistente. Impara dai match finiti del dataset mock (o futuro dataset API) con softmax regression multinomial, senza dipendenze ML esterne.

Output invariato: **P(1), P(X), P(2), pick, confidence**.

## `feature` vs `feature_trained`

| Modello | Pesi | Training |
|---------|------|----------|
| `feature` | Fissi in codice (`WEIGHTS`) | Nessuno |
| `feature_trained` | Appresi da dati | CLI `train`, artifact JSON |

`feature_trained` **non** è incluso nell'ensemble (per ora).

## Training dataset

Modulo `src/training/dataset.py`:

- Solo match **finiti** con outcome noto
- `as_of = match.starting_at` (anti-leakage)
- `build_match_context(..., profile=...)` rispetta il profilo dati scelto
- Label: `HOME`, `DRAW`, `AWAY`

## Artifact JSON

Path: `data/models/feature_trained_{league_id}.json`

Contiene: feature names, scaler (mean/std), pesi softmax per classe, bias, profilo dati, config training, warnings.

## Comando train

```bash
python -m src.cli train --league 384 --model feature_trained --profile advanced
```

Opzioni: `--epochs`, `--learning-rate`, `--l2`, `--min-samples`, `--profile`.

## Predict / backtest

```bash
python -m src.cli predict --date 2025-10-18 --model feature_trained --explain
python -m src.cli backtest --league 384 --model feature_trained --rounds 5
```

Se l'artifact manca: messaggio chiaro, exit code 1, nessun traceback sporco.

## Limiti

- Dataset mock piccolo (~40 match finiti) → modello **sperimentale**
- Warning automatico se sample < `min_samples` (default 20)
- Profilo training deve coincidere con quello usato in inferenza (salvato nell'artifact)

## Moduli

```
src/training/
  dataset.py    # TrainingSample, build_training_samples
  softmax.py    # scaler, train_softmax_model
  artifacts.py  # save/load JSON
src/models/feature_trained.py
```
