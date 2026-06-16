# 31 — Sportmonks Sync Staging Wiring (Fase 3b)

Wire controllato dei mapper offline-first (Fase 3a) nel percorso sync API, **dietro flag esplicito**, senza cambiare il default production/offline.

## 1. Obiettivo Fase 3b

Ridurre il gap «mapper presenti ma non wired» preparando:

- include avanzati centralizzati;
- modulo wiring staging puro/testabile;
- scrittura companion/registry in path staging;
- integrazione cauta in `_sync_from_api()`;
- readiness aggiornata ma **non** `READY`.

**Vincolo:** default invariato; nessuna chiamata API nei test; nessun token stampato.

## 2. Differenza 3a / 3b / production futura

| Fase | Cosa fa |
|------|---------|
| **3a** | Mapper puri: JSON sample → companion/registry interni. Zero sync. |
| **3b** | Wiring staging: se flag attivo, sync API usa include avanzati, applica mapper, scrive companion in `data/processed/league_{id}_companions/`. |
| **3c (futura)** | Sync reale controllata con token locale, validate/capabilities, cutover production graduale. |

## 3. Flag advanced mappers

```env
ENABLE_SPORTMONKS_ADVANCED_MAPPERS=false   # default
```

Proprietà derivata: `settings.can_use_advanced_mappers` = `can_sync_api` **and** `enable_sportmonks_advanced_mappers`.

- **false (default):** comportamento identico a pre-3b.
- **true:** richiede anche `ENABLE_SPORTMONKS_SYNC=true` + token; attiva include avanzati e mapper staging.

Config: `src/config.py`, `.env.example`, readiness/status CLI.

## 4. Include base vs avanzati

| Modalità | Include string |
|----------|----------------|
| Base (default) | `participants;scores;state` |
| Staging advanced | `participants;scores;state;statistics;lineups;formations;coaches` |

Funzione: `build_fixture_includes(enable_advanced_mappers)` in `src/data_pipeline/sportmonks_mapper_wiring.py`.

## 5. Artifact generati

`SportmonksMappedArtifacts`:

| Campo | File output |
|-------|-------------|
| xg_companion | `xg.json` |
| shots_companion | `shots.json` |
| lineup_companion | `lineups.json` |
| tactical_companion | `tactical.json` |
| standings_companion | `standings.json` |
| coach_registry | `coach_profiles.json` |
| player_careers | `player_careers.json` |
| manifest | `manifest.json` |

Source tag: `sportmonks_mapper_staging` (o `missing` se payload assente).

## 6. Percorsi staging

```
data/processed/league_{league_id}_companions/
  xg.json
  shots.json
  lineups.json
  tactical.json
  standings.json
  coach_profiles.json
  player_careers.json
  manifest.json
```

`data/` non committato. Test usano `tmp_path`.

## 7. Cosa viene scritto e quando

| Condizione | Scrittura companion |
|------------|---------------------|
| Flag advanced **false** | Nessuna |
| Flag advanced **true** + sync API | `write_companion_artifacts()` dopo fetch |
| Mapper fallisce | Warning log; dataset base match **non** corrotto |
| Test offline | Solo `tmp_path` via test espliciti |

## 8. Comportamento con flag false

- Include base invariato.
- Nessun mapper invocato.
- Nessun companion scritto.
- Sync offline default invariato.
- Prediction / ensemble / FeatureModel invariati.

## 9. Readiness post-3b

Comando:

```bash
python -m src.cli readiness --league 384 --profile advanced
```

| Item | Stato atteso |
|------|--------------|
| `advanced_mapper_flag` | ready/info (default false) |
| `mapper_offline_*` | partial/warning |
| `sync_wiring_*` | partial/warning |
| `overall_status` | **PARTIAL_READY** |

## 10. Perché resta PARTIAL_READY

- Wiring non validato su API reale.
- Nessuno staging run reale con token locale.
- Artifact reali non ritrainati.
- `as_of` su payload reali da verificare.
- Production default resta offline/base.

## 11. Anti-leakage

- Mapper restano **puri** (no HTTP).
- Sync staging non deve usare dati futuri per training.
- Cutoff `as_of` da validare su run reale (Fase 3c).
- Artifact `feature_trained` mock da invalidare/ritrainare post-sync reale.
- Sample JSON marcati `offline_sample` — non trattati come dati reali.

## 12. Rischi residui

- Merge fixture per id in wiring: payload API reali hanno tutti gli include in un unico oggetto; sample offline vanno combinati manualmente in test.
- Player careers: sync non fetcha ancora `/players` bulk — solo se payload passato.
- Standings fetch separato: può fallire senza bloccare dataset base.
- Include names da validare su subscription reale.

## 13. Prossimo step — Fase 3c

1. Staging sync reale controllata con token locale.
2. Validate/capabilities su artifact reali.
3. Verifica `as_of` e anti-leakage su walk-forward.
4. Ritrain feature_trained su dataset reale.
5. Zero production cutover finché promotion gate non approva.

## Modulo wiring

`src/data_pipeline/sportmonks_mapper_wiring.py`:

- `build_fixture_includes()`
- `build_companion_artifacts_from_payloads()`
- `apply_mappers_to_sync_payloads()`
- `validate_mapped_artifacts()`
- `write_companion_artifacts()`
- `artifacts_to_serializable_dict()`

## Test

- `tests/test_sportmonks_mapper_wiring.py`
- `tests/test_sportmonks_sync_staging.py`
- `tests/test_real_data_readiness.py` (aggiornato)

## Riferimenti

- [30-sportmonks-api-mappers-offline-first.md](30-sportmonks-api-mappers-offline-first.md)
- [29-real-data-readiness-audit.md](29-real-data-readiness-audit.md)
- [13-fase-3-sportmonks-api.md](13-fase-3-sportmonks-api.md)
