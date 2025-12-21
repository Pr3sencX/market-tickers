from importlib import resources
import csv


def _load_csv(relative_path: str) -> list[dict]:
    """
    Load a CSV file bundled inside the market_tickers package.
    Returns list of dict rows.
    """
    with resources.files("market_tickers").joinpath(relative_path).open(
        "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)
        return list(reader)


# -----------------------------
# STOCKS
# -----------------------------

def load_stocks(country: str) -> list[dict]:
    """
    Load stock tickers for a given country.

    Example:
        load_stocks("india")
        load_stocks("united_states")
    """
    country = country.lower().replace(" ", "_")
    path = f"data/stocks/stocks_{country}.csv"
    return _load_csv(path)


# -----------------------------
# INDICES
# -----------------------------

def load_indices() -> list[dict]:
    """
    Load global indices.
    """
    return _load_csv("data/indices/indices.csv")


# -----------------------------
# ETFs
# -----------------------------

def load_etfs() -> list[dict]:
    """
    Load global ETFs.
    """
    return _load_csv("data/etfs/etfs.csv")


# -----------------------------
# CURRENCIES
# -----------------------------

def load_currencies() -> list[dict]:
    """
    Load currency tickers.
    """
    return _load_csv("data/currencies/currencies.csv")