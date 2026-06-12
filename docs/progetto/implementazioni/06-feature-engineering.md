# 06 — Feature engineering (9 gruppi)

## Panoramica

Sistema modulare di feature engineering con **~137 chiavi** nel `feature_vector`, organizzate in **9 gruppi** testabili con ablation.

Orchestrazione:
- `match_context.py` — `build_match_context()`
- `feature_vector.py` — `build_full_feature_vector()`
- `feature_groups.py` — definizione gruppi + filtri

---

## Gruppi e moduli

### 1. Base (`base`) — 20 feature

| Modulo | Feature |
|--------|---------|
| `team_strength.py` | home/away attack, defense |
| `recent_form.py` | form_gf, form_ga |
| `standings_features.py` | position, points, gaps, win_streak |
| `home_away.py` | rest_days, congestion |

### 2. Advanced team strength — 16 feature

**File:** `advanced_strength.py`

| Feature | Descrizione |
|---------|-------------|
| `attack_rating`, `defense_rating` | Rating normalizzati |
| `attack_home_rating`, `defense_home_rating` | Split casa |
| `attack_away_rating`, `defense_away_rating` | Split trasferta |
| `opponent_adjusted_strength` | Performance vs qualità avversari |
| `rolling_5_strength`, `rolling_10_strength` | Forma rolling |
| `season_strength` | Forza stagionale |

### 3. xG — 20 feature

**File:** `xg_features.py`  
**Fixture:** `league_384_xg.json` (teams + match_history)

| Feature | Descrizione |
|---------|-------------|
| `xg_for_avg`, `xg_against_avg`, `xg_diff_avg` | Medie xG |
| `xg_for_home`, `xg_against_home`, `xg_for_away`, `xg_against_away` | Split H/A |
| `rolling_xg_for_5`, `rolling_xg_against_5`, `rolling_xg_diff_5` | Rolling 5 |
| `goals_minus_xg`, `goals_against_minus_xga` | Over/underperformance |

### 4. Shot profile — 18 feature

**File:** `shots_features.py`  
**Fixture:** `league_384_shots.json`

| Feature | Descrizione |
|---------|-------------|
| `shots_for_avg`, `shots_against_avg` | Volume tiri |
| `shots_on_target_for_avg`, `shots_on_target_against_avg` | Tiri in porta |
| `xg_per_shot`, `xga_per_shot_against` | Qualità tiro |
| `shot_conversion_rate` | Conversione |
| `big_chances_for`, `big_chances_against` | Occasioni da gol |

### 5. Strength of schedule — 8 feature

**File:** `schedule_strength.py`

| Feature | Descrizione |
|---------|-------------|
| `avg_opponent_rating_last_5/10` | Qualità avversari |
| `points_vs_expected_last_5` | Punti vs attesi |
| `xg_diff_vs_opponent_strength` | xG diff aggiustato |

### 6. Player/lineup — 20 feature

**File:** `lineup_features.py`  
**Fixture:** `league_384_lineups.json`

| Feature | Descrizione |
|---------|-------------|
| `starting_xi_attack/defense/midfield_rating` | Qualità XI |
| `goalkeeper_rating` | Portiere |
| `missing_starters_count` | Assenti |
| `missing_minutes/goals/xg_share` | Impatto assenze |
| `bench_strength`, `lineup_continuity` | Panchina e continuità |

**Gate anti-leakage** (`resolve_lineup_for_match`):
- `known_pre_match` — partite finite, valido in backtest
- `forecast` — partite future, valido in predict
- Validazione `home_id` / `away_id` vs partecipanti match
- `source`: `mock_fixture` | `default_fallback`

### 7. Tactical matchup — 8 feature

**File:** `tactical_features.py`  
**Fixture:** `league_384_tactical.json`

| Feature | Descrizione |
|---------|-------------|
| `home/away_formation_code` | Codice formazione |
| `formation_matchup_score` | Compatibilità formazioni |
| `wing_advantage`, `midfield_advantage`, `aerial_advantage` | Duelli per zona |
| `pressing_mismatch`, `defensive_line_risk` | Stile di gioco |

### 8. Calendar/fatigue — 13 feature

**File:** `fatigue_features.py`  
**Fixture:** `league_384_calendar.json`

| Feature | Descrizione |
|---------|-------------|
| `days_rest_home/away`, `rest_difference` | Riposo |
| `matches_last_7/14_days_home/away` | Congestione |
| `played_midweek_home/away` | Partita infrasettimanale |
| `rotation_risk_home/away` | Rischio rotazione |
| `fatigue_score_home/away` | Score composito fatigue |

### 9. Motivation — 14 feature

**File:** `motivation_features.py`

| Feature | Descrizione |
|---------|-------------|
| `points_gap_to_top4`, `points_gap_to_relegation` | Distanza zone |
| `title_race_pressure`, `european_spot_pressure` | Pressione alto classifica |
| `relegation_pressure`, `mid_table_low_motivation` | Pressione basso classifica |
| `end_season_motivation_score` | Score composito |

---

## Flusso build

```
build_match_context(dataset, match, settings, enabled_feature_groups?)
    → compute tutti gli snapshot (con as_of anti-leakage)
    → build_full_feature_vector(partial)
    → filter_feature_vector(full, enabled_groups)
    → MatchContext con feature_vector filtrato
```

---

## Uso in modelli

- **FeatureModel** — usa `feature_vector` filtrato (softmax lineare)
- **Poisson/Dixon-Coles** — usano `TeamStrength`, optional lineup
- **Elo** — rating da storico
- **Ensemble** — combina tutti

---

## Anti-leakage

Tutte le feature storiche usano `dataset.finished_before(as_of)` o `team_history(team_id, as_of)` con `starting_at < as_of`.

Lineup/tactical mock:
- Backtest su partite finite → solo `data_availability = known_pre_match`
- Predict su partite future → solo `data_availability = forecast`
- Il match corrente non entra mai nel proprio storico

Tracciamento fonti: `data_sources.py` → usato in explain e status.

---

## Fase di sviluppo

Fase 2 (base) → Fase 2c (9 gruppi completi + ablation) → Fase 2d (gate pre-match lineup/tactical)
