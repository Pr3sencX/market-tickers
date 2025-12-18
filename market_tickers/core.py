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
    Get Yahoo Finance ticker by human-readable name or code.

    Parameters
    ----------
    name : str
        Human-readable name or code (e.g. "Reliance Industries", "USDINR")
    country : str | None
        Country for stocks (e.g. "india", "united_states")
    category : str
        One of: stock, index, etf, currency
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

    # 1️⃣ Exact match (name OR ticker code)
    for row in rows:
        row_name = row["name"].lower()
        row_ticker = row["ticker"].lower()

        # allow matching ticker codes like USDINR or USDINR=X
        if (
            row_name == name
            or row_ticker == name
            or row_ticker.replace("=x", "") == name
        ):
            return row["ticker"]

    # 2️⃣ Startswith match (name only)
    for row in rows:
        if row["name"].lower().startswith(name):
            return row["ticker"]

    # 3️⃣ Contains match (name only)
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
