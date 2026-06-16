# 18 — Data Capability Layer e fallback intelligenti

## Perché esiste

Prima dell'attivazione dell'API Sportmonks reale (Serie A tra mesi), il motore deve funzionare con **diversi livelli di dati disponibili** senza crashare e senza fingere di avere fonti non collegate.

Il **Data Capability Layer** (`src/data_capabilities/`) centralizza:

- quali capability dati sono attese per profilo;
- quali gruppi feature sono abilitati, disabilitati o in fallback;
- un **data completeness score** (0–1) per monitorare la copertura reale.

## Profili supportati

| Profilo | Uso |
|---------|-----|
| `base` | Dati standard senza add-on avanzati (default) |
| `advanced` | Base + xG, shots, tactical, coach, historical |
| `all_in_no_predictions` | Pacchetto completo tranne Predictions/Odds |

Configurazione: `DATA_PROFILE=base` in `.env` (valori validi: `base`, `advanced`, `all_in_no_predictions`).

## Policy progetto

- **PREDICTIONS** e **ODDS** esistono come capability ma sono **sempre disabilitate per policy**.
- Non usiamo Sportmonks Predictions add-on né quote per influenzare il modello.
- Non aumentano lo completeness score.

## Gestione dati mancanti

| Gruppo | Se capability assente |
|--------|------------------------|
| xG | Gruppo disabilitato o proxy; explain trasparente |
| Shots | Stesso comportamento di xG |
| Player lineup | Fallback neutro (`default_neutral_lineup`) |
| Tactical | Default tactical fallback |
| Coach | Gruppo disabilitato (profilo `base`) o `unknown_coach_fallback` se profilo attivo ma coach assente |
| Calendar | `basic_rest_days` o neutral fatigue |
| Motivation | Neutral motivation se standings assenti |

Con profilo `base`, xG/shots/tactical/coach avanzato **non attesi** → nessun errore in validate.

## Data completeness score

- Tra **0 e 1**.
- Penalizza solo capability **attese dal profilo** ma assenti.
- Non penalizza `base` per mancanza di xG o pressure index (non attesi).
- Ogni fallback attivo abbassa leggermente lo score (~0.02 per fallback).
- Profilo `base` con fixture offline complete: tipicamente **0.85–1.0**.

## Comandi CLI

```bash
python -m src.cli capabilities --profile base
python -m src.cli capabilities --profile advanced
python -m src.cli status --league 384
python -m src.cli validate --league 384 --profile base
python -m src.cli predict --date 2025-10-18 --model ensemble --explain
```

## Esempio output `capabilities --profile base`

```text
Data capabilities — profile: base

Available:
  CORE_FIXTURES             OK
  STANDINGS                 OK
  ...

Disabled by project policy:
  PREDICTIONS               disabled
  ODDS                      disabled

Feature groups:
  xg                         disabled_or_fallback
  calendar                   enabled

Data completeness score: 0.91
```

## Integrazione

- **`status`**: mostra profilo, score, feature groups, policy disabled.
- **`validate --profile`**: controlli xG/shots/tactical solo se attesi dal profilo; JSON report con `data_completeness`.
- **`predict --explain`**: JSON con `data_profile`, `data_completeness`, warnings leggibili.

Output predizione invariato: **P(1), P(X), P(2), pick, confidence** only.

Gli edge mostrati in explain rispettano i feature group abilitati dal profilo. Se un gruppo è disabilitato, il relativo edge viene omesso (`null`) e marcato in `edge_status` come `disabled_by_profile`, per evitare explain fuorvianti.

## Moduli

```
src/data_capabilities/
  capabilities.py   # enum DataCapability
  profiles.py       # profili base / advanced / all_in_no_predictions
  requirements.py   # FEATURE_REQUIREMENTS per gruppo
  resolver.py       # detect + resolve + score
  report.py         # DataCompletenessReport
```
