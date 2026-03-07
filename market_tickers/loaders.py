from importlib import resources
import csv
import re
from pathlib import Path
from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_csv(relative_path: str) -> List[Dict[str, str]]:
    """Load a bundled CSV file. Returns list of dict rows."""
    with resources.files("market_tickers").joinpath(relative_path).open(
        "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)
        return list(reader)


def _load_xlsx(relative_path: str, sheet_name: str = "Full Dataset") -> List[Dict[str, str]]:
    """
    Load new_stocks_data.xlsx and normalise its columns to the internal schema:
        ticker, name, exchange, category name, country,
        industry, sector, broad_group, sub_group, ticker_status

    xlsx column          → internal key
    ─────────────────────────────────────
    YFinance Ticker      → ticker
    Company Name         → name
    Exchange             → exchange
    Category (YF2017)    → category name
    Country              → country
    Industry Group       → industry
    Primary Sector       → sector
    Broad Group          → broad_group
    Sub Group            → sub_group
    Ticker Status        → ticker_status
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required to read the xlsx dataset. "
            "Install it with: pip install pandas openpyxl"
        )

    pkg_path = resources.files("market_tickers").joinpath(relative_path)
    with pkg_path.open("rb") as f:
        df = pd.read_excel(f, sheet_name=sheet_name)

    col_map = {
        "YFinance Ticker":   "ticker",
        "Company Name":      "name",
        "Exchange":          "exchange",
        "Category (YF2017)": "category name",
        "Country":           "country",
        "Industry Group":    "industry",
        "Primary Sector":    "sector",
        "Broad Group":       "broad_group",
        "Sub Group":         "sub_group",
        "Ticker Status":     "ticker_status",
    }
    df = df.rename(columns=col_map)
    keep = [c for c in col_map.values() if c in df.columns]
    df = df[keep].dropna(subset=["ticker", "name"])
    return df.fillna("").astype(str).to_dict(orient="records")


def _normalize(text: str) -> str:
    """Lowercase + strip non-alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Module-level caches
# ─────────────────────────────────────────────────────────────────────────────

_DAM_BY_COUNTRY: Dict[str, List[Dict]] = {}
_DAM_NAME_INDEX: Dict[str, Dict] = {}
_DAM_TICKER_INDEX: Dict[str, Dict] = {}
_DAM_LOADED = False

_COUNTRY_CACHE: Dict[str, List[Dict]] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Damodaran 2026  (primary stock dataset — new_stocks_data.xlsx)
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_damodaran_loaded() -> None:
    """
    Lazy-load and index new_stocks_data.xlsx on first call.
    All subsequent calls return immediately (already loaded).

    Builds three indexes:
        _DAM_BY_COUNTRY  → { country_key : [rows] }
        _DAM_NAME_INDEX  → { norm_name   : row }   (first occurrence wins)
        _DAM_TICKER_INDEX → { norm_ticker : row }
    """
    global _DAM_LOADED, _DAM_BY_COUNTRY, _DAM_NAME_INDEX, _DAM_TICKER_INDEX
    if _DAM_LOADED:
        return

    rows = _load_xlsx("data/stocks/new_data/new_stocks_data.xlsx")

    for row in rows:
        ticker      = row.get("ticker",  "").strip()
        name        = row.get("name",    "").strip()
        country_raw = row.get("country", "").strip()

        if not ticker or not name:
            continue

        # Build two country key variants and avoid double-adding rows
        country_key = _normalize(country_raw)                    # "unitedstates"
        country_us  = country_raw.lower().replace(" ", "_")      # "united_states"
        seen_keys: set = set()
        for ck in (country_key, country_us):
            if ck not in seen_keys:
                seen_keys.add(ck)
                _DAM_BY_COUNTRY.setdefault(ck, []).append(row)

        norm_name = _normalize(name)
        _DAM_NAME_INDEX.setdefault(norm_name, row)

        norm_tick = _normalize(ticker.replace("=x", ""))
        _DAM_TICKER_INDEX.setdefault(norm_tick, row)

    _DAM_LOADED = True


def get_damodaran_rows_for_country(country: str) -> List[Dict]:
    """
    Return all Damodaran 2026 rows for a given country.
    Accepts any common format: "india", "united_states", "United States".
    """
    _ensure_damodaran_loaded()
    country_key = _normalize(country)
    return _DAM_BY_COUNTRY.get(country_key, [])


def get_damodaran_name_index() -> Dict[str, Dict]:
    """Return the global { normalized_name → row } index."""
    _ensure_damodaran_loaded()
    return _DAM_NAME_INDEX


def get_damodaran_ticker_index() -> Dict[str, Dict]:
    """Return the global { normalized_ticker → row } index."""
    _ensure_damodaran_loaded()
    return _DAM_TICKER_INDEX


# ─────────────────────────────────────────────────────────────────────────────
# Legacy per-country stocks  (YF2017 fallback)
# ─────────────────────────────────────────────────────────────────────────────

def load_stocks(country: str) -> List[Dict]:
    """
    Load legacy per-country stock CSV (YF2017-derived).
    Results are cached in memory after first load.

    Examples:
        load_stocks("india")          → reads stocks_india.csv
        load_stocks("united_states")  → reads stocks_united_states.csv
    """
    country_key = country.lower().replace(" ", "_")
    if country_key not in _COUNTRY_CACHE:
        path = f"data/stocks/stocks_{country_key}.csv"
        try:
            _COUNTRY_CACHE[country_key] = _load_csv(path)
        except (FileNotFoundError, Exception):
            _COUNTRY_CACHE[country_key] = []
    return _COUNTRY_CACHE[country_key]


def list_available_countries() -> List[str]:
    """
    Return a sorted list of all countries that have a legacy stock CSV.
    Used by list_countries() and the --dedup updater.
    """
    try:
        data_path = resources.files("market_tickers").joinpath("data/stocks")
        # Walk the package data directory
        country_files = [
            f.name for f in data_path.iterdir()
            if f.name.startswith("stocks_") and f.name.endswith(".csv")
        ]
    except Exception:
        # Fallback: scan filesystem (development mode)
        pkg_dir = Path(__file__).parent
        stocks_dir = pkg_dir / "data" / "stocks"
        country_files = [
            f.name for f in stocks_dir.glob("stocks_*.csv")
        ]

    countries = sorted(
        f.replace("stocks_", "").replace(".csv", "")
        for f in country_files
    )
    return countries


# ─────────────────────────────────────────────────────────────────────────────
# Indices / ETFs / Currencies
# ─────────────────────────────────────────────────────────────────────────────

def load_indices() -> List[Dict]:
    """Load global indices."""
    return _load_csv("data/indices/indices.csv")


def load_etfs() -> List[Dict]:
    """Load global ETFs."""
    return _load_csv("data/etfs/etfs.csv")


def load_currencies() -> List[Dict]:
    """Load currency pairs."""
    return _load_csv("data/currencies/currencies.csv")
