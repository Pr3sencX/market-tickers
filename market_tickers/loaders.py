from importlib import resources
import csv


def _load_csv(relative_path: str) -> list[dict]:
    """
    Load a CSV file bundled inside the market_tickers package.
    Returns list of dict rows with stripped keys & values.
    """
    with resources.files("market_tickers").joinpath(relative_path).open(
        "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # normalize keys & values (VERY IMPORTANT)
            rows.append({
                k.strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            })
        return rows


# -----------------------------
# STOCKS
# -----------------------------

def load_stocks(country: str) -> list[dict]:
    """
    Load stock tickers for a given country.
    """
    country = country.lower().replace(" ", "_")
    path = f"data/stocks/stocks_{country}.csv"
    return _load_csv(path)


# -----------------------------
# INDICES (STRICT)
# -----------------------------

def load_indices() -> list[dict]:
    """
    Load indices STRICTLY from indices.csv only.
    No fallback, no regional mixing.
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
