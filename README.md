# Modello Previsionale Calcistico

Motore previsionale **proprietario** per il mercato **1/X/2**, basato su dati **Sportmonks Football API v3**.

## Fasi di sviluppo

| Fase | Stato | Descrizione |
|------|-------|-------------|
| **Fase 1** | Completata | Foundation modulare, Poisson, CLI, backtest base |
| **Fase 2** | Completata | Multi-modello, ensemble, calibrazione — offline |
| **Fase 2b** | Completata | Hardening: fix Elo, sync future, CI, normalize |
| **Fase 2c** | Completata | 9 gruppi feature, ablation, fixture 10 squadre |
| **Fase 2d** | Completata | Hardening: status, anti-leakage lineup, explain data_sources |
| **Fase 2e** | Completata | Data quality, validate CLI, walk-forward backtest |
| **Fase 2f** | Completata | Data Capability Layer, profili dati, fallback intelligenti |
| **Fase 2g** | Completata | FeatureTrainedModel offline (train + artifact JSON) |
| **Fase 2g.1** | Completata | Audit logico, warning in-sample, walk-forward refit |
| **Fase 2h** | Completata | Multi-league isolation, player global, transfer adaptation |
| **Fase 2h-b** | Completata | Composable transfer specialists (general + pair) |
| **Fase 2h-c** | Completata | Unknown player policy e hardening transfer layer |
| **Fase 2i** | Completata | Transfer-aware lineup features (gruppo player_lineup) |
| **Fase 2i-audit** | Completata | Audit documentazione flow giocatori/trasferimenti |
| **Fase 2j** | Completata | FeatureTrained compact & regularization (full/compact) |
| **Fase 2k** | Completata | Model evaluation report & promotion gate |
| **Fase 2l** | Completata | Coach impact, league adaptation & integration layer |
| **Fase 2l-b** | Completata | Coach explain hardening & Sportmonks mapping prep |
| **Fase 2m** | Completata | Real data readiness audit pre-Fase 3 |
| **Fase 3a** | Completata | Sportmonks API mappers offline-first |
| **Fase 3b** | Completata | Sync staging wiring mapper (flag controllato) |
| **Fase 3c** | Da attivare (`PARTIAL_READY`) | Sync reale controllata + validate/capabilities |

## Output (solo 1/X/2)

P(1), P(X), P(2), pick suggerito, confidenza.

## Modelli disponibili

| Modello | Stato |
|---------|-------|
| `poisson` | Implementato |
| `dixon_coles` | Implementato |
| `elo` | Implementato |
| `feature` | Implementato (softmax su feature vector) |
| `feature_trained` | Implementato (softmax allenata offline, artifact JSON) |
| `ensemble` | Implementato (pesi configurabili + temperature scaling) |

## Feature engineering (Fase 2+)

Moduli offline testabili con ablation:

| Gruppo | Modulo | Feature chiave |
|--------|--------|----------------|
| Base | form, standings, strength | attack/defense, form, classifica |
| Advanced strength | `advanced_strength.py` | rolling_5/10, opponent_adjusted |
| xG | `xg_features.py` | xg_diff, rolling_xg, goals_minus_xg |
| Shots | `shots_features.py` | xg_per_shot, conversion, big_chances |
| SOS | `schedule_strength.py` | avg_opponent_rating, points_vs_expected |
| Player/lineup | `lineup_features.py` | XI ratings, missing share, continuity |
| Tactical | `tactical_features.py` | formation matchup, wing/midfield edge |
| Coach | `coach_features.py` | tenure, adaptation, integration, potential signal |
| Calendar | `fatigue_features.py` | rest, midweek, fatigue_score |
| Motivation | `motivation_features.py` | top4/relegation pressure |

Fixture mock: `tests/fixtures/league_384_*.json` + `tests/fixtures/coaches/coach_profiles.json` (10 squadre, 8+2 giornate).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Senza token funziona in **modalità offline** (default).

## Comandi

```bash
# Sync (offline Fase 2, oppure API se Fase 3 abilitata)
python -m src.cli sync --league 384

# Stato dataset, profilo dati, fixture companion e feature attive
python -m src.cli status --league 384

# Capability dati per profilo (base / advanced / all_in_no_predictions)
python -m src.cli capabilities --profile base

# Predizioni
python -m src.cli predict --date 2025-09-20 --model ensemble
python -m src.cli predict --date 2025-09-20 --model poisson --explain

# Backtest singolo modello
python -m src.cli backtest --league 384 --model dixon_coles --rounds 5

# Confronto tutti i modelli
python -m src.cli backtest --league 384 --all-models --rounds 5

# Feature engineering (riepilogo gruppi feature)
python -m src.cli features --league 384

# Ablation test gruppi feature
python -m src.cli ablation --league 384 --rounds 5

# Data quality — consistenza dataset, fixture companion, feature e probabilità
python -m src.cli validate --league 384 --profile base

# Audit prontezza dati reali Sportmonks (statico, no API)
python -m src.cli readiness --league 384 --profile advanced
python -m src.cli readiness --league 384 --profile advanced --json --save

# Walk-forward — predizioni nel tempo con solo info pre-kickoff
python -m src.cli walk-forward --league 384 --model ensemble

# Training offline feature_trained
python -m src.cli train --league 384 --model feature_trained --profile advanced
python -m src.cli backtest --league 384 --model feature_trained --rounds 5
python -m src.cli walk-forward --league 384 --model feature_trained --profile advanced
```

## Fase 3 — Attivare Sportmonks API

In `.env`:

```env
SPORTMONKS_API_TOKEN=il_tuo_token
ENABLE_SPORTMONKS_SYNC=true
# Opzionale staging mapper avanzati (Fase 3b) — default false
ENABLE_SPORTMONKS_ADVANCED_MAPPERS=false
```

Poi: `python -m src.cli sync --league 384`

Con `ENABLE_SPORTMONKS_ADVANCED_MAPPERS=true` il sync API usa include avanzati e scrive companion staging in `data/processed/league_{id}_companions/`. Default **false** = include base only (comportamento sicuro).

## Test

```bash
python -m pytest -q
```

## Documentazione progetto

Documentazione completa su architettura, logiche, collegamenti e cronostoria:

- **[Indice documentazione](docs/progetto/README.md)**
- [Architettura e flussi](docs/progetto/ARCHITETTURA.md)
- [Cronostoria sviluppo](docs/progetto/CRONOSTORIA.md)
- [Guida operativa](docs/progetto/GUIDA-OPERATIVA.md)
- [Documentazione per implementazione](docs/progetto/implementazioni/) (26 moduli)
- [Logica di funzionamento (audit)](docs/progetto/LOGICA-FUNZIONAMENTO.md)

## Documentazione Sportmonks API

```bash
python scripts/fetch_sportmonks_docs.py
```

Riferimento locale:

- [`docs/sportmonks-football-v3-docs.md`](docs/sportmonks-football-v3-docs.md) — bundle 367 pagine
- [`docs/sportmonks-football-v3-pagine.md`](docs/sportmonks-football-v3-pagine.md) — catalogo completo pagine
