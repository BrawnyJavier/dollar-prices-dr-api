# Dollar Prices DR

A small API that serves USD → DOP exchange rates for banks and exchange houses in the Dominican Republic, scraped from [infodolar.com.do](https://www.infodolar.com.do/).

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/uvicorn app:app --reload
```

The API runs at http://localhost:8000. Interactive docs are at http://localhost:8000/docs.

To print the scraped data once without starting the server:

```bash
.venv/bin/python scraper.py
```

## Endpoints

| Method & path | Description |
|---|---|
| `GET /` | List of endpoints |
| `GET /rates` | All entities plus the InfoDolar average. Add `?refresh=true` to bypass the cache. |
| `GET /rates/average` | InfoDolar average buy/sell |
| `GET /rates/best` | Best place to sell USD (highest buy) and to buy USD (lowest sell) |
| `GET /rates/{entity}` | A single entity by name, e.g. `/rates/banco-bhd` or just `/rates/bhd` |

Entity lookup ignores case and accents and accepts partial names. A partial name matching several entities returns `409` with the list of matches; no match returns `404`.

### Example response

`GET /rates/bhd`

```json
{
  "name": "Banco BHD",
  "buy": 57.95,
  "sell": 61.4,
  "spread": 3.45,
  "variation_pct": 0.0,
  "updated_at": "2026-11-06T18:00:00-04:00",
  "url": "https://www.infodolar.com.do/precio-dolar-entidad-banco-bhd.aspx"
}
```

- `buy`: pesos the entity pays you per dollar
- `sell`: pesos the entity charges you per dollar
- `spread`: `sell - buy`
- `variation_pct`: daily change, in percent
- `updated_at`: when the entity last updated its rate, as reported by the site

Any field the site doesn't show for an entity is `null`. Some entities publish only a buy or only a sell price.

## Configuration

| Env var | Default | Description |
|---|---|---|
| `CACHE_TTL_SECONDS` | `300` | How long scraped results are cached |

If a fetch fails and cached data exists, the API returns the cached data with `"stale": true` and an `"error"` message. If nothing is cached yet, it returns `502`.

## Notes

- The scraper reads the page's HTML tables (`#DolarPromedio` and `#Dolar`), so changes to the site's layout can break it. If that happens, `/rates` returns `502` with a "page layout may have changed" message.
- The data belongs to infodolar.com.do. Keep the cache on to avoid sending the site unnecessary traffic.
