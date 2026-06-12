# 09 — Prediction pipeline

## Moduli

| Modulo | Funzione |
|--------|----------|
| `predict_match.py` | Singola partita → `Prediction` |
| `predict_round.py` | Giornata → lista + JSON |
| `explain.py` | Explain arricchito |
| `data_sources.py` | Origine dati per gruppo feature |

---

## Flusso predict

```python
enabled_groups = getattr(model, "enabled_groups", None)
context = build_match_context(..., enabled_feature_groups=enabled_groups)
probs = model.predict(context)
→ Prediction con pick, confidence, metadata["uncertain"]
```

---

## Explain arricchito

**Funzione:** `explain_prediction(context, prediction, dataset, settings)`

### Output

```json
{
  "probabilities": {"home": 0.45, "draw": 0.28, "away": 0.27},
  "pick": "1",
  "confidence": 0.45,
  "model_contributions": {
    "poisson": {"home": 0.42, "draw": 0.30, "away": 0.28},
    "dixon_coles": {...},
    "elo": {...},
    "feature": {...}
  },
  "edges": {
    "xg": 0.35,
    "team_strength": 0.12,
    "lineup": 0.08,
    "tactical": 0.05,
    "fatigue": -0.03
  },
  "data_sources": {
    "base": "historical",
    "xg": "mock_fixture_historical",
    "player_lineup": "mock_fixture",
    "tactical": "mock_fixture"
  },
  "top_factors": {
    "positive": [{"feature": "home_xg_diff_avg", "value": 0.45}],
    "negative": [{"feature": "away_fatigue_score", "value": 0.62}]
  },
  "warnings": ["Confidenza bassa (38%) — pick incerto"]
}
```

### Edge calcolati

| Edge | Fonte |
|------|-------|
| xG | `home_xg_profile.xg_diff_avg` vs away |
| team_strength | `home_advanced.season_strength` vs away |
| lineup | XI attack rating home vs away |
| tactical | formation_matchup + wing_advantage |
| fatigue | away fatigue vs home (invertito) |

### `data_sources`

Mappa ogni gruppo feature alla fonte effettiva:
- `historical` — storico partite finite
- `mock_fixture` / `mock_fixture_historical` — fixture offline
- `default_fallback` — valori neutri (lineup/tactical non disponibili)
- `api` — Sportmonks (Fase 3)

### Warning automatici

- Confidenza sotto `MIN_CONFIDENCE_THRESHOLD`
- Squadre equilibrate su xG e strength
- Assenze significative (≥2 starter)
- Lineup/tactical con `default_fallback`

---

## CLI

```bash
python -m src.cli predict --date 2025-10-18 --model ensemble --explain
```

Explain stampato per **ogni** partita della giornata (flag `--explain`).

---

## Fase di sviluppo

Fase 1 (base) → Fase 2c (explain con edge e contributi modelli) → Fase 2d (`data_sources`, warning fallback)
