# Modulo 27 — Coach Impact, League Adaptation & Integration Layer

Fase **2l** — layer prudente per impatto allenatore, adattamento lega/paese e inserimento nel gruppo.

## Obiettivo

Stimare in modo **conservativo** e **spiegabile** l'impatto dell'allenatore sul modello 1/X/2, senza rating assoluti inventati e senza cambiare l'output match.

## Perché layer coach separato da tactical

Il gruppo **tactical** copre formazione e duelli di stile in partita. L'impatto coach include tenure, cambio recente, adattamento cross-lega, rotazioni, compatibilità rosa, tempo di inserimento e confidence dei dati — dimensioni manageriali non riducibili al matchup tattico statico.

## Differenza impatto / adattamento / potenziale

| Concetto | Significato |
|----------|-------------|
| **Impatto osservato** | Delta PPG, gol, xG/xGA sotto coach vs prima |
| **Adattamento** | Trasferibilità esperienza da lega/paese precedente |
| **Potenziale (signal)** | Combinazione prudente di segnali osservabili, attenuata da confidence — **non** un rating assoluto |

## Feature create (~68)

**Per squadra:** tenure, recent change, bounce, delta PPG/attack/defense/xG/xGA, tactical stability, rotation, confidence, unknown/low_sample flags, adaptation (same league/country/cross-country, score, confidence, integration matches/progress, early risk), style fit, potential signal.

**Differenziali (18):** tenure, deltas, stability, rotation, confidence, unknown, low sample, adaptation, integration, early risk, style fit, potential.

Gruppo feature: **`coach`**. Disabilitato in profilo `base`; abilitato in `advanced` / `all_in_no_predictions` se fixture `coach_profiles.json` presente.

## Unknown coach

- `coach_id=None`, `matches_in_charge=0`, `data_confidence=0.10`
- `potential_signal=0.50`, `adaptation_score=0.50`
- Nessun boost né penalità forte
- Explain: warning "allenatore sconosciuto"

## Low sample coach

- Flag se `matches_in_charge < 10` o `career_matches < 30`
- Confidence cap ~0.30
- `potential_signal` attenuato verso 0.50

## Recent coach change

- `recent_coach_change=1` se `matches_in_charge < 5`
- `new_manager_bounce_signal` capped a 0.20, attenuato da confidence

## Cambio campionato / paese

- **Same league:** adaptation score alto, integration breve
- **Same country, different league:** adaptation medio-alto
- **Cross country:** adaptation prudente, integration lunga, early risk più alto
- **Origine sconosciuta / lega esotica:** neutro 0.50, confidence bassa

## Tempo di inserimento

`integration_progress = clamp(matches_in_charge / expected_integration_matches, 0, 1)`

`early_adaptation_risk` deriva da `1 - progress`, modulato per same_league/cross_country e confidence. Non equivale a "coach scarso".

## Style fit coach/rosa

Confronto prudente `pressing_intensity` / `defensive_line_height` coach vs segnali tactical. Se dati insufficienti o tactical fallback: **0.50** + confidence bassa.

## FeatureModel statico

**Non modificato** in questa fase — nessun peso coach aggiunto. Le feature entrano nel vector ma il modello statico le ignora (chiavi non in pesi).

## FeatureTrained

Può usare le feature coach dopo training walk-forward. Policy **compact** include solo 13 diff coach robusti.

## Compact policy

Subset diff: `coach_ppg_delta_diff`, `coach_attack_delta_diff`, `coach_defense_delta_diff`, `coach_tactical_stability_diff`, `coach_confidence_diff`, `unknown_coach_diff`, `low_sample_coach_diff`, `coach_adaptation_score_diff`, `coach_adaptation_confidence_diff`, `coach_integration_progress_diff`, `coach_early_adaptation_risk_diff`, `coach_style_fit_diff`, `coach_potential_signal_diff`.

## Fixture mock

`tests/fixtures/coaches/coach_profiles.json` — 9 profili (team 1–5, 7–10); team 6 assente → unknown fallback.

## Limiti

- Solo dati mock, nessuna API reale
- Coach impact difficile da isolare dalla forza squadra
- Cambio paese/campionato non calibrato su dataset reale
- Style fit approssimato con segnali tactical disponibili
- Serve dataset reale (Fase 3) per validazione out-of-sample

## Prossimo step

- Training feature_trained con ablation gruppo coach
- Promotion gate dopo walk-forward con coach attivo
- Integrazione dati coach reali da Sportmonks (Fase 3)
- Calibrazione adaptation score su storico cambi allenatore

## Mapping Sportmonks (Fase 3)

Documentazione locale: `docs/sportmonks-football-v3-docs.md` (Coaches, Coach statistics).

| Campo mock / feature | Fonte API prevista |
|----------------------|-------------------|
| `matches_in_charge`, PPG | `statistics.details` — MATCHES (188), AVERAGE_POINTS_PER_GAME (9676), WIN/DRAW/LOST |
| Rotazioni | SUBSTITUTIONS (59) o derivato da lineup |
| Tenure / appointed | `teams` include su coach + `latest` fixtures (6 mesi) |
| Cross-league experience | `teams` / `statistics` per season + `country_id` |
| xG / style / formation | **Non nativi** — derivare da fixture statistics o mantenere proxy |

Endpoint: `GET /v3/football/coaches/{id}?include=statistics.details;teams;latest` e `include=coaches` su fixture/team.
