# Modello Previsionale Calcistico

Motore previsionale **proprietario** per il mercato **1/X/2**, basato su dati **Sportmonks Football API v3**.

## Fasi di sviluppo

| Fase | Stato | Descrizione |
|------|-------|-------------|
| **Fase 1** | Completata | Foundation modulare, Poisson, CLI, backtest base |
| **Fase 2** | Completata | Multi-modello, feature avanzate, ensemble, calibrazione, report — **tutto offline** |
| **Fase 3** | Da attivare | Sync API Sportmonks reale (`ENABLE_SPORTMONKS_SYNC=true` + token) |

## Output (solo 1/X/2)

P(1), P(X), P(2), pick suggerito, confidenza.

## Modelli disponibili

| Modello | Stato |
|---------|-------|
| `poisson` | Implementato |
| `dixon_coles` | Implementato |
| `elo` | Implementato |
| `feature` | Implementato (softmax su feature vector) |
| `ensemble` | Implementato (pesi configurabili + temperature scaling) |

## Feature engineering (Fase 2)

- Forma recente, attacco/difesa, casa/trasferta
- Classifica dinamica (posizione, punti, streak)
- Calendario (giorni riposo, congestione)
- xG da fixture mock (`tests/fixtures/league_384_xg.json`)
- Lineup/duelli da fixture mock (`tests/fixtures/league_384_lineups.json`)

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

# Predizioni
python -m src.cli predict --date 2025-09-20 --model ensemble
python -m src.cli predict --date 2025-09-20 --model poisson --explain

# Backtest singolo modello
python -m src.cli backtest --league 384 --model dixon_coles --rounds 5

# Confronto tutti i modelli
python -m src.cli backtest --league 384 --all-models --rounds 5
```

## Fase 3 — Attivare Sportmonks API

In `.env`:

```env
SPORTMONKS_API_TOKEN=il_tuo_token
ENABLE_SPORTMONKS_SYNC=true
```

Poi: `python -m src.cli sync --league 384`

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
- [Documentazione per implementazione](docs/progetto/implementazioni/) (13 moduli)

## Documentazione Sportmonks API

```bash
python scripts/fetch_sportmonks_docs.py
```

Riferimento locale:

- [`docs/sportmonks-football-v3-docs.md`](docs/sportmonks-football-v3-docs.md) — bundle 367 pagine
- [`docs/sportmonks-football-v3-pagine.md`](docs/sportmonks-football-v3-pagine.md) — catalogo completo pagine
