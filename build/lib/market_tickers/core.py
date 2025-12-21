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
    """Must match loaders normalization."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


# -----------------------------
# Index aliases
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
# Core resolver
# -----------------------------

def get_ticker(
    name: str,
    country: Optional[str] = None,
    category: Optional[str] = None,
):
    if not name or not isinstance(name, str):
        raise ValueError("name must be a non-empty string")

    raw_name = name.strip()
    norm_name = _normalize(raw_name.replace("=x", ""))

    # ---- shortcuts ----
    if norm_name in INDEX_ALIASES:
        return INDEX_ALIASES[norm_name]

    if len(norm_name) == 6 and norm_name.isalpha():
        return f"{norm_name.upper()}=X"

    if category is None:
        category = "stock"

    country = country.lower() if isinstance(country, str) else None

    # ---- load data ----
    if category == "index":
        rows = load_indices()
    elif category == "etf":
        rows = load_etfs()
    elif category == "currency":
        rows = load_currencies()
    elif category == "stock":
        rows = load_stocks(country or "india")
    else:
        raise ValueError(f"Unknown category: {category}")

    valid_rows: List[Dict[str, str]] = [
        r for r in rows if r.get("name") and r.get("ticker")
    ]

    # ---- exact match ----
    exact = [
        r for r in valid_rows
        if norm_name == _normalize(r["name"])
        or norm_name == _normalize(r["ticker"].replace("=x", ""))
    ]

    if len(exact) == 1:
        return exact[0]["ticker"]

    if len(exact) > 1:
        if country == "india":
            nse = [r for r in exact if r["ticker"].endswith(".NS")]
            if len(nse) == 1:
                return nse[0]["ticker"]

        raise KeyError(
            f"'{raw_name}' is ambiguous. "
            f"Please use full company name (e.g. 'Reliance Industries')."
        )

    # ---- startswith ----
    starts = [
        r for r in valid_rows
        if _normalize(r["name"]).startswith(norm_name)
    ]

    if len(starts) == 1:
        return starts[0]["ticker"]

    # ---- contains ----
    contains = [
        r for r in valid_rows
        if norm_name in _normalize(r["name"])
    ]

    if len(contains) == 1:
        return contains[0]["ticker"]

    if len(contains) > 1:
        if country == "india":
            nse = [r for r in contains if r["ticker"].endswith(".NS")]
            if nse:
                return nse[0]["ticker"]

        raise KeyError(
            f"'{raw_name}' is ambiguous. "
            f"Please use full company name (e.g. 'Reliance Industries')."
        )

    raise KeyError(f"Ticker not found for: {raw_name}")


# -----------------------------
# Defaults
# -----------------------------

def get_default_index(stock_name: str, country: str = "india"):
    if country.lower() == "india":
        return "^NSEI"
    if country.lower() in ("us", "usa", "united_states"):
        return "^GSPC"
    raise ValueError(f"No default index defined for country: {country}")


# -----------------------------
# Smart wrapper
# -----------------------------

def get(name: str, country: Optional[str] = None):
    """
    Smart ticker resolver.
    Priority:
    1. Index (only if name looks like index)
    2. Currency (only if looks like FX code)
    3. Stock (DEFAULT and PRIMARY)
    4. ETF (last fallback)
    """

    name_norm = _normalize(name)

    # 1️⃣ Index keywords
    if name_norm in INDEX_ALIASES or any(
        k in name_norm for k in ("nifty", "sensex", "dow", "nasdaq", "sp")
    ):
        try:
            return get_ticker(name, category="index")
        except Exception:
            pass

    # 2️⃣ Currency pattern (USDINR, EURUSD, etc.)
    if len(name_norm) == 6 and name_norm.isalpha():
        try:
            return get_ticker(name, category="currency")
        except Exception:
            pass

    # 3️⃣ STOCK FIRST (most important)
    try:
        return get_ticker(name, country=country, category="stock")
    except Exception:
        pass

    # 4️⃣ ETF fallback
    try:
        return get_ticker(name, category="etf")
    except Exception:
        pass

    raise KeyError(f"Ticker not found for: {name}")

