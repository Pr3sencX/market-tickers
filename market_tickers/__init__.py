# market_tickers/__init__.py

from market_tickers.core import (
    get_ticker,
    get_default_index,
    search_tickers,
)
from market_tickers.loaders import list_available_countries


def list_countries() -> list:
    """Return a sorted list of all countries that have stock data."""
    return list_available_countries()


def update_data(
    countries: list = None,
    update_etfs: bool = True,
    update_indices: bool = True,
    verbose: bool = True,
) -> None:
    """
    Pull fresh ticker data from official exchange sources and update
    the bundled CSVs.

    Parameters
    ----------
    countries      : list of country strings to update, e.g. ["india", "usa"].
                     Pass an empty list [] to skip stocks.
                     Defaults to all live-source countries (india, usa, uk).
    update_etfs    : refresh etfs.csv (default True)
    update_indices : refresh indices.csv (default True)
    verbose        : print progress (default True)

    Requires: pip install market-tickers[updater]
    """
    from market_tickers.updater import (
        fetch_nse_india,
        fetch_usa_stocks,
        fetch_uk_stocks,
        update_etfs as _update_etfs,
        update_indices as _update_indices,
        _write_csv,
        DATA_DIR,
    )

    LIVE_FETCHERS = {
        "india":          (fetch_nse_india,  ["ticker", "name", "exchange", "category name", "country"]),
        "united_states":  (fetch_usa_stocks, ["ticker", "name", "exchange", "category name", "country"]),
        "usa":            (fetch_usa_stocks, ["ticker", "name", "exchange", "category name", "country"]),
        "united_kingdom": (fetch_uk_stocks,  ["ticker", "name", "exchange", "category name", "country"]),
        "uk":             (fetch_uk_stocks,  ["ticker", "name", "exchange", "category name", "country"]),
    }

    if update_indices:
        n = _update_indices()
        if verbose:
            print(f"  ✅ indices.csv → {n} rows")

    if update_etfs:
        n = _update_etfs()
        if verbose:
            print(f"  ✅ etfs.csv → {n} rows")

    targets = countries if countries is not None else ["india", "united_states", "united_kingdom"]
    for country in targets:
        c = country.lower().strip()
        if c not in LIVE_FETCHERS:
            if verbose:
                print(f"  ⚠️  No live source for '{c}'. Available: india, usa, uk.")
            continue
        fetcher, fieldnames = LIVE_FETCHERS[c]
        rows = fetcher()
        if not rows:
            continue
        file_key = "usa"            if c in ("united_states", "usa") else \
                   "united_kingdom" if c in ("united_kingdom", "uk") else c
        csv_path = DATA_DIR / "stocks" / f"stocks_{file_key}.csv"
        n = _write_csv(csv_path, rows, fieldnames)
        if verbose:
            print(f"  ✅ stocks_{file_key}.csv → {n} rows")
