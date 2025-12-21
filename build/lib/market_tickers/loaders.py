from importlib import resources
import csv
from typing import List, Dict


def _load_csv(relative_path: str) -> List[Dict[str, str]]:
    """
    Load a CSV file bundled inside the market_tickers package.
    Returns list of dict rows.
    """
    try:
        with resources.files("market_tickers").joinpath(relative_path).open(
            "r", encoding="utf-8"
        ) as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        # Safe fallback if file is missing
        return []


# -----------------------------
# STOCKS (OLD + NEW)
# -----------------------------

def load_stocks(country: str) -> List[Dict[str, str]]:
    """
    Load stock tickers for a given country.

    Uses:
    - legacy dataset (pre-2016)
    - new dataset (post-2016)

    Deduplicates by ticker (safest key).
    """
    country = country.lower().replace(" ", "_")

    rows: List[Dict[str, str]] = []

    # 1️⃣ Old stable dataset
    rows.extend(_load_csv(f"data/stocks/stocks_{country}.csv"))

    # 2️⃣ New dataset (only India + US for now)
    if country == "india":
        rows.extend(_load_csv("data/new_stocks/india_stocks.csv"))
    elif country in ("united_states", "us"):
        rows.extend(_load_csv("data/new_stocks/us_stocks.csv"))

    # 3️⃣ Deduplicate by ticker
    deduped = {}
    for row in rows:
        ticker = row.get("ticker")
        if ticker:
            deduped[ticker] = row

    return list(deduped.values())


# -----------------------------
# INDICES
# -----------------------------

def load_indices() -> List[Dict[str, str]]:
    return _load_csv("data/indices/indices.csv")


# -----------------------------
# ETFs
# -----------------------------

def load_etfs() -> List[Dict[str, str]]:
    return _load_csv("data/etfs/etfs.csv")


# -----------------------------
# CURRENCIES
# -----------------------------

def load_currencies() -> List[Dict[str, str]]:
    return _load_csv("data/currencies/currencies.csv")
