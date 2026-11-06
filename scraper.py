"""Scrape USD -> DOP exchange rates from infodolar.com.do."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup, Tag

SOURCE_URL = "https://www.infodolar.com.do/"
USER_AGENT = "Mozilla/5.0 (compatible; dollar-prices-dr/1.0)"

_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


def _parse_money(text: str) -> float | None:
    """'$61.28' -> 61.28; blank or placeholder -> None."""
    match = _NUMBER.search(text.replace(",", ""))
    return float(match.group()) if match else None


def _own_text(td: Tag) -> str:
    """Text of a cell excluding nested spans (which hold the daily change)."""
    return "".join(s for s in td.find_all(string=True, recursive=False)).strip()


def _parse_row(tr: Tag) -> dict | None:
    name_el = tr.select_one("td.colNombre .nombre")
    rate_cells = tr.select("td.colCompraVenta")
    if not name_el or len(rate_cells) < 2:
        return None

    buy_td, sell_td = rate_cells[0], rate_cells[1]
    spread_td = tr.select_one("td.colSpread")
    variation_el = tr.select_one("td.colVariacion .variacion")
    time_el = tr.select_one("td.colFecha abbr[title]")
    link_el = tr.select_one("td.colNombre a[href]")

    variation_pct = None
    if variation_el and variation_el.get_text(strip=True):
        variation_pct = _parse_money(variation_el.get_text(" ", strip=True))

    return {
        "name": name_el.get_text(strip=True),
        "buy": _parse_money(_own_text(buy_td)),
        "sell": _parse_money(_own_text(sell_td)),
        "spread": _parse_money(spread_td.get_text(strip=True)) if spread_td else None,
        "variation_pct": variation_pct,
        "updated_at": time_el["title"] if time_el else None,
        "url": SOURCE_URL.rstrip("/") + link_el["href"] if link_el else None,
    }


def _parse_table(soup: BeautifulSoup, table_id: str) -> list[dict]:
    table = soup.find("table", id=table_id)
    if table is None:
        return []
    rows = (_parse_row(tr) for tr in table.find_all("tr"))
    return [r for r in rows if r is not None]


def parse(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    averages = _parse_table(soup, "DolarPromedio")
    entities = _parse_table(soup, "Dolar")
    if not entities:
        raise ValueError("Could not find the rates table; the page layout may have changed.")
    return {
        "source": SOURCE_URL,
        "currency": "USD",
        "quote_currency": "DOP",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "average": averages[0] if averages else None,
        "entities": entities,
    }


def fetch(timeout: float = 15.0) -> dict:
    resp = httpx.get(
        SOURCE_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return parse(resp.text)


if __name__ == "__main__":
    import json

    print(json.dumps(fetch(), indent=2, ensure_ascii=False))
