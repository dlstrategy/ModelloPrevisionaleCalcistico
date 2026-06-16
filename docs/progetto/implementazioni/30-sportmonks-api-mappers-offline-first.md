# 30 — Sportmonks API Mappers Offline-First (Fase 3a)

Implementazione mapper Sportmonks **senza chiamate API**: JSON sample locali → strutture interne / companion compatibili.

## 1. Obiettivo Fase 3a

Colmare il gap segnalato in Fase 2m (`PARTIAL_READY`) introducendo mapper puri e testati offline, pronti per wiring sync in Fase 3b.

**Vincolo:** nessuna chiamata API, nessun token, nessuna attivazione sync reale.

## 2. Vincolo: no API, solo JSON test

Tutti i mapper accettano `dict` JSON Sportmonks già presenti o sample creati in `tests/fixtures/sportmonks/`, marcati con `_meta.source = offline_sample`.

## 3. JSON test Sportmonks trovati / usati

| File | Origine | Usato da |
|------|---------|----------|
| `tests/fixtures/league_384_matches.json` | Già presente (formato Sportmonks base) | Riferimento fixture id=1001 |
| `tests/fixtures/sportmonks/fixture_statistics_sample.json` | **Creato** (sample offline) | statistics_mapper |
| `tests/fixtures/sportmonks/fixture_lineups_sample.json` | **Creato** | lineup_mapper |
| `tests/fixtures/sportmonks/coach_sample.json` | **Creato** | coach_mapper |
| `tests/fixtures/sportmonks/fixture_coaches_sample.json` | **Creato** | coach_mapper (fixture include) |
| `tests/fixtures/sportmonks/standings_season_sample.json` | **Creato** | standings_mapper |
| `tests/fixtures/sportmonks/player_statistics_sample.json` | **Creato** | player_mapper |

**JSON mancanti prima di 3a:** nessun raw Sportmonks con includes avanzati; creati sample minimali allineati a doc v3.

## 4. Mapper implementati

| Mapper | Modulo |
|--------|--------|
| statistics → xG/shots | `src/sportmonks/mappers/statistics_mapper.py` |
| lineups → player_lineup/tactical | `src/sportmonks/mappers/lineup_mapper.py` |
| coaches → CoachProfile | `src/sportmonks/mappers/coach_mapper.py` |
| standings → motivation/base | `src/sportmonks/mappers/standings_mapper.py` |
| players → PlayerCareer | `src/sportmonks/mappers/player_mapper.py` |

Utility condivise: `src/sportmonks/mappers/_common.py`

## 5. Dettaglio per mapper

### statistics_mapper

| Aspetto | Dettaglio |
|---------|-----------|
| Input | Fixture JSON con `statistics[]` (type_id / developer_name) |
| Output | Companion parziale `match_history` per xG e shots |
| Diretti | xG (5304), shots (42), SOT (86), goals (52), dangerous attacks (44) |
| Derivati | xGA da xG avversario, conversion_rate, xg_per_shot |
| Fallback | `{}` se statistiche assenti; no inventati |
| Limiti | No aggregazione team season in 3a; no as_of (mapper puro) |

### lineup_mapper

| Aspetto | Dettaglio |
|---------|-----------|
| Input | Fixture JSON con `lineups[]`, `formations[]` |
| Output | Companion `fixtures` per player_lineup e tactical |
| Diretti | player_id, team_id, formation, type_id starter (11) |
| Derivati | missing_starters_count, data_availability |
| Fallback | formation default `4-4-2` solo in tactical; no ratings inventati |
| Limiti | No expected lineups distinte se non marcate in JSON |

### coach_mapper

| Aspetto | Dettaglio |
|---------|-----------|
| Input | Coach JSON o fixture `coaches[]` include |
| Output | `CoachProfile` |
| Diretti | coach_id, name, country, MATCHES/PPG da statistics.details |
| Derivati | matches_in_charge, career_ppg, data_confidence, new_manager_bounce |
| Fallback | confidence 0.40 se stats assenti; xG/style None |
| Limiti | PPG before/under, style proxy non mappati in 3a |

### standings_mapper

| Aspetto | Dettaglio |
|---------|-----------|
| Input | Standings season payload `data[]` |
| Output | dict team_id → record + companion |
| Diretti | position, points, participant, details OVERALL_* |
| Derivati | played/wins/draws/losses da details |
| Fallback | campi None se assenti |
| Limiti | form opzionale; no live standings |

### player_mapper

| Aspetto | Dettaglio |
|---------|-----------|
| Input | Player JSON con `statistics[].details` |
| Output | `PlayerLeagueSnapshot`, `PlayerCareer`, `PlayerSkillVector` |
| Diretti | minutes (119), rating (118), goals (52), assists (79) |
| Derivati | sample_confidence, rating_percentile, skill vector |
| Fallback | rating 5.5 neutro se assente; low sample se minuti bassi |
| Limiti | No cronologia multi-lega automatica da singolo payload |

## 6. Cosa resta non wired nel sync

- **Fase 3b completata:** wiring staging in `sportmonks_mapper_wiring.py` + integrazione in `_sync_from_api()` **dietro** `ENABLE_SPORTMONKS_ADVANCED_MAPPERS=false` (default).
- Con flag **false**: include base only; nessun mapper; nessuna scrittura companion (comportamento pre-3b).
- Con flag **true**: include avanzati + mapper + scrittura `data/processed/league_{id}_companions/`.
- Vedi [31-sportmonks-sync-staging-wiring.md](31-sportmonks-sync-staging-wiring.md).

## 7. Readiness post-3a / post-3b

Resta **`PARTIAL_READY`**:

- `mapper_offline_*` → **partial** (warning)
- `sync_wiring_*` → **partial** (warning) dopo 3b
- `advanced_mapper_flag` → **ready** (info) se default false

Comando: `python -m src.cli readiness --league 384 --profile advanced`

## 8. Test aggiunti

- `tests/test_sportmonks_statistics_mapper.py`
- `tests/test_sportmonks_lineup_mapper.py`
- `tests/test_sportmonks_coach_mapper.py`
- `tests/test_sportmonks_standings_mapper.py`
- `tests/test_sportmonks_player_mapper.py`
- `tests/test_sportmonks_mapper_wiring.py` (3b)
- `tests/test_sportmonks_sync_staging.py` (3b)
- `tests/test_real_data_readiness.py` (aggiornato)

## 9. Anti-leakage

- Mapper **puri**: nessun I/O, nessun cutoff temporale interno
- Cutoff `as_of` da applicare nel futuro sync/walk-forward **prima** di aggregare statistiche
- Nessuna statistica futura introdotta dai mapper

## 10. Prossimo step — Fase 3c

Sync reale controllata con token locale:

1. Validare include avanzati su subscription reale
2. Verificare artifact companion su dataset reale
3. Ritrain feature_trained; promotion gate
4. Cutover production graduale (zero default change)

Vedi [31-sportmonks-sync-staging-wiring.md](31-sportmonks-sync-staging-wiring.md).

## Riferimenti

- [29-real-data-readiness-audit.md](29-real-data-readiness-audit.md)
- [13-fase-3-sportmonks-api.md](13-fase-3-sportmonks-api.md)
- [28-sportmonks-coach-mapping-prep.md](28-sportmonks-coach-mapping-prep.md)
