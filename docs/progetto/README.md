# Documentazione progetto — Modello Previsionale Calcistico

Indice della documentazione interna del motore previsionale 1/X/2 per la Serie A.

## Documenti principali

| Documento | Contenuto |
|-----------|-----------|
| [ARCHITETTURA.md](ARCHITETTURA.md) | Architettura completa, collegamenti tra moduli, flussi dati e logiche |
| [CRONOSTORIA.md](CRONOSTORIA.md) | Cronologia di sviluppo (Fase 1 → 2 → 3) |
| [GUIDA-OPERATIVA.md](GUIDA-OPERATIVA.md) | Setup, comandi, configurazione, troubleshooting |

## Documentazione per implementazione

| # | File | Modulo |
|---|------|--------|
| 01 | [01-setup-repository.md](implementazioni/01-setup-repository.md) | Repository, config, struttura cartelle |
| 02 | [02-documentazione-sportmonks-locale.md](implementazioni/02-documentazione-sportmonks-locale.md) | Bundle docs Sportmonks + script fetch |
| 03 | [03-sportmonks-client-cache.md](implementazioni/03-sportmonks-client-cache.md) | Client API, cache SQLite, endpoint |
| 04 | [04-data-pipeline.md](implementazioni/04-data-pipeline.md) | Sync, normalizzazione, dataset |
| 05 | [05-domain-models.md](implementazioni/05-domain-models.md) | Entità di dominio calcistico |
| 06 | [06-feature-engineering.md](implementazioni/06-feature-engineering.md) | Feature squadra, partita, classifica, xG, lineup |
| 07 | [07-modelli-previsionali.md](implementazioni/07-modelli-previsionali.md) | Poisson, Dixon-Coles, Elo, Feature |
| 08 | [08-ensemble-calibrazione.md](implementazioni/08-ensemble-calibrazione.md) | Ensemble e calibrazione probabilità |
| 09 | [09-prediction-pipeline.md](implementazioni/09-prediction-pipeline.md) | Inferenza match/giornata, explain |
| 10 | [10-backtesting.md](implementazioni/10-backtesting.md) | Valutazione modelli, metriche, report |
| 11 | [11-cli.md](implementazioni/11-cli.md) | Interfaccia a riga di comando |
| 12 | [12-test-e-fixture-offline.md](implementazioni/12-test-e-fixture-offline.md) | Test automatici e dati mock |
| 13 | [13-fase-3-sportmonks-api.md](implementazioni/13-fase-3-sportmonks-api.md) | Collegamento API reale (da attivare) |

## Documentazione API esterna

| File | Contenuto |
|------|-----------|
| [../sportmonks-football-v3-docs.md](../sportmonks-football-v3-docs.md) | Bundle Markdown API Sportmonks Football v3 (367 pagine) |
| [../sportmonks-football-v3-pagine.md](../sportmonks-football-v3-pagine.md) | Catalogo completo di tutte le pagine scaricate |
| [../sportmonks-llms-index.md](../sportmonks-llms-index.md) | Indice originale `llms.txt` |

## Cursor Rules

Regole IDE in [`.cursor/rules/sportmonks.mdc`](../../.cursor/rules/sportmonks.mdc).
