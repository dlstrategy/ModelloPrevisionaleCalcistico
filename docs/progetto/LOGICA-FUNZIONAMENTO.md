# Logica di funzionamento del motore previsionale

Documento di audit end-to-end — stato attuale del programma (offline, Fase 2g).

## 1. Visione generale

```
Input dati → dataset → MatchContext → modello → P(1)/P(X)/P(2) → pick + confidence
                                    ↓
                          explain / validate / backtest / report
```

**Output unico del motore:** P(1), P(X), P(2), pick, confidence. Nessun mercato betting aggiuntivo.

---

## 2. Modalità dati

| Modalità | Descrizione |
|----------|-------------|
| **Offline fixture mock** | Default. Dati in `tests/fixtures/` + `data/processed/` |
| **Sportmonks API (futura)** | Attivabile con token + `ENABLE_SPORTMONKS_SYNC=true` |
| **Profilo `base`** | Core fixtures, standings, lineup, calendar — no xG/shots/tactical avanzato |
| **Profilo `advanced`** | Base + xG, shots, tactical, historical |
| **Profilo `all_in_no_predictions`** | Completo tranne Predictions/Odds |

### Fallback per dati mancanti

| Capability assente | Comportamento |
|--------------------|---------------|
| xG / Shots | Gruppo feature disabilitato o fallback; explain con `edge_status` |
| Lineup / Expected lineups | Fallback neutro lineup |
| Tactical | Default tactical |
| Calendar | `basic_rest_days` o neutral fatigue |
| Standings | Neutral motivation |

**PREDICTIONS e ODDS** sono sempre disabilitati per policy progetto — non influenzano il modello.

---

## 3. Flusso `predict`

```bash
python -m src.cli predict --date YYYY-MM-DD --model ensemble --explain
```

1. Carica `Settings` (`.env`, `DATA_PROFILE`)
2. Carica dataset processato (`load_dataset`)
3. Risolve modello (`get_model_by_name`)
4. Trova match futuri per data
5. Per ogni match: `build_match_context(dataset, match, settings, profile=...)`
6. Capability layer filtra feature groups per profilo
7. Modello produce `OutcomeProbabilities`
8. Pick = argmax; confidence = max prob
9. Salva JSON predizioni
10. Con `--explain`: JSON con edges, data_completeness, data_sources, edge_status, warnings

---

## 4. Flusso `train feature_trained`

```bash
python -m src.cli train --league 384 --model feature_trained --profile advanced
```

1. Solo match **finiti** con outcome
2. `as_of = match.starting_at` (anti-leakage)
3. Feature vector coerente col profilo scolto
4. Label HOME / DRAW / AWAY
5. Normalizzazione (mean/std per feature)
6. Softmax regression (gradient descent + L2)
7. Artifact JSON in `data/models/feature_trained_{league}.json`

**Artifact contiene:** feature_names, scaler, pesi, bias, data_profile, versione (`2g.1`), training_algorithm.

Il profilo training **deve coincidere** con quello usato in inferenza. Dataset mock piccolo (~40 match) → rischio **overfitting**.

---

## 5. Flusso `backtest` e valutazione

| Tipo | Comportamento | Onestà metriche |
|------|---------------|-----------------|
| Modelli statici (Poisson, Elo, feature) | `as_of=starting_at`, no training | OK per simulazione pre-match |
| `feature_trained` + artifact salvato | Valuta stessi match usati in train | **In-sample** — metriche fuorvianti |
| Walk-forward no-refit (ensemble, ecc.) | `as_of_simulation_no_refit` | OK temporalmente, no refit |
| Walk-forward refit (`feature_trained`) | Refit per finestra su soli match train | **Valutazione onesta** |

### Backtest in-sample (warning obbligatorio)

```text
Evaluation mode: in_sample_artifact
WARNING: feature_trained artifact was evaluated on historical matches that may overlap with training data.
Use walk-forward refit for honest temporal evaluation.
```

### Walk-forward refit onesto

```bash
python -m src.cli walk-forward --league 384 --model feature_trained --profile advanced
```

Finestra 1: train 1-10, test 11-15 → refit → predici test  
Finestra 2: train 1-15, test 16-20 → refit → predici test  
...

`training_mode: walk_forward_refit`

---

## 6. Anti-leakage

| Difesa | Dove |
|--------|------|
| `as_of = match.starting_at` | training, backtest, walk-forward |
| `finished_before(as_of)` | feature storiche |
| Gate `is_pre_match_fixture_row_usable` | lineup/tactical companion |
| `known_pre_match` vs `forecast` | lineup future vs finished |
| Profili dati + capability layer | no dati non attesi |
| `edge_status` in explain | edge disabilitati se gruppo off |
| Validate / data quality | controlli coerenza |

### Rischi residui

- Artifact allenato su tutti i match finiti poi valutato sugli stessi (backtest standard)
- Dataset mock piccolo e pulito
- Lineup/tactical mock non realistici
- Overfitting con 40 match e 137 feature
- Nessuna split train/calibration/test formale

---

## 7. Modelli disponibili

| Modello | Trainabile | Artifact | Rischio leakage | Quando usarlo |
|---------|------------|----------|-----------------|---------------|
| poisson | No | No | Basso | Baseline gol |
| dixon_coles | No | No | Basso | Correlazione 1-X-2 |
| elo | No (online update) | No | Basso | Forza relativa |
| feature | No (pesi fissi) | No | Basso | Feature engineering statico |
| feature_trained | Sì | Sì JSON | **Alto se backtest in-sample** | Dopo train; valutare con walk-forward refit |
| ensemble | No | No | Basso | Produzione default (no feature_trained) |

`feature_trained` **non** è nell'ensemble né in `--all-models`.

---

## 8. Buchi potenziali individuati

| # | Buco | Impatto | Rischio | Correzione | Priorità |
|---|------|---------|---------|------------|----------|
| 1 | Backtest feature_trained in-sample | Metriche 100% fuorvianti | Alto | Walk-forward refit (implementato) + warning | Alta |
| 2 | Mock dataset troppo piccolo | Overfitting, metriche instabili | Alto | Più dati reali o mock più grande | Alta |
| 3 | No split calibrazione/test | Calibrazione optimistica | Medio | Hold-out temporale dedicato | Media |
| 4 | No model registry versionato | Difficile riproducibilità | Medio | Registry con hash artifact | Media |
| 5 | No confronto auto feature vs feature_trained OOS | Scelta modello non guidata | Medio | Report comparativo walk-forward | Media |
| 6 | No simulatore stagione | Valutazione strategica limitata | Basso | Simulatore round-by-round | Bassa |
| 7 | Sync Sportmonks non attivo | Dati reali assenti | Alto (pre-stagione) | Fase 3 API | Alta (quando serve) |

---

Vedi anche: [implementazioni/20-logica-funzionamento-audit.md](implementazioni/20-logica-funzionamento-audit.md)
