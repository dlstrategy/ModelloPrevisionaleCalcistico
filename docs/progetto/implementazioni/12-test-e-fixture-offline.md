# 12 — Test e fixture offline

## Test suite

**305 test** — `python -m pytest -q`

| File | Copertura |
|------|-----------|
| `test_poisson.py` | Modello Poisson |
| `test_dixon_coles.py` | Dixon-Coles |
| `test_elo.py` | Elo + fix away prob |
| `test_ensemble.py` | Ensemble |
| `test_features.py` | Team strength base |
| `test_feature_engineering.py` | Advanced strength, xG, shots, explain + data_sources |
| `test_ablation.py` | 8 varianti ablation |
| `test_anti_leakage.py` | Gate pre-match, storico, coerenza lineup |
| `test_status.py` | Comando CLI status |
| `test_data_quality.py` | Controlli data quality |
| `test_validate_cli.py` | CLI validate + report |
| `test_walk_forward.py` | Walk-forward backtest |
| `test_pre_match_gate.py` | Gate generico `is_pre_match_fixture_row_usable` |
| `test_data_sources.py` | Fonti explain prudenti (offline vs API mode) |
| `test_metrics.py` | Calibration gap, pick confidence rates |
| `test_normalize.py` | Datetime Sportmonks/ISO |
| `test_sync.py` | Sync past+future, merge |
| `test_client.py` | HTTP mock (auth, 429, cache) |
| `test_cache.py` | SQLite cache |
| `test_backtest_*.py` | Backtest, no leakage |
| `test_standings.py` | Classifica dinamica |
| `test_prediction_output.py` | Output 1/X/2 |
| `test_coach_registry.py` | Registry mock profili coach |
| `test_coach_adaptation.py` | Adattamento lega/paese |
| `test_coach_features.py` | Feature coach, explain, compact policy |
| `test_coach_capabilities.py` | Capability COACH_PROFILES |
| `test_transfer_lineup_features.py` | Transfer-aware lineup |
| `test_feature_policy.py` | Policy full vs compact |
| `test_feature_trained_compact.py` | FeatureTrained compact |
| `test_evaluate_models_cli.py` | Model evaluation / promotion gate |
| `test_capabilities_integration.py` | Integrazione capability layer |

---

## Fixture mock (10 squadre)

Generatore: `scripts/generate_fixtures.py`

| File | Contenuto |
|------|-----------|
| `league_384_matches.json` | 50 partite: 40 finite + 10 future |
| `league_384_xg.json` | xG per team + match_history |
| `league_384_shots.json` | Shot profile + match_history |
| `league_384_lineups.json` | Lineup, player impact, assenze (tutte le 50 partite) |
| `league_384_tactical.json` | Formazioni, duelli tattici (tutte le 50 partite) |
| `league_384_calendar.json` | Midweek, rotation risk |
| `coaches/coach_profiles.json` | 9 profili allenatore mock (team 1–5, 7–10; team 6 → unknown) |

### Convenzione `data_availability`

| Valore | Partite | Uso |
|--------|---------|-----|
| `known_pre_match` | Finite (40) | Backtest — snapshot pre-kickoff |
| `forecast` | Future (10) | Predict — proiezione pre-match |

Ogni riga lineup/tactical include `home_id`, `away_id` coerenti con `league_384_matches.json`. I rating offensive corrispondono alla tabella strength del generatore.

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
python -m src.cli status --league 384
```

---

## Fase di sviluppo

Fase 1 (10 match, 4 squadre) → Fase 2c (50 match, 10 squadre) → Fase 2l (`coaches/coach_profiles.json`, test coach)
