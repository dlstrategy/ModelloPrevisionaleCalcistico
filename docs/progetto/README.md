# Documentazione progetto — Modello Previsionale Calcistico

Indice della documentazione interna del motore previsionale 1/X/2 per la Serie A.

## Documenti principali

| Documento | Contenuto |
|-----------|-----------|
| [ARCHITETTURA.md](ARCHITETTURA.md) | Architettura a strati, 9 gruppi feature, ablation, flussi |
| [CRONOSTORIA.md](CRONOSTORIA.md) | Timeline Fase 0 → 2d → 3 |
| [GUIDA-OPERATIVA.md](GUIDA-OPERATIVA.md) | Setup, comandi CLI, fixture, test |

## Documentazione per implementazione

| # | File | Modulo |
|---|------|--------|
| 01 | [01-setup-repository.md](implementazioni/01-setup-repository.md) | Repository, config, struttura |
| 02 | [02-documentazione-sportmonks-locale.md](implementazioni/02-documentazione-sportmonks-locale.md) | Bundle docs Sportmonks |
| 03 | [03-sportmonks-client-cache.md](implementazioni/03-sportmonks-client-cache.md) | Client API, cache |
| 04 | [04-data-pipeline.md](implementazioni/04-data-pipeline.md) | Sync, normalize, dataset |
| 05 | [05-domain-models.md](implementazioni/05-domain-models.md) | Entità dominio |
| 06 | [06-feature-engineering.md](implementazioni/06-feature-engineering.md) | **9 gruppi feature (~137 chiavi)** |
| 07 | [07-modelli-previsionali.md](implementazioni/07-modelli-previsionali.md) | Poisson, Dixon-Coles, Elo, Feature |
| 08 | [08-ensemble-calibrazione.md](implementazioni/08-ensemble-calibrazione.md) | Ensemble e calibrazione |
| 09 | [09-prediction-pipeline.md](implementazioni/09-prediction-pipeline.md) | Inferenza, explain arricchito |
| 10 | [10-backtesting.md](implementazioni/10-backtesting.md) | Backtest e metriche estese |
| 11 | [11-cli.md](implementazioni/11-cli.md) | CLI (sync, status, predict, backtest, features, ablation) |
| 12 | [12-test-e-fixture-offline.md](implementazioni/12-test-e-fixture-offline.md) | 53 test, fixture 10 squadre |
| 13 | [13-fase-3-sportmonks-api.md](implementazioni/13-fase-3-sportmonks-api.md) | API live (da attivare) |
| 14 | [14-ablation-e-valutazione.md](implementazioni/14-ablation-e-valutazione.md) | Ablation test e valutazione feature |
| 15 | [15-hardening-foundation.md](implementazioni/15-hardening-foundation.md) | Fix Elo, sync, CI, normalize |
| 16 | [16-hardening-feature-anti-leakage.md](implementazioni/16-hardening-feature-anti-leakage.md) | Status CLI, anti-leakage lineup, metriche calibrazione |

## Documentazione API esterna

| File | Contenuto |
|------|-----------|
| [../sportmonks-football-v3-docs.md](../sportmonks-football-v3-docs.md) | Bundle 367 pagine |
| [../sportmonks-football-v3-pagine.md](../sportmonks-football-v3-pagine.md) | Catalogo pagine |

## Cursor Rules

| Regola | Scopo |
|--------|-------|
| [`.cursor/rules/sportmonks.mdc`](../../.cursor/rules/sportmonks.mdc) | Integrazione API Sportmonks v3 |
| [`.cursor/rules/auto-update-documentation.mdc`](../../.cursor/rules/auto-update-documentation.mdc) | Aggiornamento automatico documentazione a fine prompt |
