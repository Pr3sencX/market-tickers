# market_tickers/core.py

import re
from typing import List, Dict

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


# Common index aliases (UX improvement)
INDEX_ALIASES = {
    "nifty": "^NSEI",
    "nifty50": "^NSEI",
    "sensex": "^BSESN",
    "bse": "^BSESN",
    "sp500": "^GSPC",
    "sandp500": "^GSPC",
    "s&p500": "^GSPC",
    "dow": "^DJI",
    "nasdaq": "^IXIC",
}


# -----------------------------
# Public API
# -----------------------------

def get_ticker(
    name: str,
    country: str | None = None,
    category: str = "stock",
):
    """
    Get Yahoo Finance ticker by human-readable name or code.

    Parameters
    ----------
    name : str
        Human-readable name or code
        (e.g. "Reliance Industries", "USDINR", "Nifty 50")
    country : str | None
        Required for stocks (e.g. "india", "united_states")
    category : str
        One of: stock, index, etf, currency
    """
    if not name:
        raise ValueError("name cannot be empty")

    raw_name = name.strip()
    name = raw_name.lower().strip().replace("=x", "")
    norm_name = _normalize(name)

    # -----------------------------
    # Load data
    # -----------------------------

    if category == "stock":
        if not country:
            raise ValueError("country is required for stock lookup")
        rows = load_stocks(country)

    elif category == "index":
        if norm_name in INDEX_ALIASES:
            return INDEX_ALIASES[norm_name]
        rows = load_indices()

    elif category == "etf":
        rows = load_etfs()

    elif category == "currency":
        rows = load_currencies()

        # Guaranteed Yahoo Finance FX fallback
        # Example: USDINR → USDINR=X
        if len(norm_name) == 6 and norm_name.isalpha():
            return f"{norm_name.upper()}=X"

    else:
        raise ValueError(f"Unknown category: {category}")

    # -----------------------------
    # Defensive filtering
    # -----------------------------

    valid_rows: List[Dict[str, str]] = [
        row for row in rows
        if isinstance(row, dict)
        and "name" in row
        and "ticker" in row
        and row["name"]
        and row["ticker"]
    ]

    # -----------------------------
    # 1️⃣ Exact match (name OR ticker)
    # -----------------------------

    exact_matches = []
    for row in valid_rows:
        row_name = _normalize(row["name"])
        row_ticker = _normalize(row["ticker"].replace("=x", ""))

        if norm_name == row_name or norm_name == row_ticker:
            exact_matches.append(row)

    if len(exact_matches) == 1:
        return exact_matches[0]["ticker"]

    # -----------------------------
    # 2️⃣ Startswith match
    # -----------------------------

    startswith_matches = [
        row for row in valid_rows
        if _normalize(row["name"]).startswith(norm_name)
    ]

    if len(startswith_matches) == 1:
        return startswith_matches[0]["ticker"]

    # -----------------------------
    # 3️⃣ Contains match
    # -----------------------------

    contains_matches = [
        row for row in valid_rows
        if norm_name in _normalize(row["name"])
    ]

    if len(contains_matches) == 1:
        return contains_matches[0]["ticker"]

    # -----------------------------
    # 4️⃣ Smart disambiguation (NEW)
    # -----------------------------

    if len(contains_matches) > 1:
        # Prefer NSE over BSE for India
        if country == "india":
            nse = [r for r in contains_matches if r["ticker"].endswith(".NS")]
            if len(nse) == 1:
                return nse[0]["ticker"]
            if nse:
                contains_matches = nse

        # Prefer shortest name (usually main listing)
        contains_matches.sort(key=lambda r: len(r["name"]))
        return contains_matches[0]["ticker"]

    # -----------------------------
    # Final fallback
    # -----------------------------

    raise KeyError(f"Ticker not found for: {raw_name}")


def get_default_index(stock_name: str, country: str = "india"):
    """
    Return default index for a stock (simple heuristic).
    """
    country = country.lower()

    if country == "india":
        return "^NSEI"   # NIFTY 50
    if country in ("united_states", "usa", "us"):
        return "^GSPC"   # S&P 500

    raise ValueError(f"No default index defined for country: {country}")
