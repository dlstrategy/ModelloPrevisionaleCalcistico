# Modulo 28 — Sportmonks Coach Mapping Prep (Fase 2l-b)

Preparazione tecnica per integrare dati coach reali Sportmonks in Fase 3 **senza chiamate API** in questa fase.

## Obiettivo

Definire il mapping tra risorse Sportmonks Football API v3 e le strutture interne:

- `CoachProfile` (`src/coaches/coach_registry.py`);
- `CoachAdaptationEstimate` (`src/coaches/coach_adaptation.py`);
- feature coach (`src/features/coach_features.py`);
- `coach_summary` in explain.

Riferimento documentazione locale: `docs/sportmonks-football-v3-docs.md`.

---

## Endpoint / risorse Sportmonks da mappare

### Endpoint coaches (base URL: `/v3/football/coaches`)

| Endpoint | Uso previsto |
|----------|--------------|
| GET All Coaches | Sync iniziale / cache registry |
| GET Coach by ID | Profilo singolo + includes |
| GET Coaches by Country ID | Scouting / fallback country |
| GET Coaches Search by Name | Risoluzione manuale |
| GET Last Updated Coaches | Incremental sync (ultime 2h) |

### Include su coach

| Include | Uso previsto |
|---------|--------------|
| `statistics.details` | MATCHES, WIN/DRAW/LOST, AVERAGE_POINTS_PER_GAME, SUBSTITUTIONS |
| `teams` | Storico squadre / leghe per prior experience |
| `latest` | Fixture ultimi 6 mesi → tenure proxy |
| `fixtures` | Cronologia partite coach |
| `trophies` | Opzionale — non usato in Fase 2l |
| `country` / `nationality` | `country_code`, `prior_country_code` |
| `player` | Link coach ↔ ex giocatore (id) |

### Include su fixture / team

| Include | Uso previsto |
|---------|--------------|
| `coaches` su **fixture** | Coach associato alla partita (as_of) |
| `coaches` su **team** | Coach corrente della squadra |

### Filtri statistiche coach

- `coachStatisticSeasons` — stats per stagione
- `coachStatisticDetailTypes` — tipi dettaglio (188, 214–216, 9676, 59, …)

---

## Mapping API → CoachProfile

| CoachProfile field | Fonte Sportmonks prevista | Diretto/Derivato | Note |
| ------------------ | ------------------------- | ---------------- | ---- |
| `coach_id` | `Coach.id` | **Diretto** | Chiave primaria |
| `coach_name` | `Coach.display_name` o `name` | **Diretto** | |
| `team_id` | Relazione team-coach corrente (fixture/team include) | **Derivato** | Da pivot team assignment |
| `league_id` | `Season.league_id` del team corrente | **Derivato** | Da contesto partita/stagione |
| `country_code` | `Coach.country_id` → lookup ISO | **Derivato** | Mappa country Sportmonks |
| `season_id` | `Season.id` attiva | **Derivato** | |
| `appointed_at` | Cronologia team-coach | **Derivato** | **Non campo nativo** coach base |
| `matches_in_charge` | `statistics.details` MATCHES (188) per season/team **o** conteggio fixture post-appointment | **Derivato** | Taglio as_of anti-leakage |
| `career_matches` | Somma MATCHES su seasons/teams storici | **Derivato** | |
| `career_ppg` | Media AVERAGE_POINTS_PER_GAME (9676) career | **Derivato** | |
| `team_ppg_before` | Punti squadra / match **prima** appointment | **Derivato** | Da fixture storiche team |
| `team_ppg_under_coach` | Punti squadra / match **sotto** coach | **Derivato** | Solo partite ≤ as_of |
| `goals_for_delta` | Delta gol fatti squadra before vs under | **Derivato** | Team statistics |
| `goals_against_delta` | Delta gol subiti before vs under | **Derivato** | Team statistics |
| `xg_delta` | Delta xG squadra before vs under | **Derivato** | Fixture/team xG stats — **non coach-native** |
| `xga_delta` | Delta xGA squadra before vs under | **Derivato** | Idem |
| `formation_changes_last_10` | Variazioni formazione ultime N partite | **Derivato** | Da lineup/fixture formations |
| `lineup_rotation_rate` | Share titolari cambiati tra match | **Derivato** | Da starting XI history |
| `preferred_style` | Proxy tattico (possession/pressing/…) | **Derivato** | **Non nativo** — euristica |
| `pressing_intensity` | Proxy da team/fixture pressing stats | **Derivato** | **Non nativo** |
| `defensive_line_height` | Proxy da tactical/lineup | **Derivato** | **Non nativo** |
| `prior_league_id` | Ultima lega diversa da `teams` history | **Derivato** | |
| `prior_country_code` | Country della lega prior | **Derivato** | |
| `prior_league_matches` | MATCHES in prior league | **Derivato** | |
| `prior_foreign_league_matches` | MATCHES cross-league | **Derivato** | |
| `same_country_experience_matches` | Somma match in leghe stesso paese | **Derivato** | |
| `cross_country_experience_matches` | Somma match cross-country | **Derivato** | |
| `new_manager_bounce_matches` | min(matches_in_charge, 8) se recente | **Derivato** | Logica interna |
| `data_confidence` | Regola composita (vedi sotto) | **Derivato** | |
| `source` | `"sportmonks_api"` / `"unknown_coach_fallback"` | **Derivato** | |

### Statistiche coach native (type IDs)

Da `coach-statistics.md`:

| ID | Code | Uso interno |
|----|------|-------------|
| 188 | MATCHES | `matches_in_charge`, `career_matches` |
| 214 | WIN | Performance sotto coach |
| 215 | DRAW | Idem |
| 216 | LOST | Idem |
| 9676 | AVERAGE_POINTS_PER_GAME | `career_ppg`, `team_ppg_under_coach` |
| 59 | SUBSTITUTIONS | Proxy rotazioni |
| 83–85 | Cartellini | Opzionale — non in Fase 2l |

---

## Campi diretti vs derivati vs non nativi

### Diretti o quasi diretti

- `coach_id`, `coach_name`, `country_id` (→ country_code)
- Coach statistics: MATCHES, WIN/DRAW/LOST, AVERAGE_POINTS_PER_GAME
- Relazione team corrente via include coaches
- Storico team via `teams` include

### Derivati internamente (Fase 3)

- Tenure, appointment date, PPG before/under, gol/xG deltas
- Formation changes, lineup rotation
- Prior league/country experience
- `CoachAdaptationEstimate` via `estimate_coach_adaptation()`
- Integration progress, early risk, potential signal via `coach_features.py`
- `data_confidence` composita

### Non disponibili direttamente su Sportmonks

- xG coach-specific (usare team xG)
- Pressing style / preferred_style nativo
- Formation changes aggregate per coach
- True appointment date (ricostruire da cronologia)
- Coach-rosa style compatibility (proxy tactical + mock fields)

---

## Strategia di calcolo futura (Fase 3)

1. **Associazione coach corrente:** `include=coaches` su fixture pre-match o team del match.
2. **Statistiche base:** `GET /coaches/{id}?include=statistics.details` filtrato per `coachStatisticSeasons`.
3. **Storico leghe:** `include=teams` + statistics per season → `prior_league_id`, cross-country counters.
4. **Tenure:** `include=latest` (6 mesi) o prima fixture dopo appointment stimato.
5. **PPG before/under:** walk fixture team con cutoff `as_of = match.starting_at`.
6. **Gol/xG deltas:** team statistics window before vs after appointment.
7. **Formation / rotation:** lineup history ultime 10 partite.
8. **Adaptation:** riusare `estimate_coach_adaptation()` con profilo popolato.
9. **Features / summary:** riusare `build_coach_features()` e `build_coach_summary()` invariati.
10. **Sync incrementale:** `GET Last Updated Coaches` + cache locale.

---

## Data confidence (regola futura)

| Condizione | Confidence indicativa |
|------------|----------------------|
| coach_id + team relation + season stats + team history | 0.70–0.90 |
| coach_id + MATCHES/PPG ma senza xG/style | 0.45–0.65 |
| coach noto, statistiche assenti | 0.20–0.35 |
| coach assente | 0.10 (`unknown_coach_fallback`) |

Cap aggiuntivi come in `UnknownCoachPolicy`: low sample, cross-country new coach, unknown origin.

---

## Anti-leakage Fase 3

Per ogni match storico o pre-match:

- Usare **solo dati disponibili a `as_of = match.starting_at`**.
- Non includere statistiche coach/team calcolate su partite future.
- `team_ppg_before` / `team_ppg_under_coach`: solo fixture con `starting_at < as_of`.
- `matches_in_charge`: conteggio partite squadra sotto coach fino ad as_of.
- `integration_progress` / tenure: calcolati alla data partita, non a oggi.
- Coach statistics cumulative: filtrare per season/stage e cutoff temporale se cumulative globali.
- Cambio allenatore: rilevare appointment prima di as_of; non usare performance post-match corrente.

---

## Limiti

- Sportmonks non espone tutti i segnali tattici/stilistici del mock attuale.
- Molti campi restano proxy o derivati — rischio confondere impatto coach e forza squadra.
- Appointment date e team-coach history possono essere incompleti.
- Serve validazione out-of-sample e ablation gruppo `coach` su dati reali.

---

## Collegamenti

- Implementazione mock: [27-coach-impact-league-adaptation-layer.md](27-coach-impact-league-adaptation-layer.md)
- Attivazione API: [13-fase-3-sportmonks-api.md](13-fase-3-sportmonks-api.md)
- Docs Sportmonks: `docs/sportmonks-football-v3-docs.md` (Coaches, Coach statistics)
