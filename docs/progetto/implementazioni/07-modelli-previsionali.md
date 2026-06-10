# 07 — Modelli previsionali

## Cosa è stato fatto

Quattro modelli base che trasformano `MatchContext` in `OutcomeProbabilities` (P(1), P(X), P(2)). Tutti implementano `BaseModel` con metodo `predict(context)`.

## Interfaccia comune

```python
# src/models/base.py
class BaseModel(ABC):
    name: str
    def predict(self, context: MatchContext) -> OutcomeProbabilities
```

## Modelli implementati

### 1. Poisson (`poisson.py`)

**Logica:**

1. Stima λ_home e λ_away da `TeamStrength` (attack vs defense avversario)
2. Applica `home_advantage` al λ casa
3. Costruisce matrice score P(i,j) con Poisson indipendente
4. Somma: i>j → P(1), i=j → P(X), i<j → P(2)

**Parametri:** `poisson_max_goals`, `home_advantage`

**Dipendenze:** `score_matrix.py` per calcolo matrice

### 2. Dixon-Coles (`dixon_coles.py`)

**Logica:**

Come Poisson, ma applica correzione τ (tau) su score bassi:

- (0,0), (1,0), (0,1), (1,1) — modifica dipendenza tra gol

Riduce sottostima pareggi e match low-scoring tipici del calcio.

**Parametri:** `dixon_coles_rho` (tipicamente negativo, es. -0.13)

### 3. Elo (`elo.py`, `elo_ratings.py`)

**Logica:**

1. `EloRatings` calcola rating pre-partita da storico (K-factor, home advantage)
2. Differenza rating → probabilità implicita vittoria
3. Distribuzione residua tra pareggio e vittoria trasferta

**Parametri:** `elo_k_factor`, `elo_home_advantage`, `elo_initial_rating`

**Nota:** Richiede `MatchDataset` intero per costruire rating progressivo.

### 4. Feature Model (`feature_model.py`)

**Logica:**

1. Legge `context.feature_vector` (dict chiave → float)
2. Score lineare: `z_k = Σ w_k * feature_k`
3. Softmax su [z_home, z_draw, z_away] → probabilità

Pesi iniziali hardcoded (non ancora training da backtest).

## Matrice score (`score_matrix.py`)

Utility condivisa da Poisson e Dixon-Coles:

- Genera P(home_goals=i, away_goals=j) per i,j ∈ [0, max_goals]
- Dixon-Coles applica fattore τ prima della normalizzazione

## Registry (`registry.py`)

```python
build_base_models(settings, dataset) → [Poisson, DixonColes, Elo, Feature]
get_model_by_name(name, settings, dataset) → BaseModel
```

## Collegamenti

```
MatchContext
    ├→ PoissonModel.predict()
    ├→ DixonColesModel.predict()
    ├→ EloModel.predict()      ← usa dataset storico
    └→ FeatureModel.predict()  ← usa feature_vector
            ↓
    OutcomeProbabilities (ognuno)
            ↓
    EnsembleModel (vedi doc 08)
```

## Confronto modelli

| Modello | Punto di forza | Limitazione |
|---------|----------------|-------------|
| Poisson | Semplice, interpretabile | Indipendenza gol |
| Dixon-Coles | Corregge low-score | ρ fisso, non calibrato |
| Elo | Dinamico nel tempo | Meno ricco di feature |
| Feature | Usa tutte le feature | Pesi non addestrati |

## Fase di sviluppo

Fase 1: Poisson
Fase 2: Dixon-Coles, Elo, Feature
