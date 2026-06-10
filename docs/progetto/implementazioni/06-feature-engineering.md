# 06 — Feature engineering

## Cosa è stato fatto

Sistema di estrazione feature da storico partite, classifica dinamica, calendario, xG e lineup. Tutto aggregato in `MatchContext` con `feature_vector` per FeatureModel e explain.

## Moduli

| Modulo | File | Input | Output |
|--------|------|-------|--------|
| Forma recente | `recent_form.py` | Ultimi N match squadra | `TeamFormSnapshot` (GF, GA) |
| Forza squadra | `team_strength.py` | Storico gol | `TeamStrength` (attack/defense casa/trasferta) |
| Classifica | `standings_features.py` | Tutte le partite finite | `TeamStandingsSnapshot` (pos, punti, streak) |
| Calendario | `home_away.py` | Date partite | `ScheduleSnapshot` (riposo, congestione) |
| xG | `xg_features.py` | Fixture mock xG | `TeamXgSnapshot` |
| Lineup | `lineup_features.py` | Fixture mock lineup | `LineupImpact` |
| Tattico | `tactical_features.py` | LineupImpact | `tactical_edge_score` |
| Giocatori | `player_features.py` | — | Scheletro Fase 3 |
| Contesto | `match_context.py` | Tutto sopra | `MatchContext` |

## Logica `build_match_context`

```python
as_of = match.starting_at
history = dataset.finished_before(as_of)

# Per home e away:
form = compute_team_form(history, team_id, window)
strength = compute_team_strengths(history, team_id)
standings = get_team_standings(history, team_id)
schedule = compute_schedule_snapshot(history, team_id, as_of)
xg = get_team_xg(team_id)          # da mock JSON
lineup = get_lineup_impact(match)  # da mock JSON

feature_vector = _build_feature_vector(context)
```

## Feature vector (chiavi principali)

| Chiave | Significato |
|--------|-------------|
| `home_attack`, `home_defense` | Forza offensiva/difensiva in casa |
| `away_attack`, `away_defense` | Forza in trasferta |
| `home_form_gf`, `home_form_ga` | Gol fatti/subiti forma recente |
| `home_position`, `away_position` | Posizione in classifica |
| `points_gap`, `position_gap` | Differenziali |
| `home_rest_days`, `away_rest_days` | Giorni dall'ultima partita |
| `home_congestion`, `away_congestion` | Partite ultimi 14 giorni |
| `home_xg_for`, `away_xg_against` | xG (se disponibile) |
| `tactical_edge` | Vantaggio tattico da lineup |

## Classifica dinamica

Non usa API standings in Fase 2. `standings_features.py` **ricostruisce** la classifica sommando punti da partite finite prima di `as_of`. Garantisce coerenza temporale nel backtest.

## Dati mock (Fase 2)

| File | Uso |
|------|-----|
| `tests/fixtures/league_384_xg.json` | xG per squadra |
| `tests/fixtures/league_384_lineups.json` | Qualità lineup e duelli |

In Fase 3 questi moduli leggeranno da API Sportmonks.

## Collegamenti

```
MatchDataset.finished_before(as_of)
        ↓
  [recent_form, team_strength, standings, home_away]
        ↓
  [xg_features, lineup_features] ← fixture mock
        ↓
  match_context.build_match_context()
        ↓
  MatchContext.feature_vector → FeatureModel, explain.py
  MatchContext.strength/form → Poisson, Dixon-Coles, Elo
```

## Fase di sviluppo

Fase 1: form, strength, match_context base
Fase 2: standings, schedule, xG, lineup, feature_vector esteso
