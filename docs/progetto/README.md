# Documentazione progetto — Modello Previsionale Calcistico

Indice della documentazione interna del motore previsionale 1/X/2 per la Serie A.

## Documenti principali

| Documento | Contenuto |
|-----------|-----------|
| [ARCHITETTURA.md](ARCHITETTURA.md) | Architettura a strati, 10 gruppi feature, ablation, flussi |
| [LOGICA-FUNZIONAMENTO.md](LOGICA-FUNZIONAMENTO.md) | Audit end-to-end, anti-leakage, buchi/rischi |
| [CRONOSTORIA.md](CRONOSTORIA.md) | Timeline Fase 0 → 2l → 3 |
| [GUIDA-OPERATIVA.md](GUIDA-OPERATIVA.md) | Setup, comandi CLI, fixture, test |

## Documentazione per implementazione

| # | File | Modulo |
|---|------|--------|
| 01 | [01-setup-repository.md](implementazioni/01-setup-repository.md) | Repository, config, struttura |
| 02 | [02-documentazione-sportmonks-locale.md](implementazioni/02-documentazione-sportmonks-locale.md) | Bundle docs Sportmonks |
| 03 | [03-sportmonks-client-cache.md](implementazioni/03-sportmonks-client-cache.md) | Client API, cache |
| 04 | [04-data-pipeline.md](implementazioni/04-data-pipeline.md) | Sync, normalize, dataset |
| 05 | [05-domain-models.md](implementazioni/05-domain-models.md) | Entità dominio |
| 06 | [06-feature-engineering.md](implementazioni/06-feature-engineering.md) | **10 gruppi feature (~232 chiavi)** |
| 07 | [07-modelli-previsionali.md](implementazioni/07-modelli-previsionali.md) | Poisson, Dixon-Coles, Elo, Feature |
| 08 | [08-ensemble-calibrazione.md](implementazioni/08-ensemble-calibrazione.md) | Ensemble e calibrazione |
| 09 | [09-prediction-pipeline.md](implementazioni/09-prediction-pipeline.md) | Inferenza, explain arricchito |
| 10 | [10-backtesting.md](implementazioni/10-backtesting.md) | Backtest e metriche estese |
| 11 | [11-cli.md](implementazioni/11-cli.md) | CLI (sync, status, predict, backtest, features, ablation) |
| 12 | [12-test-e-fixture-offline.md](implementazioni/12-test-e-fixture-offline.md) | 305 test, fixture 10 squadre + coach |
| 13 | [13-fase-3-sportmonks-api.md](implementazioni/13-fase-3-sportmonks-api.md) | API live (da attivare) |
| 14 | [14-ablation-e-valutazione.md](implementazioni/14-ablation-e-valutazione.md) | Ablation test e valutazione feature |
| 15 | [15-hardening-foundation.md](implementazioni/15-hardening-foundation.md) | Fix Elo, sync, CI, normalize |
| 16 | [16-hardening-feature-anti-leakage.md](implementazioni/16-hardening-feature-anti-leakage.md) | Status CLI, anti-leakage lineup, metriche calibrazione |
| 17 | [17-data-quality-walk-forward.md](implementazioni/17-data-quality-walk-forward.md) | Data quality, validate, walk-forward |
| 18 | [18-data-capability-layer.md](implementazioni/18-data-capability-layer.md) | Data Capability Layer, profili, fallback |
| 19 | [19-feature-trained-model.md](implementazioni/19-feature-trained-model.md) | FeatureTrainedModel offline, CLI train |
| 20 | [20-logica-funzionamento-audit.md](implementazioni/20-logica-funzionamento-audit.md) | Audit logico, in-sample warning, walk-forward refit |
| 21 | [21-multi-league-player-transfer-layer.md](implementazioni/21-multi-league-player-transfer-layer.md) | Isolamento multi-lega, player global, transfer adaptation |
| 22 | [22-composable-transfer-specialists.md](implementazioni/22-composable-transfer-specialists.md) | Composable transfer: general adapter + pair specialists |
| 23 | [23-transfer-aware-lineup-features.md](implementazioni/23-transfer-aware-lineup-features.md) | Transfer-aware lineup features (gruppo player_lineup) |
| 24 | [24-player-transfer-flow-audit.md](implementazioni/24-player-transfer-flow-audit.md) | Audit flow giocatori/trasferimenti (Fase 2i-audit) |
| 25 | [25-feature-trained-compact-regularization.md](implementazioni/25-feature-trained-compact-regularization.md) | FeatureTrained compact & regularization (Fase 2j) |
| 26 | [26-model-evaluation-promotion-gate.md](implementazioni/26-model-evaluation-promotion-gate.md) | Model evaluation & promotion gate (Fase 2k) |
| 27 | [27-coach-impact-league-adaptation-layer.md](implementazioni/27-coach-impact-league-adaptation-layer.md) | Coach impact & league adaptation (Fase 2l) |
| 28 | [28-sportmonks-coach-mapping-prep.md](implementazioni/28-sportmonks-coach-mapping-prep.md) | Sportmonks coach mapping prep (Fase 2l-b) |
| 29 | [29-real-data-readiness-audit.md](implementazioni/29-real-data-readiness-audit.md) | Real data readiness audit pre-Fase 3 (Fase 2m) |
| 30 | [30-sportmonks-api-mappers-offline-first.md](implementazioni/30-sportmonks-api-mappers-offline-first.md) | Sportmonks API mappers offline-first (Fase 3a) |
| 31 | [31-sportmonks-sync-staging-wiring.md](implementazioni/31-sportmonks-sync-staging-wiring.md) | Sync staging wiring mapper (Fase 3b) |

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
