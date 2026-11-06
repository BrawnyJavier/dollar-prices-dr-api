"""Small API serving USD/DOP rates scraped from infodolar.com.do.

Run:  uvicorn app:app --reload
"""

from __future__ import annotations

import os
import threading
import time
import unicodedata

from fastapi import FastAPI, HTTPException, Query

import scraper

CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "300"))

app = FastAPI(title="Dollar Prices DR", version="1.0.0")

_cache: dict = {"data": None, "ts": 0.0}
_lock = threading.Lock()


def get_rates(force: bool = False) -> dict:
    with _lock:
        fresh = _cache["data"] is not None and time.time() - _cache["ts"] < CACHE_TTL
        if fresh and not force:
            return _cache["data"]
        try:
            data = scraper.fetch()
        except Exception as exc:
            if _cache["data"] is not None:  # serve stale data rather than fail
                return {**_cache["data"], "stale": True, "error": str(exc)}
            raise HTTPException(status_code=502, detail=f"Failed to fetch source: {exc}")
        _cache.update(data=data, ts=time.time())
        return data


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "-".join(text.lower().split())


@app.get("/")
def root():
    return {
        "endpoints": {
            "/rates": "All entities plus the InfoDolar average",
            "/rates/average": "InfoDolar average buy/sell",
            "/rates/best": "Best place to buy USD (lowest sell) and to sell USD (highest buy)",
            "/rates/{entity}": "One entity, e.g. /rates/banco-bhd or /rates/bhd",
        },
        "cache_ttl_seconds": CACHE_TTL,
    }


@app.get("/rates")
def rates(refresh: bool = Query(False, description="Bypass the cache")):
    return get_rates(force=refresh)


@app.get("/rates/average")
def average():
    data = get_rates()
    if not data["average"]:
        raise HTTPException(404, "Average not available")
    return data["average"]


@app.get("/rates/best")
def best():
    entities = get_rates()["entities"]
    buyers = [e for e in entities if e["buy"]]
    sellers = [e for e in entities if e["sell"]]
    return {
        # Where you get the most pesos for your dollars
        "best_to_sell_usd": max(buyers, key=lambda e: e["buy"], default=None),
        # Where dollars cost the fewest pesos
        "best_to_buy_usd": min(sellers, key=lambda e: e["sell"], default=None),
    }


@app.get("/rates/{entity}")
def entity(entity: str):
    wanted = _slug(entity)
    for e in get_rates()["entities"]:
        if _slug(e["name"]) == wanted:
            return e
    matches = [e for e in get_rates()["entities"] if wanted in _slug(e["name"])]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise HTTPException(409, {"error": "Ambiguous entity", "matches": [m["name"] for m in matches]})
    raise HTTPException(404, f"Entity '{entity}' not found")
