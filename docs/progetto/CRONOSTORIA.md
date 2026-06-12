# Cronostoria del programma

Timeline dello sviluppo del **Modello Previsionale Calcistico** — repository [dlstrategy/ModelloPrevisionaleCalcistico](https://github.com/dlstrategy/ModelloPrevisionaleCalcistico).

---

## Fase 0 — Setup iniziale

| Evento | Dettaglio |
|--------|-----------|
| Repository | `https://github.com/dlstrategy/ModelloPrevisionaleCalcistico` |
| Primo push | Commit iniziale (81 file) |

---

## Fase 0b — Documentazione Sportmonks locale

- Bundle 367 pagine in `docs/sportmonks-football-v3-docs.md`
- Catalogo pagine in `docs/sportmonks-football-v3-pagine.md`
- Cursor rules in `.cursor/rules/sportmonks.mdc`

---

## Fase 1 — Foundation (completata)

Pipeline offline end-to-end: dominio, Poisson, CLI, backtest base, 10 partite mock.

---

## Fase 2 — Multi-modello avanzato (completata)

Multi-modello (Poisson, Dixon-Coles, Elo, Feature, Ensemble), calibrazione, explain base, fixture xG/lineup.

---

## Fase 2b — Hardening foundation (completata)

**Obiettivo:** Solidificare la base prima di nuove feature.

| Area | Modifica |
|------|----------|
| Bug Elo | `p_away_beats = expected_score(ra, rh_adj)` |
| Sync API | Partite passate (180gg) + future (30gg) |
| Normalize | ISO datetime con timezone |
| Test client | Mock HTTP: auth, 429, errori, cache hit |
| CI | GitHub Actions pytest |

**Test:** 35 passed.

---

## Fase 2c — Feature engineering avanzato + ablation (completata)

**Obiettivo:** Sistema serio di feature testabile con ablation, tutto offline.

### Moduli feature (9 gruppi)

| Gruppo | File |
|--------|------|
| Advanced strength | `advanced_strength.py` |
| xG esteso | `xg_features.py` |
| Shot profile | `shots_features.py` |
| Strength of schedule | `schedule_strength.py` |
| Player/lineup | `lineup_features.py` |
| Tactical matchup | `tactical_features.py` |
| Calendar/fatigue | `fatigue_features.py` |
| Motivation | `motivation_features.py` |
| Orchestrazione | `feature_vector.py`, `feature_groups.py` |

### Ablation test

7 varianti cumulative: `base` → `full`

Metriche: accuracy, Brier, log-loss, Brier skill score, calibration bins, over/underconfidence.

### Fixture mock ampliate

- 10 squadre Serie A
- 8 giornate passate (40 partite) + 2 future (10 partite)
- 6 file JSON: matches, xg, shots, lineups, tactical, calendar
- Generatore: `scripts/generate_fixtures.py`

### CLI estesa

- `features` — riepilogo gruppi feature
- `ablation` — studio ablation
- `predict --explain` — explain arricchito per tutte le partite

### Explain arricchito

Probabilità, contributi modelli, edge (xG, strength, lineup, tactical, fatigue), warning confidenza.

**Test:** 42 passed.

---

## Fase 3 — Sync API Sportmonks (da attivare)

Token + `ENABLE_SPORTMONKS_SYNC=true`. Sync passato + futuro già predisposto.

---

## Milestone riepilogative

```
2025-2026 (sessione sviluppo)
│
├── [M0] Repository GitHub + push iniziale
├── [M1] Docs Sportmonks locale + Cursor rules
├── [M2] Fase 1 — Poisson + pipeline + CLI + backtest
├── [M3] Fase 2 — Multi-modello + ensemble
├── [M4] Documentazione progetto completa
├── [M5] Fase 2b — Hardening (Elo, sync, CI)
├── [M6] Fase 2c — Feature engineering + ablation
└── [M7] Fase 3 — API live (futuro)
```

---

## Problemi risolti

| Problema | Soluzione |
|----------|-----------|
| Elo away prob invertita | Fix `expected_score(ra, rh_adj)` |
| Predict senza partite future API | Sync today → today+30 |
| Date invalide in fixture generator | `datetime + timedelta` |
| SSL Windows | `urllib` + `certifi` |
| SQLite lock test | Cache `:memory:` |

---

## Evoluzione prevista

- Training pesi FeatureModel da ablation/backtest
- Calibrazione isotonica
- Fase 3 API live (xG, shots, lineup da Sportmonks)
- Estensione altre leghe
