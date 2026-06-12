# Modulo 24 — Player Identity, New Players & Transfers Flow (Audit)

Fase **2i-audit** — documentazione tecnica del flusso giocatori/trasferimenti **senza refactor invasivo**.

## Scopo

Descrivere esattamente come il programma (offline, fixture mock) gestisce:

- giocatori nuovi o sconosciuti;
- giocatori noti senza storico nella lega target;
- trasferimenti cross-league;
- campionati non coperti dai profili;
- pochi minuti / sample basso;
- ruoli alias o non riconosciuti;
- scelta tra `same_league`, `general_adapter`, `pair_specialist`, `unknown_player`.

## File coinvolti

| Area | File |
|------|------|
| Registry | `src/players/global_registry.py` |
| Entry point | `src/players/player_value.py` |
| Resolver | `src/players/composable_transfer.py` |
| Policy | `src/players/unknown_player_policy.py` |
| Adapter generico | `src/players/general_transfer_adapter.py` |
| Specialisti coppia | `src/players/pair_specialists.py` |
| Skill vector | `src/players/player_skill.py` |
| Profili lega | `src/players/league_profiles.py` |
| Legacy coeff | `src/players/transfer_adaptation.py` (non usato dal composable resolver) |
| Learning offline | `src/players/specialist_learning.py` |
| Lineup aggregate | `src/features/transfer_lineup_features.py` |
| Context | `src/features/match_context.py`, `src/features/data_sources.py` |
| CLI | `src/cli.py` (`transfer-estimate`) |
| Fixture | `tests/fixtures/players/player_careers.json`, `league_profiles.json`, `pair_transfer_specialists.json` |

---

## 1. Identificazione giocatore

- **Chiave primaria:** `player_id` intero **globale** (non per-league).
- **Caricamento:** `load_player_careers()` legge `tests/fixtures/players/player_careers.json` → `dict[int, PlayerCareer]`.
- **Struttura:** ogni `PlayerCareer` contiene N `PlayerLeagueSnapshot` (una riga per lega/stagione mock).
- **Collegamento cross-league:** stesso `player_id` con snapshot in leghe diverse (es. 1002 in Liga 564 e Serie A 384).
- **API pubblica:** `resolve_player_value_for_league(player_id, target_league_id, ...)` → dict con `rating`, `confidence`, `source` (adapter_type), `notes`.

---

## 2. Flow completo (testuale)

```
Input: player_id + target_league_id + optional role + optional target_matches_played
↓
load_player_careers() + load_league_profiles()
↓
player_id presente nel registry E snapshots non vuoti?
│ NO → unknown_player_estimate
│      rating=0.50, confidence=0.10
│      notes: unknown_player, player_not_in_career_registry, neutral_rating_low_confidence
↓ SÌ
get_player_snapshot_for_league(player_id, target_league_id)
↓
Esiste snapshot nella target league?
│ SÌ → skill_from_snapshot(same_league)
│      estimate_transfer_with_general_adapter(source=target, target=target)
│      adapter_type = same_league
│      apply_transfer_hardening (low minutes, unknown league, role)
↓ NO
get_best_available_snapshot(player_id, before_league_id=target)
  (euristica: max per minutes, rating — NON cronologico)
↓
Nessuno snapshot utilizzabile?
│ SÌ → unknown_player_estimate
↓ NO
skill_from_snapshot(origin)
resolve_role: input role → normalize_role → snapshot position → skill.role
get_league_profile(origin.league_id) + get_league_profile(target_league_id)
estimate_transfer_with_general_adapter → base (adapter_type=general_adapter)
find_best_specialist(origin→target, role)
│ specialist valido (sample≥20, reliability≥0.55)?
│ SÌ → apply_pair_specialist → adapter_type=pair_specialist
│ NO → resta general_adapter
apply_transfer_hardening(cross_league_transfer=True)
  notes += known_player_unknown_target_league
  cap confidence se unknown_source_league / low_sample / unknown_role
↓
TransferEstimate → resolve_player_value_for_league() dict
```

---

## 3. I quattro adapter_type

### `same_league`

- Snapshot esiste nella lega target.
- Rating = `skill_vector.overall` (rating/10 normalizzato 0..1).
- Confidence = `skill_vector.sample_confidence` (già modulata da minuti).
- Nessun adattamento cross-league.

### `general_adapter`

- Giocatore noto, snapshot solo in altra lega (o lega non coperta).
- `context_distance` tra profili lega → `rating_factor = 1 - min(distance*0.20, 0.20)`.
- Confidence = `sample_confidence × source_profile.confidence × target_profile.confidence × (0.70 + 0.30×adaptation)`.
- Se lega origine/target assente da `league_profiles.json` → `fallback_league_profile`, cap confidence 0.25.

### `pair_specialist`

- Dopo `general_adapter`, se esiste specialist valido in `pair_transfer_specialists.json`.
- Chiave: `{source}->{target}:{role}` (es. `564->384:forward`).
- Role-specific vince su general (`564->384:any`).
- Applica `rating_multiplier` e `confidence_multiplier` sul base estimate.

### `unknown_player`

- `player_id` assente dal registry **oppure** career con `snapshots: []` (es. 1004).
- Rating neutro **0.50**, confidence **0.10**.
- Nessuna penalità inventata oltre al neutro esplicito.

---

## 4. Policy unknown player

Definita in `UnknownPlayerPolicy` (`unknown_player_policy.py`):

| Parametro | Valore default |
|-----------|----------------|
| `neutral_rating` | 0.50 |
| `default_confidence` | 0.10 |
| `low_minutes_threshold` | 300 minuti |
| `low_minutes_confidence_cap` | 0.30 |
| `low_sample_confidence_threshold` | 0.30 |
| `low_sample_confidence_cap` | 0.30 |
| `unknown_league_confidence_cap` | 0.25 |
| `unknown_role_confidence_penalty` | -0.05 |

**Principio:** il modello deve sapere che la stima è incerta, non assumere che il giocatore sia scarso.

---

## 5. Policy low sample

Trigger in `apply_transfer_hardening`:

- `snapshot.minutes < 300` → note `low_sample_minutes`, confidence cap 0.30.
- `snapshot.sample_confidence < 0.30` → note `low_sample_confidence`, `low_sample_player`, cap 0.30.
- **Rating non abbassato** — solo confidence ridotta.

Esempio: player 1005 ha rating alto (0.85) ma confidence ~0.22 per pochi minuti.

---

## 6. Policy unknown league

- Lega assente da `league_profiles.json` → `get_league_profile()` restituisce profilo fallback (strength 0.50, confidence 0.35).
- Note: `fallback_league_profile`, spesso `unknown_source_league`.
- Confidence cap 0.25 (sia in general_adapter che in hardening).

Esempio: player 1003 da lega 999 (non in profili) verso Serie A 384.

---

## 7. Normalizzazione ruoli

`normalize_role()` in `player_skill.py`:

| Input alias | Canonico |
|-------------|----------|
| FW, ST, CF | forward |
| AM, CM, DM, MF | midfielder |
| CB, FB, DF | defender |
| GK | goalkeeper |
| forward/midfielder/defender/goalkeeper (lowercase) | invariato |
| altro (es. WINGBACK) | `None` → note `unknown_role`, confidence -0.05 |

Gli alias servono a trovare pair specialist role-specific (es. FW → `564->384:forward`).

---

## 8. Esempi concreti (fixture mock, target Serie A 384)

Generati con `python -m src.cli transfer-estimate --json`.

| Caso | player_id | adapter | rating | confidence | specialist_key | Note principali |
|------|-----------|---------|--------|------------|----------------|-----------------|
| Same league stabile | 1001 | same_league | 0.74 | ~0.92 | — | FW, 2800 min, Serie A |
| Same league pochi minuti | 1005 | same_league | 0.85 | ~0.22 | — | low_sample_minutes, low_sample_confidence |
| Same league (già in target) | 1002 | same_league | 0.71 | ~0.36 | — | Usa snapshot 384 (450 min), non Liga |
| Liga → Serie A + specialist | 1006 | pair_specialist | ~0.70 | ~0.32 | 564->384:forward | general_adapter + pair_specialist, known_player_unknown_target_league |
| Lega non coperta (999) | 1003 | general_adapter | ~0.77 | ~0.11 | — | fallback_league_profile, unknown_source_league |
| Sconosciuto (assente registry) | 99999 | unknown_player | 0.50 | 0.10 | — | unknown_player, neutral_rating_low_confidence |
| In registry, zero snapshot | 1004 | unknown_player | 0.50 | 0.10 | — | Stesso trattamento di sconosciuto |

Comando role alias:

```bash
python -m src.cli transfer-estimate --player-id 1006 --target-league 384 --role FW --json
# → source: pair_specialist, specialist_key: 564->384:forward
```

---

## 9. Integrazione lineup features (Fase 2i)

Modulo `src/features/transfer_lineup_features.py`:

- Per ogni `player_id` in `starting_xi_player_ids` (fixture lineups) chiama `resolve_player_value_for_league()`.
- Aggrega 27 feature conservative nel gruppo **`player_lineup`**: avg rating/confidence, share unknown/low_sample/cross-league/pair_specialist/general_adapter, diff home-away.
- Se lineup manca → rating neutro 0.50, `missing_player_share=1.0`.
- Integrato in `build_full_feature_vector()`; filtrato se `player_lineup` disabilitato.

**Cosa influenza oggi le prediction:**

| Componente | Impatto predizioni match |
|------------|-------------------------|
| `transfer-estimate` CLI | Nessuno — solo diagnostica |
| `transfer_lineup_features` | Solo se modello usa quelle chiavi nel feature vector |
| Poisson / Dixon-Coles / Elo | **No** — non leggono player transfer |
| FeatureModel (pesi statici) | **No** — non include le 27 chiavi transfer-aware |
| FeatureTrainedModel | Potenziale se ri-addestrato; **fuori ensemble e --all-models** |

Output match resta: **P(1), P(X), P(2), pick, confidence**.

---

## 10. Limiti attuali

- Dati **mock** (`player_careers.json`, profili lega, specialisti).
- **Nessuna API Sportmonks** reale.
- `get_best_available_snapshot` **non cronologico** (max minutes/rating, non latest season).
- Coefficienti transfer e profili lega **non calibrati** out-of-sample.
- Specialisti mock con sample/reliability fissi.
- Player 1004 in registry ma vuoto → trattato come unknown (non distinto da 99999).
- Validazione statistica cross-league assente.
- Rischio overfitting se `feature_trained` include transfer features con pochi match.

---

## 11. Prossimi step consigliati

1. Snapshot **cronologici** (season_id / transfer_date) in `get_best_available_snapshot`.
2. Calibrazione profili lega e specialisti su dataset reale (Fase 3).
3. Distinzione esplicita "nuovo in rosa" vs "sconosciuto totale".
4. Regularization / feature selection per `feature_trained` con transfer lineup features.
5. XI completi con ID globali da Sportmonks (quando API attiva, senza Predictions/Odds).

---

## Test audit

File: `tests/test_player_transfer_flow_audit.py`

Copre: unknown, same_league, pair_specialist Liga→Serie A, role alias FW, unknown source league, low sample, output bounded, CLI JSON.

Vedi anche: [22-composable-transfer-specialists.md](22-composable-transfer-specialists.md), [23-transfer-aware-lineup-features.md](23-transfer-aware-lineup-features.md).
