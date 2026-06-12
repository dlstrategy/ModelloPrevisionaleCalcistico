# 15 — Hardening foundation

## Obiettivo

Passaggio di hardening prima di nuove feature: correggere bug, rafforzare sync, test e CI.

---

## 1. Fix bug Elo

**File:** `src/models/elo.py`

```python
# Prima (bug):
p_away_beats = 1.0 - table.expected_score(ra, rh_adj)

# Dopo (corretto):
p_away_beats = table.expected_score(ra, rh_adj)
```

**Test:** `tests/test_elo.py` — strong home P(1)>P(2), strong away P(2)>P(1).

---

## 2. Sync API con partite future

**File:** `src/data_pipeline/sync.py`

| Finestra | Range |
|----------|-------|
| Passate | `today - 180` → `today` |
| Future | `today` → `today + 30` |

Merge con dedup per `match.id` via `_merge_matches()`.

Permette `predict --date` con dati API reali futuri.

**Test:** `tests/test_sync.py`

---

## 3. Normalize datetime robusto

**File:** `src/data_pipeline/normalize.py`

Supporta:
- `2025-09-20 20:45:00` (Sportmonks)
- ISO con timezone (`2025-09-20T18:45:00+00:00`, `...Z`)
- Solo data (`2025-09-20`)

Timezone convertiti in UTC naive.

**Test:** `tests/test_normalize.py`

---

## 4. Test client HTTP mockati

**File:** `tests/test_client.py`

- Header `Authorization`
- Retry su HTTP 429
- Errore HTTP 500
- Cache hit evita chiamata HTTP

---

## 5. GitHub Actions CI

**File:** `.github/workflows/ci.yml`

Trigger: push/PR su `main`  
Azione: `python -m pytest -q`

---

## Fase di sviluppo

Fase 2b — tra Fase 2 e Fase 2c feature engineering.
