# 09 — Prediction pipeline

## Cosa è stato fatto

Layer di inferenza che collega dataset, feature, modelli e output JSON per predizioni singola partita e intera giornata.

## Moduli

| Modulo | File | Funzione |
|--------|------|----------|
| Predizione match | `predict_match.py` | Una partita → `Prediction` |
| Predizione giornata | `predict_round.py` | Lista partite su data |
| Explain | `explain.py` | Breakdown feature |

## Flusso `predict_match`

```python
1. model = get_model_by_name(model_name, settings, dataset)
2. context = build_match_context(match, dataset, settings)
3. probs = model.predict(context)
4. prediction = Prediction(match, probs, model.name, pick, confidence)
5. Se --explain: prediction.explanation = explain_prediction(context)
```

## Flusso `predict_round`

```python
1. matches = dataset.upcoming_on(target_date)
2. Per ogni match: predict_match(...)
3. Serializza lista Prediction → JSON
4. Salva in data/predictions/predictions_{date}.json
```

## Output `Prediction`

```json
{
  "match_id": 12345,
  "home_team": "Inter",
  "away_team": "Milan",
  "starting_at": "2025-09-20T18:45:00",
  "model": "ensemble",
  "probabilities": {
    "home_win": 0.45,
    "draw": 0.28,
    "away_win": 0.27
  },
  "pick": "1",
  "confidence": 0.45,
  "explanation": { ... }
}
```

(Struttura effettiva può variare leggermente nella serializzazione CLI.)

## Explain (`explain.py`)

Quando `--explain` è attivo, aggiunge un dict con:

- Valori feature principali dal `feature_vector`
- Contributi interpretativi (form, classifica, xG, lineup)
- Probabilità per modello (se ensemble)

Serve trasparenza senza esporre internals del modello.

## Regola temporale

Per partite future, `as_of = match.starting_at`. Le feature usano solo dati **precedenti** alla partita. Nessun risultato futuro entra nel contesto.

## Collegamenti

```
CLI predict
    ↓
predict_round(date, model)
    ↓
predict_match(match, model, dataset, settings)
    ├→ build_match_context()
    ├→ model.predict()
    └→ explain_prediction() [opzionale]
    ↓
data/predictions/*.json
```

## Fase di sviluppo

Fase 1: predict_match, predict_round
Fase 2: explain
