# market_tickers/core.py

from market_tickers.loaders import (
    load_stocks,
    load_indices,
    load_etfs,
    load_currencies,
)


# -----------------------------
# Public API
# -----------------------------

def get_ticker(name: str, country: str | None = None, category: str = "stock"):
    """
    Get Yahoo Finance ticker by human-readable name.
    """
    name = name.lower().strip()

    if category == "stock":
        if not country:
            raise ValueError("country is required for stock lookup")
        rows = load_stocks(country)

    elif category == "index":
        rows = load_indices()

    elif category == "etf":
        rows = load_etfs()

    elif category == "currency":
        rows = load_currencies()

    else:
        raise ValueError(f"Unknown category: {category}")

    # 1️⃣ Exact match
    for row in rows:
        if row["name"].lower() == name:
            return row["ticker"]

    # 2️⃣ Startswith match
    for row in rows:
        if row["name"].lower().startswith(name):
            return row["ticker"]

    # 3️⃣ Contains match
    for row in rows:
        if name in row["name"].lower():
            return row["ticker"]

    raise KeyError(f"Ticker not found for: {name}")



def get_default_index(stock_name: str, country: str = "india"):
    """
    Return default index for a stock (simple heuristic).
    """
    country = country.lower()

    if country == "india":
        return "^NSEI"   # NIFTY 50
    if country in ("united_states", "usa", "us"):
        return "^GSPC"  # S&P 500

    raise ValueError(f"No default index defined for country: {country}")
