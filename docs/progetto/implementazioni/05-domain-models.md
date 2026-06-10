# 05 — Modelli di dominio

## Cosa è stato fatto

Entità calcistiche **indipendenti** da Sportmonks e dai modelli statistici. Rappresentano il "linguaggio comune" di tutto il sistema.

## Moduli

| File | Contenuto |
|------|-----------|
| `src/domain/enums.py` | Enum (es. stato partita) |
| `src/domain/team.py` | `Team` |
| `src/domain/player.py` | `Player` |
| `src/domain/match.py` | `Match`, partecipanti, score |
| `src/domain/models.py` | `OutcomeProbabilities`, `Prediction` |

## Entità principali

### `Match`

Rappresenta una partita con:

- Identificativi (`id`, `league_id`, `season_id`)
- `starting_at` (datetime UTC)
- Partecipanti home/away (`MatchParticipant`)
- Score opzionale (`home_score`, `away_score`)
- Stato (`finished`, `scheduled`, ecc.)

### `OutcomeProbabilities`

```python
home_win: float   # P(1)
draw: float       # P(X)
away_win: float   # P(2)
```

Con validazione: somma = 1, tutti ≥ 0.

Metodi: `normalized()`, `pick()`, `confidence()` (max delle tre probabilità).

### `Prediction`

Output finale per una partita:

- Riferimento al `Match`
- `OutcomeProbabilities`
- `model_name`
- `pick` (1, X, 2)
- `confidence`
- `explanation` opzionale (dict da `explain.py`)

## Perché un layer dominio separato

1. **normalize.py** traduce Sportmonks → dominio
2. **Modelli** consumano `MatchContext` (che contiene `Match`)
3. **CLI/JSON export** serializza `Prediction`
4. Cambio provider API non tocca modelli né feature

## Collegamenti

```
Sportmonks JSON
      ↓ normalize.py
   Match, Team
      ↓ match_context.py
   MatchContext
      ↓ models/*.py
   OutcomeProbabilities
      ↓ predict_match.py
   Prediction
```

## Fase di sviluppo

Fase 1 — foundation
