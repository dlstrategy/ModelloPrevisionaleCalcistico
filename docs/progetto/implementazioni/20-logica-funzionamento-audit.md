# 20 — Audit logico e correzioni Fase 2g

## Scopo

Documentare la logica end-to-end del motore e le correzioni post-review Fase 2g (metriche in-sample, walk-forward refit).

Documento principale: [LOGICA-FUNZIONAMENTO.md](../LOGICA-FUNZIONAMENTO.md)

## Correzioni implementate

### Backtest in-sample warning

`backtest --model feature_trained` con artifact salvato marca:

- `evaluation_mode: in_sample_artifact`
- `training_leakage_risk: true`
- Warning console + JSON

### Walk-forward refit

`walk-forward --model feature_trained` usa automaticamente `walk_forward_refit`:

- Refit per finestra solo su match train
- Test match esclusi dal training della stessa finestra
- `training_mode: walk_forward_refit`
- Report con `training_features`, `training_warnings` per finestra

### FeatureTrainedModel.from_artifact

Factory per artifact in memoria — nessun I/O disco durante walk-forward.

### Artifact version

`model_version: 2g.1`, `training_algorithm: softmax_regression_python`

## Comandi

```bash
# Valutazione in-sample (con warning)
python -m src.cli backtest --league 384 --model feature_trained --rounds 5

# Valutazione onesta temporale
python -m src.cli walk-forward --league 384 --model feature_trained --profile advanced
```

## Vincoli mantenuti

- `feature_trained` fuori da ensemble e `--all-models`
- Output solo 1/X/2, pick, confidence
- Offline only
