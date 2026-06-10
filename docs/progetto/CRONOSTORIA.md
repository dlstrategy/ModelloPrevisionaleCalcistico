# Cronostoria del programma

Timeline dello sviluppo del **Modello Previsionale Calcistico** — repository [dlstrategy/ModelloPrevisionaleCalcistico](https://github.com/dlstrategy/ModelloPrevisionaleCalcistico).

---

## Fase 0 — Setup iniziale

**Obiettivo:** Collegare il progetto locale a GitHub e preparare l'ambiente.

| Evento | Dettaglio |
|--------|-----------|
| Creazione repository | `https://github.com/dlstrategy/ModelloPrevisionaleCalcistico` |
| Clone locale | Workspace `Modello previsionale calcstico` |
| Tooling | `gh` CLI, Python 3.12, `pytest`, `requirements.txt` |
| Primo push | Commit iniziale con struttura completa (81 file) |

**Deliverable:** Repository versionato, README base, `.env.example`, `.gitignore`.

---

## Fase 0b — Documentazione Sportmonks locale

**Obiettivo:** Avere riferimento API offline per Cursor e sviluppo senza navigare il web.

| Evento | Dettaglio |
|--------|-----------|
| Script `scripts/fetch_sportmonks_docs.py` | Scarica `llms.txt`, filtra Football API v3, genera bundle |
| Bundle generato | `docs/sportmonks-football-v3-docs.md` (367 pagine) |
| Catalogo pagine | `docs/sportmonks-football-v3-pagine.md` (elenco completo categorizzato) |
| Indice | `docs/sportmonks-llms-index.md` |
| Cursor rule | `.cursor/rules/sportmonks.mdc` — usa docs locali, solo 1/X/2 |
| Fix SSL Windows | Script riscritto con `urllib` + `certifi` (fallimento `requests`) |
| Fix pagina mancante | 1/367 pagine patchata manualmente nel bundle |

**Deliverable:** Documentazione API consultabile offline + regole IDE.

---

## Fase 1 — Foundation (completata)

**Obiettivo:** Motore modulare minimo funzionante offline con Poisson e backtest base.

### 1.1 Configurazione e dominio

- `src/config.py` — Settings da `.env`
- `src/logging_config.py` — Logging strutturato
- `src/domain/` — `Match`, `Team`, `Player`, `OutcomeProbabilities`, `Prediction`

### 1.2 Layer Sportmonks (predisposto)

- `SportmonksClient` con retry e rate limit
- Cache SQLite (`src/sportmonks/cache.py`)
- Moduli endpoint: leagues, fixtures, teams, standings
- Scheletri: players, lineups, injuries, statistics

### 1.3 Data pipeline

- `normalize.py` — JSON → `Match`
- `dataset_builder.py` — `MatchDataset` con filtri temporali
- `sync.py` — Caricamento da `tests/fixtures/league_384_matches.json`

### 1.4 Feature base

- Forma recente (`recent_form.py`)
- Forza attacco/difesa (`team_strength.py`)
- Contesto partita (`match_context.py`)

### 1.5 Modello Poisson

- Stima λ da strength
- Matrice score fino a `max_goals`
- Somma diagonali → P(1), P(X), P(2)

### 1.6 Prediction e CLI

- `predict_match`, `predict_round`
- CLI: `sync`, `predict`, `backtest`
- Export JSON in `data/predictions/`

### 1.7 Backtest base

- Walk-forward su partite finite
- Metriche: accuracy, Brier score

### 1.8 Test

- Test dominio, Poisson, dataset, cache, sync offline
- 10 partite mock Serie A (`league_id=384`)

**Stato fine Fase 1:** Pipeline end-to-end offline, un modello, CLI operativa.

---

## Fase 2 — Multi-modello avanzato (completata)

**Obiettivo:** Feature ricche, più modelli, ensemble, calibrazione, report comparativi — tutto offline.

### 2.1 Config estesa

- Pesi ensemble (`ENSEMBLE_WEIGHT_*`)
- Parametri Dixon-Coles (`DIXON_COLES_RHO`)
- Parametri Elo (`ELO_K`, `ELO_HOME_ADVANTAGE`)
- Calibrazione (`CALIBRATION_TEMPERATURE`)
- Gate Fase 3: `ENABLE_SPORTMONKS_SYNC=false` di default

### 2.2 Feature avanzate

| Feature | File | Stato |
|---------|------|-------|
| Classifica dinamica | `standings_features.py` | Implementato |
| Casa/trasferta, riposo | `home_away.py` | Implementato |
| xG | `xg_features.py` | Mock fixture |
| Lineup e duelli | `lineup_features.py` | Mock fixture |
| Metriche giocatore | `player_features.py` | Scheletro |
| Duelli tattici | `tactical_features.py` | Scheletro |
| `feature_vector` | `match_context.py` | Implementato |

### 2.3 Nuovi modelli

| Modello | File | Note |
|---------|------|------|
| Dixon-Coles | `dixon_coles.py` | Correzione τ low-score |
| Elo | `elo.py`, `elo_ratings.py` | Rating pre-partita |
| Feature | `feature_model.py` | Softmax su vettore feature |
| Ensemble | `ensemble.py` | Media pesata |
| Calibrazione | `calibration.py` | Temperature scaling |
| Registry | `registry.py` | Factory modelli |

### 2.4 Backtest multi-modello

- `--all-models` confronta tutti i modelli
- Report JSON in `data/backtests/`
- Metriche: log-loss, calibration bins

### 2.5 Explain

- `explain.py` — Breakdown feature per predizione

### 2.6 Fixture estese

- `league_384_xg.json`
- `league_384_lineups.json`

### 2.7 Test estesi

- Test Dixon-Coles, Elo, ensemble, standings, backtest multi-modello
- 15 test pass, 1 skipped (client API quando offline)

**Stato fine Fase 2:** Motore multi-modello completo in modalità offline.

---

## Fase 3 — Sync API Sportmonks (da attivare)

**Obiettivo:** Sostituire fixture mock con dati live da Sportmonks Football API v3.

| Prerequisito | Azione |
|--------------|--------|
| Token API | `SPORTMONKS_API_TOKEN` in `.env` |
| Abilitazione | `ENABLE_SPORTMONKS_SYNC=true` |
| Sync | `python -m src.cli sync --league 384` |

**Cosa cambia:**

- `sync.py` chiama `SportmonksClient` invece di fixture JSON
- xG, lineup, standings da endpoint documentati
- Cache SQLite popolata con risposte API

**Cosa resta uguale:**

- Pipeline normalizzazione → feature → modelli → prediction
- Output solo 1/X/2
- Nessun uso add-on Predictions Sportmonks

**Stato:** Codice predisposto, non attivato per scelta di sviluppo offline-first.

---

## Milestone riepilogative

```
2025 (sessione sviluppo)
│
├── [M0] Repository GitHub + push iniziale
├── [M1] Docs Sportmonks locale + Cursor rules
├── [M2] Fase 1 — Poisson + pipeline + CLI + backtest base
├── [M3] Fase 2 — Multi-modello + ensemble + feature avanzate
├── [M4] Documentazione progetto completa  ← questa milestone
└── [M5] Fase 3 — API live (futuro, on-demand)
```

---

## Problemi risolti durante lo sviluppo

| Problema | Soluzione |
|----------|-----------|
| `gh` non in PATH | Reinstall winget + refresh PATH |
| Auth GitHub interrotta | Retry `gh auth login` |
| SSL Python Windows Store | `urllib` + `certifi` nello script docs |
| Unicode `→` in log Windows | Sostituito con `->` in `sync.py` |
| SQLite lock su Windows test | Cache test con `:memory:` |
| PowerShell `&&` | Usare `;` come separatore |

---

## Evoluzione prevista (post Fase 3)

- Training pipeline per FeatureModel (pesi da dati storici)
- Calibrazione isotonica e reliability curves
- Ottimizzazione ρ Dixon-Coles su backtest
- Integrazione infortuni e metriche giocatore da API
- Estensione ad altre leghe (stesso `league_id` pattern)
