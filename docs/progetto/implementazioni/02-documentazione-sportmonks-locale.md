# 02 — Documentazione Sportmonks locale

## Cosa è stato fatto

Sistema per scaricare e consultare offline tutta la documentazione **Sportmonks Football API v3**, usata come unica fonte di verità per endpoint, parametri e campi.

## File

| File | Descrizione |
|------|-------------|
| `scripts/fetch_sportmonks_docs.py` | Script di download, bundling e catalogo |
| `docs/sportmonks-football-v3-docs.md` | Bundle unico con **367 pagine** Markdown |
| `docs/sportmonks-football-v3-pagine.md` | **Catalogo completo** di tutte le pagine (titolo, URL, categoria) |
| `docs/sportmonks-llms-index.md` | Indice `llms.txt` originale salvato in locale |
| `.cursor/rules/sportmonks.mdc` | Regole Cursor per l'IDE |

## Flusso dello script

```
1. GET https://docs.sportmonks.com/llms.txt
2. Estrae la sezione "Football API 3.0" (367 URL)
3. Esclude Motorsport, Odds, Core, Widgets, Beta
4. Per ogni URL: scarica pagina Markdown
5. Concatena in docs/sportmonks-football-v3-docs.md
6. Genera docs/sportmonks-football-v3-pagine.md (catalogo categorizzato)
```

## Catalogo pagine (367 totali)

Il file [`docs/sportmonks-football-v3-pagine.md`](../../sportmonks-football-v3-pagine.md) elenca **ogni pagina** inclusa nel bundle, con:

- Numero progressivo (1–367)
- Titolo (da `llms.txt`)
- URL sorgente
- Categoria (es. `endpoints/fixtures`, `endpoints/standings`, `welcome`, `api`)
- Stato download (`ok` / `failed`)

### Categorie principali

| Categoria | Pagine | Rilevanza progetto |
|-----------|--------|-------------------|
| `welcome` | 11 | Setup, auth, best practices |
| `api` | 18 | Syntax, includes, filters, rate limit |
| `endpoints/fixtures` | 13 | Sync partite (Fase 3) |
| `endpoints/leagues` | 9 | Season corrente Serie A |
| `endpoints/standings` | 7 | Classifica ufficiale |
| `endpoints/teams` | 10 | Dati squadra |
| `endpoints/players` | 6 | Metriche giocatori |
| `endpoints/expected-xg` | 3 | xG per feature |
| `endpoints/statistics` | 4 | Statistiche partita |
| `definitions/types` | 17 | Tipi dati API |
| `tutorials-and-guides/*` | 80+ | Guide integrazione |

**Nota:** Il bundle include anche pagine su odds, predictions e premium feed (documentazione di riferimento), ma il motore previsionale **non le usa** — produce solo 1/X/2 proprietario.

## Scelta tecnica: urllib + certifi

Su Windows con Python da Microsoft Store, `requests`/`httpx` fallivano con errori SSL. Lo script usa `urllib.request` con certificati da `certifi`.

## Regole Cursor (`.cursor/rules/sportmonks.mdc`)

Vincoli imposti all'assistente IDE:

- Consultare **solo** la documentazione locale
- Autenticazione: header `Authorization` (no query `api_token`)
- Output previsioni: **solo** 1/X/2
- Non usare add-on Predictions Sportmonks

## Collegamenti

```
fetch_sportmonks_docs.py → docs/sportmonks-football-v3-docs.md
                                    ↓
              sportmonks/endpoints.py, client.py, fixtures.py, ...
                                    ↓
                         .cursor/rules/sportmonks.mdc
```

## Uso

```bash
# Download completo + bundle + catalogo
python scripts/fetch_sportmonks_docs.py

# Solo rigenerare il catalogo da indice/bundle locale (veloce)
python scripts/fetch_sportmonks_docs.py --catalog-only
```

## Fase di sviluppo

Fase 0b — prima dell'implementazione del motore (vedi [CRONOSTORIA.md](../CRONOSTORIA.md))
