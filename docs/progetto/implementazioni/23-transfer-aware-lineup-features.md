# Modulo 23 — Transfer-aware Lineup Features

Fase **2i** — feature aggregate transfer-aware nel gruppo `player_lineup`.

## Obiettivo

Usare il layer giocatori/trasferimenti (2h–2h-c) a livello squadra quando la lineup è disponibile, **senza** valutazioni aggressive sui singoli giocatori e **senza** cambiare l'output match.

## Perché feature aggregate

Il modello deve sapere che la lineup è incerta, non assumere automaticamente che sia scarsa. Rating e confidence restano separati: confidence bassa segnala incertezza senza penalizzare il rating in modo inventato.

## Nuove feature (27)

**Per squadra (20):** avg rating/confidence transfer-aware, share unknown/low_sample/cross_league/pair_specialist/general_adapter/unknown_league/unknown_role/missing.

**Differenziali (7):** diff rating, confidence, e share principali home-away.

Tutte nel gruppo **`player_lineup`** — non compaiono se il profilo disabilita quel gruppo.

## Gestione casi

| Caso | Comportamento |
|------|---------------|
| Player assente registry | unknown_player_share ↑, confidence ↓ |
| Low sample | low_sample_player_share ↑, confidence cap ~0.30 |
| Cross-league | cross_league_share ↑; pair_specialist o general_adapter |
| Lega origine sconosciuta | unknown_league_share + fallback profile |
| Lineup senza player_id | missing_player_share=1.0, rating neutro 0.50 |

Fixture: campo opzionale `starting_xi_player_ids` in `league_*_lineups.json`.

## Output match

Invariato: **P(1), P(X), P(2), pick, confidence**. Le nuove feature entrano solo nel feature vector interno.

## Explain

Sezione `transfer_lineup_summary` con avg_rating, avg_confidence, share home/away.

## Limiti

- Dati mock; pochi XI con player_id espliciti
- Coefficienti transfer non calibrati
- Non validato out-of-sample
- Rischio overfitting feature_trained con ~40 match

## Prossimo step

- Regularization/compact per feature_trained
- Calibrazione su dataset reale (Fase 3)
- XI completi da Sportmonks con ID globali
