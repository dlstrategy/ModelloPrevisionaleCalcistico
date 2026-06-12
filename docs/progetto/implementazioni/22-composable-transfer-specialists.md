# Modulo 22 — Composable Transfer Specialists

Fase **2h-b** — sistema ibrido per valutare trasferimenti cross-league.

## Problema combinatorio

Con N leghe servirebbero N×(N−1) specialisti direzionali se ogni coppia fosse hardcoded. Non scalabile.

## Architettura ibrida

```
PlayerCareer → PlayerSkillVector
                    ↓
LeagueProfile(source) + LeagueProfile(target)
                    ↓
         GeneralTransferAdapter (sempre disponibile)
                    ↓
         PairSpecialist? (solo se valido)
                    ↓
            TransferEstimate
```

| Componente | Modulo |
|------------|--------|
| LeagueProfile | `src/players/league_profiles.py` |
| PlayerSkillVector | `src/players/player_skill.py` |
| GeneralTransferAdapter | `src/players/general_transfer_adapter.py` |
| PairSpecialist | `src/players/pair_specialists.py` |
| ComposableResolver | `src/players/composable_transfer.py` |
| SpecialistLearning | `src/players/specialist_learning.py` |

## Tipi adapter

| `adapter_type` | Quando |
|----------------|--------|
| `same_league` | Snapshot già nella lega target |
| `general_adapter` | Cross-league, nessuno specialista valido |
| `pair_specialist` | Coppia direzionale con dati sufficienti |
| `unknown_player` | Giocatore assente dal registry |

## Validità PairSpecialist

- `sample_size >= 20`
- `reliability >= 0.55`
- Direzionale: Liga→Serie A ≠ Serie A→Liga
- Role-specific prevale su role `None`

## Aggiornamento futuro

`specialist_learning.py` aggrega `TransferOutcomeObservation`:

- predicted vs observed rating
- `rating_multiplier` clampato 0.75..1.15
- `reliability` da sample size e varianza
- `learned_version = 2h-b.1`

Non scrive automaticamente su fixture production.

## CLI read-only

```bash
python -m src.cli transfer-estimate --player-id 1006 --target-league 384 --role forward
python -m src.cli transfer-estimate --player-id 1006 --target-league 384 --json
```

## Limiti

- Profili lega e coefficienti **mock/proprietari**
- Fixture offline, nessun dato Sportmonks reale
- Non validato statisticamente
- **Output match invariato**: P(1), P(X), P(2), pick, confidence

## Retrocompatibilità

`transfer_adaptation.py` (Fase 2h) resta per test legacy. `player_value.py` usa il composable resolver.
