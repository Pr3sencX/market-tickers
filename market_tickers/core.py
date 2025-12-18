# market_tickers/core.py

import re
from typing import List, Dict, Optional

from market_tickers.loaders import (
    load_stocks,
    load_indices,
    load_etfs,
    load_currencies,
)

# -----------------------------
# Helpers
# -----------------------------

def _normalize(text: str) -> str:
    """
    Normalize text for matching:
    - lowercase
    - remove spaces, punctuation, symbols
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())


# -----------------------------
# Index aliases (UX-first)
# -----------------------------

INDEX_ALIASES = {
    "nifty": "^NSEI",
    "nifty50": "^NSEI",
    "niftyfifty": "^NSEI",
    "sensex": "^BSESN",
    "bse": "^BSESN",
    "sp500": "^GSPC",
    "sandp500": "^GSPC",
    "s&p500": "^GSPC",
    "dow": "^DJI",
    "dowjones": "^DJI",
    "nasdaq": "^IXIC",
}


# -----------------------------
# Public API
# -----------------------------

def get_ticker(
    name: str,
    country: Optional[str] = None,
    category: Optional[str] = None,
):
    """
    Get Yahoo Finance ticker by human-readable name or code.

    Smart defaults:
    - Index aliases auto-detected ("Nifty", "Sensex", "SP500")
    - Currency codes auto-detected ("USDINR" → "USDINR=X")
    - Stocks default to NSE for India

    Parameters
    ----------
    name : str
        Human-readable name or code
    country : str | None
        Optional; required only when stock ambiguity exists
    category : str | None
        Optional; auto-detected if omitted
    """
    if not name or not isinstance(name, str):
        raise ValueError("name must be a non-empty string")

    raw_name = name.strip()
    norm_name = _normalize(raw_name.replace("=x", ""))

    # -----------------------------
    # 0️⃣ Hard short-circuits (NO ERRORS)
    # -----------------------------

    # Index aliases (work even if category not provided)
    if norm_name in INDEX_ALIASES:
        return INDEX_ALIASES[norm_name]

    # FX auto-detection (USDINR, EURUSD, etc.)
    if len(norm_name) == 6 and norm_name.isalpha():
        return f"{norm_name.upper()}=X"

    # -----------------------------
    # Category auto-detection
    # -----------------------------

    if category is None:
        # If looks like an index keyword
        if any(k in norm_name for k in INDEX_ALIASES):
            category = "index"
        else:
            category = "stock"

    # Normalize country
    country = country.lower() if isinstance(country, str) else None

    # -----------------------------
    # Load data
    # -----------------------------

    if category == "index":
        rows = load_indices()

    elif category == "etf":
        rows = load_etfs()

    elif category == "currency":
        rows = load_currencies()

    elif category == "stock":
        # Default to India if not specified (UX decision)
        if not country:
            country = "india"
        rows = load_stocks(country)

    else:
        raise ValueError(f"Unknown category: {category}")

    # -----------------------------
    # Defensive filtering
    # -----------------------------

    valid_rows: List[Dict[str, str]] = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("name")
        and row.get("ticker")
    ]

    # -----------------------------
    # 1️⃣ Exact match (name OR ticker)
    # -----------------------------

    exact = []
    for row in valid_rows:
        if (
            norm_name == _normalize(row["name"])
            or norm_name == _normalize(row["ticker"].replace("=x", ""))
        ):
            exact.append(row)

    if len(exact) == 1:
        return exact[0]["ticker"]

    # -----------------------------
    # 2️⃣ Startswith match
    # -----------------------------

    starts = [
        row for row in valid_rows
        if _normalize(row["name"]).startswith(norm_name)
    ]

    if len(starts) == 1:
        return starts[0]["ticker"]

    # -----------------------------
    # 3️⃣ Contains match
    # -----------------------------

    contains = [
        row for row in valid_rows
        if norm_name in _normalize(row["name"])
    ]

    if len(contains) == 1:
        return contains[0]["ticker"]

    # -----------------------------
    # 4️⃣ Smart disambiguation (SAFE DEFAULTS)
    # -----------------------------

    if len(contains) > 1:
        # Prefer NSE for India
        if country == "india":
            nse = [r for r in contains if r["ticker"].endswith(".NS")]
            if nse:
                contains = nse

        # Prefer shortest name (usually main listing)
        contains.sort(key=lambda r: len(r["name"]))
        return contains[0]["ticker"]

    # -----------------------------
    # Final fallback
    # -----------------------------

    raise KeyError(f"Ticker not found for: {raw_name}")


def get_default_index(stock_name: str, country: str = "india"):
    """
    Return default index for a stock.
    """
    country = country.lower()

    if country == "india":
        return "^NSEI"
    if country in ("us", "usa", "united_states"):
        return "^GSPC"

    raise ValueError(f"No default index defined for country: {country}")
