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

### Moduli feature (evoluzione: 9 → 10 gruppi)

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

## Fase 2d — Hardening feature e anti-leakage (completata)

**Obiettivo:** Consolidare Fase 2c prima di nuove feature — diagnostica, gate pre-match, test leakage, metriche calibrazione.

| Area | Modifica |
|------|----------|
| CLI `status` | Riepilogo modalità, dataset, companion, feature attive |
| Fixture generator | Lineup/tactical con home/away reali per ogni match |
| Pre-match gate | `known_pre_match` (finite) / `forecast` (future) |
| Explain | Sezione `data_sources`, warning fallback lineup/tactical |
| Metriche | `mean_calibration_gap`, `pick_overconfidence_rate` |
| Test | `test_status`, `test_anti_leakage`, `test_metrics` |

**Test:** 53 passed.

---

## Fase 2e — Data quality e walk-forward (completata)

| Area | Modifica |
|------|----------|
| Data quality | `src/data_quality/` — controlli dataset, companion, feature |
| CLI `validate` | Report JSON/CSV in `data/quality/` |
| Walk-forward | `src/backtesting/walk_forward.py` — finestre temporali |
| CLI `walk-forward` | Backtest realistico pre-kickoff |

**Test:** 74 passed.

---

## Fase 2f — Data Capability Layer (completata)

| Area | Modifica |
|------|----------|
| Capability layer | `src/data_capabilities/` — profili base / advanced / all_in_no_predictions |
| Config | `DATA_PROFILE=base` in `.env` |
| CLI `capabilities` | Report capability, feature groups, completeness score |
| Integrazione | `status`, `validate --profile`, `predict --explain` |
| Policy | PREDICTIONS e ODDS sempre disabilitati |

**Test:** 116 passed.

---

## Fase 2g — FeatureTrainedModel offline (completata)

| Area | Modifica |
|------|----------|
| Training | `src/training/` — dataset, scaler, softmax regression |
| Modello | `feature_trained` — artifact JSON in `data/models/` |
| CLI `train` | Allenamento offline con profilo dati |
| Predict/backtest | `--model feature_trained` (non in ensemble) |

**Test:** 130+ passed.

---

## Fase 2g.1 — Audit logico e correzioni valutazione (completata)

| Area | Modifica |
|------|----------|
| Backtest | Warning `in_sample_artifact` per feature_trained |
| Walk-forward | Refit automatico per feature_trained |
| Modello | `FeatureTrainedModel.from_artifact()` |
| Docs | `LOGICA-FUNZIONAMENTO.md`, modulo 20 |

**Test:** 148+ passed.

---

## Fase 2h — Multi-league player transfer (completata)

Isolamento multi-lega, player global registry, transfer adaptation layer.

---

## Fase 2i — Transfer-aware lineup (completata)

27 feature aggregate nel gruppo `player_lineup`; explain `transfer_lineup_summary`.

---

## Fase 2j — FeatureTrained compact (completata)

Policy `full` vs `compact`, clipping, L2, feature importance.

---

## Fase 2k — Model evaluation & promotion gate (completata)

CLI `evaluate-models`, report walk-forward full vs compact.

---

## Fase 2l — Coach impact layer (completata)

Gruppo `coach` (68 feature), registry mock, adaptation lega/paese, explain `coach_summary`. Capability `COACH_PROFILES`.

**Test:** 305 passed.

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
├── [M6b] Fase 2d — Hardening anti-leakage + status CLI
├── [M6c] Fase 2e — Data quality + walk-forward
├── [M6d] Fase 2f — Data Capability Layer + fallback
├── [M6e] Fase 2g — FeatureTrainedModel offline
├── [M6f] Fase 2h–2k — Transfer layer, compact, evaluation gate
├── [M6g] Fase 2l — Coach impact & league adaptation
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
| Lineup con squadre sbagliate in fixture | `MatchRef` con home/away reali in `generate_fixtures.py` |
| Leakage lineup post-match | Gate `data_availability` + `resolve_lineup_for_match()` |

---

## Evoluzione prevista

- Training pesi FeatureModel da ablation/backtest
- Calibrazione isotonica
- Fase 3 API live (xG, shots, lineup, **coach statistics** da Sportmonks)
- Estensione altre leghe
