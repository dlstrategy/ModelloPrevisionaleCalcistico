# 29 — Real Data Readiness Audit (Fase 2m)

Audit strutturato di prontezza **prima** dell'attivazione sync Sportmonks reale (Fase 3). Nessuna chiamata API in questa fase.

**Raccomandazione finale: `PARTIAL_READY`** (post Fase 3b: mapper wired in staging dietro flag, sync reale non validata)

Aggiornamento Fase 3a: vedi [30-sportmonks-api-mappers-offline-first.md](30-sportmonks-api-mappers-offline-first.md).
Aggiornamento Fase 3b: vedi [31-sportmonks-sync-staging-wiring.md](31-sportmonks-sync-staging-wiring.md).

---

## 1. Executive summary

Il motore previsionale 1/X/2 è **architecturalmente pronto** per integrare dati Sportmonks: client HTTP, cache SQLite, pipeline sync gated, normalizer, capability layer, 10 gruppi feature, transfer layer, coach layer, feature_trained full/compact, promotion gate e explain arricchito funzionano **offline/mock**.

**Non è ancora pronto** per un cutover production con dati reali completi: la sync API attuale scarica solo fixture base (`participants;scores;state`); mancano mapper reali per xG, shots, lineups, player careers e coach profiles. Artifact `feature_trained` mock vanno invalidati e ritrainati.

Comando audit statico:

```bash
python -m src.cli readiness --league 384 --profile advanced
python -m src.cli readiness --league 384 --profile advanced --json --save
```

Modulo: `src/data_pipeline/readiness.py`

---

## 2. Stato attuale: offline/mock, Fase 2m

| Aspetto | Stato |
|---------|-------|
| Modalità default | Offline (no token / `ENABLE_SPORTMONKS_SYNC=false`) |
| Dataset | `tests/fixtures/league_384_*.json` → `data/processed/` |
| Feature vector | ~232 chiavi (profilo advanced), 10 gruppi |
| Output prediction | P(1), P(X), P(2), pick, confidence — invariato |
| feature_trained | Fuori ensemble e `--all-models` |
| PREDICTIONS / ODDS | Policy-disabled permanentemente |
| Sync API | Predisposta ma non attiva di default |

---

## 3. Cosa è pronto per Fase 3

### Infrastruttura API/client/cache

- `SportmonksClient`: auth **solo** header `Authorization`, no token in query string
- Cache SQLite (`data/cache.db`) con TTL configurabili
- Retry/backoff su HTTP 429
- Logging senza stampa token
- `ENABLE_SPORTMONKS_SYNC` default `false`; `can_sync_api` richiede token + flag

### Pipeline dati

- `_sync_from_api()` gated; offline default in `sync_league_data()`
- Dataset salvato in `data/processed/league_{id}_dataset.json`
- `DataScope` su league/season
- Normalizer robusto su campi mancanti (fixture mock + API skeleton)
- Finestra sync: 180 giorni passato + 30 futuro (UTC date)
- Backtest/walk-forward: `as_of=match.starting_at` anti-leakage

### Feature / capabilities

- Data Capability Layer con profili `base`, `advanced`, `all_in_no_predictions`
- 10 feature groups definiti e testati offline
- Fallback intelligenti per dati assenti
- Explain con `data_sources`, `coach_summary`, `transfer_lineup_summary`, warnings

### Transfer / coach (offline)

- Global player registry, composable transfer, unknown player policy
- Coach registry, adaptation, unknown coach policy
- Doc mapping coach Sportmonks ([28](28-sportmonks-coach-mapping-prep.md))

### Training / evaluation

- feature_trained full/compact, league isolation artifact
- Walk-forward refit train-only feature selection
- Promotion gate (non usa backtest in-sample per decisione)

### CLI

- Tutti i comandi esistenti funzionano offline
- Nuovo: `readiness` (audit statico)

---

## 4. Cosa non è pronto

| Area | Gap |
|------|-----|
| Sync includes | Solo base; no statistics, lineups, coaches |
| xG / shots | Moduli feature OK offline; **nessun mapper API → domain** in sync |
| Lineups / tactical | Fixture companion mock; API lineups non integrate |
| Player careers | `player_careers.json` solo fixture; no sync API |
| Coach profiles | `coach_profiles.json` fixture; no fetch coaches/statistics |
| Standings API | Modulo esiste; non in sync path principale |
| Artifact feature_trained | Validità solo su mock; invalidi post-dataset reale |
| Style fit coach | Proxy; dati insufficienti senza storico reale |

---

## 5. Bloccanti prima di attivare API reale

1. **Mapper xG/shots** — statistics fixture non normalizzate in pipeline sync
2. **Mapper lineups** — include `lineups` / expected lineups non in sync
3. **Mapper player careers** — registry globale non popolabile da API
4. **Mapper coach** — doc 28 non implementato in codice sync
5. **Include sync insufficienti** — feature avanzate resterebbero fallback/mock anche con API on
6. **Retraining obbligatorio** — artifact mock non validi su scope/league/season reali

---

## 6. Rischi non bloccanti

- Rate limit API su sync iniziale ampia (180+30 giorni) — mitigato da cache
- Style fit / tactical proxy con bassa confidenza — warning explain già presenti
- Lineup confirmed vs expected — dipende da timing pre-match
- Cross-league transfer coefficients — da calibrare su dati reali
- Timezone UTC vs locale kickoff — verificare su primi fixture reali
- Mock companion fixtures obsoleti se non aggiornati post-sync

---

## 7. Tabella feature group coverage

| Feature group | Stato offline | Fonte Sportmonks prevista | Diretto/Derivato | Pronto Fase 3? | Note |
|---------------|---------------|---------------------------|------------------|----------------|------|
| base | OK mock | fixtures + scores + participants | Diretto + derivato | **Parziale** | Sync base copre; standings parziale |
| advanced_strength | OK mock | storico scores/fixture | Derivato | **Parziale** | OK se storico fixture completo |
| xg | OK mock | fixture statistics (xG) | Diretto | **No** | Mapper API assente |
| shots | OK mock | fixture statistics (shots) | Diretto | **No** | Mapper API assente |
| strength_of_schedule | OK mock | storico fixture | Derivato | **Parziale** | Dipende da storico |
| player_lineup | OK mock | lineups + player stats | Diretto + derivato | **No** | Include lineups non in sync |
| tactical | OK mock | lineups + formation | Derivato | **No** | Dipende da lineups API |
| coach | OK mock | coaches + statistics.details | Diretto + derivato | **No** | Solo fixture; doc 28 non wired |
| calendar | OK mock | starting_at fixture | Diretto | **Sì** | Disponibile con sync base |
| motivation | OK mock | standings | Derivato | **Parziale** | Standings API da integrare |

---

## 8. Tabella Sportmonks endpoint/include necessari

| Endpoint / include | Feature group | Stato mapper | Priorità |
|--------------------|---------------|--------------|----------|
| `GET /fixtures/between/{start}/{end}` + `participants;scores;state` | base, calendar | **Implementato** in sync | P0 |
| `GET /leagues/{id}` (currentSeason) | scope | **Implementato** | P0 |
| `GET /standings/seasons/{season_id}` | base, motivation | Modulo esiste, **non in sync** | P1 |
| Fixture `include=statistics` (xG, shots) | xg, shots | **Non implementato** | P0 |
| Fixture `include=lineups` | player_lineup, tactical | **Non implementato** | P0 |
| Fixture `include=coaches` | coach | **Non implementato** | P0 |
| `GET /coaches/{id}` + `statistics.details` | coach | **Non implementato** | P1 |
| `GET /players/{id}` + statistics | player_lineup, transfer | **Non implementato** | P1 |
| Predictions API | — | **Policy-disabled** | — |
| Odds API | — | **Policy-disabled** | — |

---

## 9. Audit API/client/cache

| Controllo | Esito |
|-----------|-------|
| Auth solo header Authorization | OK |
| Token in query string | No |
| Cache attiva | OK (SQLite, TTL) |
| Rate limit 429 | Retry con backoff |
| Pagination | Non necessaria per fixtures between (window limitata) |
| Error handling | `SportmonksError`, `SportmonksRateLimitError` |
| Logging senza token | OK (path/debug only) |
| OFFLINE_MODE / ENABLE_SPORTMONKS_SYNC | Coerenti; default offline sicuro |
| Warning sync senza token | Aggiunto in `sync_league_data()` |

---

## 10. Audit sync/normalizer/dataset

| Controllo | Esito |
|-----------|-------|
| `_sync_from_api()` predisposto, non default | OK |
| Sync offline default | OK |
| Salvataggio `data/processed` | OK |
| `DataScope` league/season | OK |
| Normalizer campi mancanti | OK (test offline) |
| Stati fixture | OK (`state` include) |
| Timezone | UTC in sync window; verificare su reali |
| Leakage finestra futuro | Future solo per predict, non training finished |
| Dati futuri in training/backtest | Esclusi (solo `is_finished`) |

---

## 11. Audit transfer player

| Controllo | Esito | Prontezza |
|-----------|-------|-----------|
| player_id globale | OK offline | partial |
| Snapshots per lega | OK fixture | partial |
| Career registry | OK fixture `player_careers.json` | partial |
| Trasferimenti cross-league | OK composable transfer | partial |
| Unknown player policy | OK | ready |
| Low sample player | OK warning | ready |
| Source league unknown | OK fallback | ready |
| Role normalization | OK | ready |
| Dependency Sportmonks player statistics | Documentata, **non wired** | not_ready |
| Popolamento `player_careers.json` da API | **Mancante** | not_ready |

---

## 12. Audit coach

| Controllo | Esito | Prontezza |
|-----------|-------|-----------|
| CoachProfile | OK fixture | partial |
| Coach statistics | Offline mock | not_ready (API) |
| include coaches | Documentato doc 28 | not_ready |
| teams/history/latest | Documentato | not_ready |
| PPG before/under, deltas | Derivati offline | partial |
| Style proxy | Proxy con warning | partial |
| Anti-leakage | `as_of` rispettato | ready |
| Unknown coach | OK | ready |
| Low sample coach | OK | ready |
| Cross-country adaptation | OK offline | partial |

---

## 13. Audit feature_trained / promotion gate

| Controllo | Esito |
|-----------|-------|
| full/compact compatibili strutturalmente | OK |
| Artifact league isolation | OK (path per league) |
| No leakage walk-forward | OK (refit per window) |
| Feature selection train-only | OK |
| Compact riduce feature | OK |
| Promotion gate non usa in-sample backtest | OK |
| Retraining richiesto su dati reali | **Obbligatorio** |
| Artifact mock su dataset reale | **Invalidi** — non promuovere |

---

## 14. Audit explain / data sources

| Controllo | Esito |
|-----------|-------|
| data_sources mock/api/fallback/disabled | OK onesto su mock |
| coach_summary | OK (advanced) |
| transfer_lineup_summary | OK |
| edge_status | OK |
| missing data warnings | OK |
| fallback indicators | OK |
| low confidence | OK |
| style fit insufficient warning | OK (Fase 2l-b) |

---

## 15. Checklist pre-attivazione Fase 3

- [ ] Eseguire `python -m src.cli readiness --league 384 --profile advanced`
- [ ] Overall status = `READY` (attualmente `PARTIAL_READY`)
- [ ] Implementare mapper statistics (xG, shots) + test offline con payload API sample
- [ ] Estendere sync includes: `statistics;lineups;coaches` (minimo)
- [ ] Integrare standings season in sync o post-process
- [ ] Implementare sync player careers / player stats
- [ ] Implementare coach fetch + normalizer (doc 28)
- [ ] Sync reale su staging; `validate` + `capabilities` su dataset reale
- [ ] Ritrain `feature_trained` full/compact; promotion gate walk-forward
- [ ] Confermare PREDICTIONS/ODDS ancora disabled
- [ ] Confermare ensemble invariato (no feature_trained)
- [ ] Documentare delta rispetto mock in CRONOSTORIA

---

## 16. Raccomandazione finale

### `PARTIAL_READY`

**Motivazione:** infrastruttura client/cache/sync gated e layer feature offline sono solidi; i **mapper API avanzati** (xG, shots, lineups, player careers, coach) non sono collegati al sync pipeline. Attivare sync reale oggi produrrebbe un dataset incompleto e feature groups in fallback silenzioso o proxy.

**Prossimo step consigliato:** Fase 3c — sync reale controllata con token locale, validate/capabilities su artifact companion, ritrain feature_trained, zero production cutover.

---

## Riferimenti

- [13 — Fase 3 Sportmonks API](13-fase-3-sportmonks-api.md)
- [28 — Coach mapping prep](28-sportmonks-coach-mapping-prep.md)
- Modulo readiness: `src/data_pipeline/readiness.py`
- Test: `tests/test_real_data_readiness.py`
