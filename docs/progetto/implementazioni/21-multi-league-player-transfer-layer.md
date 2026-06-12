# Modulo 21 — Multi-league isolation & player transfer adaptation

Fase **2h** — preparazione dominio multi-campionato e trasferimenti giocatori.

## Perché isolare i campionati

Ogni lega ha dinamiche, forza relativa e feature companion distinte. Un modello `feature_trained` allenato sulla Serie A non deve essere applicato alla Liga. Dataset, artifact e report devono restare **scoped per `league_id`** (e in futuro `season_id`).

## Perché identità globale giocatori

I giocatori possono trasferirsi tra leghe. Un ID giocatore deve essere **globale**; lo storico per lega è una sequenza di snapshot (`PlayerCareer`).

## DataScope

Modulo: `src/data_pipeline/scope.py`

```python
DataScope(league_id=384)                    # dataset_key: league_384
DataScope(league_id=384, season_id=23614)   # league_384_season_23614
```

- `validate_match()` — blocca match di lega diversa
- `scope_metadata_dict()` — metadati in JSON dataset/artifact/report
- Path fisici **retrocompatibili**: `league_{id}_dataset.json`, `feature_trained_{id}.json`

## Player Global Layer

Modulo: `src/players/global_registry.py`

Fixture: `tests/fixtures/players/player_careers.json`

- `PlayerLeagueSnapshot` — rating/minuti per lega
- `PlayerCareer` — carriera globale
- `load_player_careers()`, `get_latest_snapshot()`, `get_player_snapshot_for_league()`

## Transfer Adaptation

Modulo: `src/players/transfer_adaptation.py`

```python
adapt_player_rating(snapshot, target_league_id=384, target_matches_played=0)
```

- Stessa lega: nessuna penalità
- Lega diversa: coefficiente mock da tabella `LEAGUE_TRANSFER_COEFFICIENTS`
- Lega sconosciuta: fallback `0.85` + confidence cap `0.50`
- Più partite nella lega target → confidence cresce (finestra 15 match)

**Attenzione:** coefficienti placeholder, da calibrare con dati reali.

## Player value resolver

Modulo: `src/players/player_value.py`

`resolve_player_value_for_league()` — utility league-aware per explain/future lineup integration.

## Protezione artifact

`FeatureTrainedModel` verifica `artifact.league_id == dataset.league_id`. Mismatch → `is_ready() == False` + errore chiaro.

## Explain / data_sources

`data_sources["player_transfer"] = "mock_player_career_registry"` quando player_lineup attivo.

## Limiti attuali

- Coefficienti transfer mock
- Nessuna integrazione profonda in feature vector lineup (solo layer + test)
- Path fisici non ancora migrati a `league_X_season_Y/`
- Registry giocatori solo fixture JSON offline

## Prossimi step

1. Calibrare coefficienti transfer con dati reali
2. Integrare `resolve_player_value_for_league` in lineup features
3. Multi-league CLI batch train/backtest
4. Model registry versionato per lega
5. Sync Sportmonks con player IDs globali
