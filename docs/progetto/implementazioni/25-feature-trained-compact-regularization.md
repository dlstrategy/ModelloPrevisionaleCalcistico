# Modulo 25 — FeatureTrained Compact & Regularization

Fase **2j** — ridurre overfitting di `feature_trained` con policy `full`/`compact`, clipping e L2.

## Perché serve compact

- Mock dataset ~40 match finiti vs feature vector >150 chiavi (profile advanced).
- Rapporto esempi/feature troppo basso → rischio overfitting in-sample.
- Backtest su artifact statico resta in-sample; valutazione onesta = **walk-forward refit**.
- Transfer-aware lineup (27 feature) mock e poco coperte → in compact restano solo i **diff** aggregati.

## full vs compact

| Aspetto | full | compact |
|---------|------|---------|
| Feature | Tutte disponibili nei sample | Allowlist robusta + filtri sparse/variance |
| L2 default | 0.001 | 0.005 |
| Clip default | None | ±5.0 post-scaling |
| Transfer lineup | Tutte (se in vector) | Solo 5 diff principali |
| Tactical | Sì (se abilitato) | No |

## Feature policy

Modulo: `src/training/feature_policy.py`

- `parse_feature_policy(name)` → `FeaturePolicy`
- `select_features_for_policy(samples, policy)` → feature names + warnings
- Selezione calcolata **solo sui training samples** della finestra corrente (walk-forward).

### compact include

- Gruppi: base, advanced_strength, strength_of_schedule, calendar, motivation
- xg/shots: subset medie principali
- lineup legacy: attack/defense rating, missing starters, continuity
- transfer diff: rating, confidence, unknown/low_sample/cross_league share diff

### compact esclude

- tactical
- home/away transfer share dettagliate (22 delle 27 transfer-aware)
- feature sparse (non-zero ratio < 5%) o varianza ~0

## Anti-leakage walk-forward

1. Train window → `build_training_samples(only_match_ids=train_ids)`
2. `select_features_for_policy` su quei sample only
3. Refit artifact per finestra
4. Predict test window con artifact della finestra
5. `ValueError` esplicito se train/test overlap fixture_ids

## CLI

```bash
# Train full (default, retrocompatibile)
python -m src.cli train --league 384 --model feature_trained --profile advanced

# Train compact
python -m src.cli train --league 384 --model feature_trained --profile advanced --feature-policy compact

# Walk-forward full
python -m src.cli walk-forward --league 384 --model feature_trained --profile advanced

# Walk-forward compact
python -m src.cli walk-forward --league 384 --model feature_trained --profile advanced --feature-policy compact

# Confronto full vs compact
python -m src.cli walk-forward --league 384 --model feature_trained --profile advanced --compare-feature-policies
```

## Feature importance

```bash
python -m src.cli train --league 384 --profile advanced --feature-policy compact
# stampa top 10 + salva data/models/feature_trained_384_importance.json
```

Importanza ≈ somma |peso| sulle classi HOME/DRAW/AWAY.

## Artifact metadata (nuovi campi)

- `feature_policy`, `selected_feature_count`, `original_feature_count`
- `feature_selection_warnings`, `regularization_notes`, `clip_value`

Artifact senza questi campi → default `feature_policy=full`, counts = len(feature_names).

## Limiti

- Mock dataset piccolo; metriche walk-forward instabili
- Compact allowlist manuale, non auto-ML
- Overfitting residuo possibile anche in compact
- Coefficienti transfer mock non calibrati
- Serve dataset reale per validazione out-of-sample (Fase 3)

## Prossimo step

- Auto-tuning L2/clip su walk-forward
- Feature selection data-driven con più match reali
- Integrazione Sportmonks reale (senza Predictions/Odds)
