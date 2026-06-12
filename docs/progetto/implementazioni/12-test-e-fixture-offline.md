# 12 — Test e fixture offline

## Test suite

**42 test** — `python -m pytest -q`

| File | Copertura |
|------|-----------|
| `test_poisson.py` | Modello Poisson |
| `test_dixon_coles.py` | Dixon-Coles |
| `test_elo.py` | Elo + fix away prob |
| `test_ensemble.py` | Ensemble |
| `test_features.py` | Team strength base |
| `test_feature_engineering.py` | Advanced strength, xG, shots, explain |
| `test_ablation.py` | 7 varianti ablation |
| `test_normalize.py` | Datetime Sportmonks/ISO |
| `test_sync.py` | Sync past+future, merge |
| `test_client.py` | HTTP mock (auth, 429, cache) |
| `test_cache.py` | SQLite cache |
| `test_backtest_*.py` | Backtest, no leakage |
| `test_standings.py` | Classifica dinamica |
| `test_prediction_output.py` | Output 1/X/2 |

---

## Fixture mock (10 squadre)

Generatore: `scripts/generate_fixtures.py`

| File | Contenuto |
|------|-----------|
| `league_384_matches.json` | 50 partite: 40 finite + 10 future |
| `league_384_xg.json` | xG per team + match_history |
| `league_384_shots.json` | Shot profile + match_history |
| `league_384_lineups.json` | Lineup, player impact, assenze |
| `league_384_tactical.json` | Formazioni, duelli tattici |
| `league_384_calendar.json` | Midweek, rotation risk |

### Squadre mock (ID)

| ID | Squadra | Strength |
|----|---------|----------|
| 1 | Inter | 1.85 |
| 2 | Genoa | 0.95 |
| 3 | Milan | 1.75 |
| 4 | Torino | 1.05 |
| 5 | Juventus | 1.70 |
| 6 | Napoli | 1.65 |
| 7 | Roma | 1.55 |
| 8 | Lazio | 1.45 |
| 9 | Atalanta | 1.40 |
| 10 | Fiorentina | 1.25 |

### Calendario

- **8 giornate passate** (5 partite/giornata = 40 match)
- **2 giornate future** (5 partite/giornata = 10 match)

---

## CI

GitHub Actions: `.github/workflows/ci.yml` — pytest su push/PR.

---

## Rigenerare fixture

```bash
python scripts/generate_fixtures.py
python -m src.cli sync --league 384
```

---

## Fase di sviluppo

Fase 1 (10 match, 4 squadre) → Fase 2c (50 match, 10 squadre, 6 file JSON)
