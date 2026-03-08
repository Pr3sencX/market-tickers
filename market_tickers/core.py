# market_tickers/core.py
# v0.5.0 — Batch lookup + case-insensitive countries

import re
import difflib
from typing import Dict, List, Optional, Union

from market_tickers.loaders import (
    get_damodaran_rows_for_country,
    load_stocks,
    load_indices,
    load_etfs,
    load_currencies,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase + strip non-alphanumeric characters for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _ticker_base(ticker: str) -> str:
    """
    Normalize a ticker for matching — strips exchange suffix and special chars.
    Examples:  'TCS.NS' → 'tcs'   'AAPL' → 'aapl'   'EURUSD=X' → 'eurusd'
    """
    t = ticker.replace("=X", "").replace("=x", "")
    dot = t.rfind(".")
    if dot != -1 and len(t) - dot <= 4:
        t = t[:dot]
    return _normalize(t)


_SUFFIX_PREF = {"": 0, "ns": 1, "l": 2, "to": 3, "ax": 4}

# Country aliases — normalise any input to the underscore key used in data files
_COUNTRY_ALIASES: Dict[str, str] = {
    "us":  "united_states",
    "usa": "united_states",
    "uk":  "united_kingdom",
    "gb":  "united_kingdom",
    "hk":  "hong_kong",
    "nz":  "new_zealand",
    "kr":  "south_korea",
    "uae": "united_arab_emirates",
}


def _resolve_country(country: str) -> str:
    """
    Normalise any country string to the internal underscore key.

    Handles mixed case, spaces, and short aliases:
      "United States" → "united_states"
      "south korea"   → "south_korea"
      "USA"           → "united_states"
      "india"         → "india"
    """
    key = country.strip().lower().replace(" ", "_")
    return _COUNTRY_ALIASES.get(key, key)


# Common index aliases
INDEX_ALIASES = {
    "nifty":       "^NSEI",
    "nifty50":     "^NSEI",
    "nifty 50":    "^NSEI",
    "sensex":      "^BSESN",
    "bse":         "^BSESN",
    "sp500":       "^GSPC",
    "s&p500":      "^GSPC",
    "sandp500":    "^GSPC",
    "s&p 500":     "^GSPC",
    "dow":         "^DJI",
    "dowjones":    "^DJI",
    "nasdaq":      "^IXIC",
    "nasdaq100":   "^NDX",
    "nasdaq 100":  "^NDX",
    "russell2000": "^RUT",
    "vix":         "^VIX",
    "dax":         "^GDAXI",
    "ftse":        "^FTSE",
    "ftse100":     "^FTSE",
    "cac40":       "^FCHI",
    "cac 40":      "^FCHI",
    "nikkei":      "^N225",
    "nikkei225":   "^N225",
    "hangseng":    "^HSI",
    "hang seng":   "^HSI",
    "kospi":       "^KS11",
    "asx200":      "^AXJO",
    "asx 200":     "^AXJO",
    "bitcoin":     "BTC-USD",
    "btc":         "BTC-USD",
    "ethereum":    "ETH-USD",
    "eth":         "ETH-USD",
}


# ─────────────────────────────────────────────────────────────────────────────
# Match engine
# ─────────────────────────────────────────────────────────────────────────────

def _match_rows(
    norm_name: str,
    raw_name: str,
    rows: List[Dict],
    fuzzy: bool = True,
) -> Optional[str]:
    """
    5-tier matching pipeline against a list of rows.

    Tier 1 — Exact name match
    Tier 2 — Exact base-ticker match (suffix-priority tiebreak)
    Tier 3 — Prefix match (single result required)
    Tier 4 — Contains match (single → return; multiple → highest coverage fraction)
    Tier 5 — Token-based difflib fuzzy (cutoff 0.82) for typo tolerance
    """
    valid = [r for r in rows if "name" in r and "ticker" in r]

    # 1. Exact name
    exact_name = [r for r in valid if _normalize(r["name"]) == norm_name]
    if len(exact_name) == 1:
        return exact_name[0]["ticker"]
    if len(exact_name) > 1:
        raise KeyError(
            f"Multiple tickers found for '{raw_name}'. Please refine your query."
        )

    # 2. Exact ticker (base, suffix stripped)
    exact_tick = [r for r in valid if _ticker_base(r["ticker"]) == norm_name]
    if len(exact_tick) == 1:
        return exact_tick[0]["ticker"]
    if len(exact_tick) > 1:
        def _prio(r):
            t = r["ticker"]
            dot = t.rfind(".")
            suf = t[dot + 1:].lower() if dot != -1 else ""
            return _SUFFIX_PREF.get(suf, 99)
        exact_tick.sort(key=_prio)
        return exact_tick[0]["ticker"]

    # 3. Prefix (name)
    prefix = [r for r in valid if _normalize(r["name"]).startswith(norm_name)]
    if len(prefix) == 1:
        return prefix[0]["ticker"]

    # 4. Contains (name)
    contains = [r for r in valid if norm_name in _normalize(r["name"])]
    if len(contains) == 1:
        return contains[0]["ticker"]
    if len(contains) > 1:
        if fuzzy:
            def _match_fraction(r):
                nlen = len(_normalize(r["name"]))
                return -len(norm_name) / nlen if nlen else 0
            contains.sort(key=_match_fraction)
            return contains[0]["ticker"]
        raise KeyError(
            f"Multiple tickers found for '{raw_name}'. Please refine your query."
        )

    # 5. Token-based fuzzy — splits on whitespace + punctuation so that
    #    "Amazon.com, Inc." → tokens ["amazon", "com", "inc"] and
    #    "Amazn" vs "amazon" → 0.909 ✓
    if fuzzy:
        FUZZY_CUTOFF = 0.82
        scored: list = []
        for r in valid:
            raw_tokens = re.split(r"[\s.,\-/&]+", r["name"])
            tokens = [
                _normalize(w)
                for w in raw_tokens
                if len(_normalize(w)) >= max(3, len(norm_name) - 2)
            ]
            if not tokens:
                continue
            best = max(
                difflib.SequenceMatcher(None, norm_name, tok).ratio()
                for tok in tokens
            )
            if best >= FUZZY_CUTOFF:
                scored.append((best, r))

        if scored:
            scored.sort(key=lambda x: -x[0])
            return scored[0][1]["ticker"]

    return None


def _get_single(
    name: str,
    country: Optional[str],
    category: str,
    fuzzy: bool,
    country_clean: Optional[str] = None,
) -> str:
    """Core single-name resolver (reused by both get_ticker and batch mode)."""
    if not name:
        raise ValueError("name cannot be empty")

    raw_name  = name.strip()
    norm_name = _normalize(raw_name.lower().replace("=x", ""))

    if category == "index":
        alias = INDEX_ALIASES.get(norm_name) or INDEX_ALIASES.get(raw_name.lower())
        if alias:
            return alias
        rows = load_indices()
        result = _match_rows(norm_name, raw_name, rows, fuzzy=fuzzy)
        if result:
            return result
        raise KeyError(f"Index not found: '{raw_name}'")

    if category == "etf":
        rows = load_etfs()
        result = _match_rows(norm_name, raw_name, rows, fuzzy=fuzzy)
        if result:
            return result
        raise KeyError(f"ETF not found: '{raw_name}'")

    if category == "currency":
        # Normalise all common input formats to a bare 6-letter code:
        #   "USD/INR"  → "USDINR=X"
        #   "USDINR"   → "USDINR=X"
        #   "usdinr"   → "USDINR=X"
        #   "USDINR=X" → "USDINR=X"
        _stripped = re.sub(r"=X$", "", raw_name, flags=re.IGNORECASE)  # remove =X suffix first
        currency_code = re.sub(r"[^a-zA-Z]", "", _stripped)            # then strip / spaces etc.
        if len(currency_code) == 6 and currency_code.isalpha():
            return f"{currency_code.upper()}=X"
        rows = load_currencies()
        result = _match_rows(norm_name, raw_name, rows, fuzzy=fuzzy)
        if result:
            return result
        raise KeyError(f"Currency not found: '{raw_name}'")

    if category == "stock":
        if not country and not country_clean:
            raise ValueError("country is required for stock lookup")

        cc = country_clean or _resolve_country(country)
        is_india = cc == "india"

        dam_rows = get_damodaran_rows_for_country(cc)
        if dam_rows:
            result = _match_rows(norm_name, raw_name, dam_rows, fuzzy=fuzzy)
            if result:
                return result

        legacy_rows = load_stocks(cc)
        if is_india and legacy_rows:
            legacy_rows = [r for r in legacy_rows if r.get("ticker", "").endswith(".NS")]
        if legacy_rows:
            result = _match_rows(norm_name, raw_name, legacy_rows, fuzzy=fuzzy)
            if result:
                return result

        raise KeyError(
            f"Ticker not found for '{raw_name}' in country '{country or cc}'. "
            f"Searched Damodaran 2026 ({len(dam_rows)} rows) and "
            f"legacy dataset ({len(legacy_rows)} rows)."
        )

    raise ValueError(
        f"Unknown category: '{category}'. Use one of: stock, index, etf, currency"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_ticker(
    name: Union[str, List[str]],
    country: Optional[str] = None,
    category: str = "stock",
    fuzzy: bool = True,
) -> Union[str, List[str]]:
    """
    Get Yahoo Finance ticker(s) by human-readable name or code.

    Pass a single string → returns a single ticker string.
    Pass a list          → returns a list of resolved tickers (not-found entries
                           are silently skipped, so the result is always clean).

    Parameters
    ----------
    name     : str, or list of str for batch lookup.
    country  : Country for stock lookups. Case-insensitive, spaces accepted.
               e.g. "India", "United States", "USA", "uk", "south korea"
    category : "stock" | "index" | "etf" | "currency"
    fuzzy    : Approximate / typo-tolerant matching (default True)

    Single lookup
    -------------
    >>> get_ticker("Reliance Industries", country="india")
    'RELIANCE.NS'
    >>> get_ticker("AAPL", country="USA")
    'AAPL'
    >>> get_ticker("S&P 500", category="index")
    '^GSPC'

    Batch lookup
    ------------
    >>> companies = ["Apple", "Microsoft", "Amazon"]
    >>> tickers = get_ticker(companies, country="United States")
    >>> tickers
    ['AAPL', 'MSFT', 'AMZN']

    >>> # Not-found names are silently skipped — result is always yfinance-ready
    >>> tickers = get_ticker(["Apple", "FakeXYZ", "Microsoft"], country="usa")
    >>> tickers
    ['AAPL', 'MSFT']
    >>> yf.download(tickers, period="1y")
    """
    # ── Single ────────────────────────────────────────────────────────────────
    if isinstance(name, str):
        resolved = _resolve_country(country) if country else None
        return _get_single(name, country, category, fuzzy, country_clean=resolved)

    # ── Batch ─────────────────────────────────────────────────────────────────
    if not isinstance(name, (list, tuple)):
        raise TypeError(f"name must be a str or list, got {type(name).__name__}")

    # Resolve country once — not per-item
    resolved = _resolve_country(country) if country else None

    results: List[str] = []
    for n in name:
        try:
            results.append(
                _get_single(n, country, category, fuzzy, country_clean=resolved)
            )
        except (KeyError, ValueError):
            pass   # silently skip — result stays clean, no None pollution

    return results


def search_tickers(
    query: str,
    country: Optional[str] = None,
    category: str = "stock",
    limit: int = 10,
) -> List[Dict]:
    """
    Search for tickers matching a query string.
    Returns a list of matching row dicts: [{"ticker": ..., "name": ..., ...}]

    Parameters
    ----------
    query    : Search string (partial name or ticker)
    country  : Required for category="stock". Case-insensitive.
    category : "stock" | "index" | "etf" | "currency"
    limit    : Max results to return (default 10)
    """
    if not query:
        raise ValueError("query cannot be empty")

    norm_query = _normalize(query)

    if category == "stock":
        if not country:
            raise ValueError("country is required for stock search")
        country_clean = _resolve_country(country)
        rows = get_damodaran_rows_for_country(country_clean) or load_stocks(country_clean)
    elif category == "index":
        rows = load_indices()
    elif category == "etf":
        rows = load_etfs()
    elif category == "currency":
        rows = load_currencies()
    else:
        raise ValueError(f"Unknown category: '{category}'")

    valid = [r for r in rows if "name" in r and "ticker" in r]
    results, seen = [], set()

    for r in valid:
        t = r["ticker"]
        if t in seen:
            continue
        if norm_query in _normalize(r["name"]) or norm_query in _normalize(t.replace("=x", "")):
            results.append(r)
            seen.add(t)
        if len(results) >= limit:
            break

    return results[:limit]


def get_default_index(stock_name: str, country: str = "india") -> str:
    """
    Return the default benchmark index ticker for a given country.

    Parameters
    ----------
    stock_name : str  (unused; reserved for future per-sector logic)
    country    : str  Case-insensitive. e.g. "India", "United States", "uk"
    """
    _INDEX_MAP = {
        "india":           "^NSEI",
        "united_states":   "^GSPC",
        "united_kingdom":  "^FTSE",
        "germany":         "^GDAXI",
        "france":          "^FCHI",
        "japan":           "^N225",
        "china":           "000001.SS",
        "hong_kong":       "^HSI",
        "australia":       "^AXJO",
        "canada":          "^GSPTSE",
        "brazil":          "^BVSP",
        "south_korea":     "^KS11",
        "taiwan":          "^TWII",
        "singapore":       "^STI",
        "italy":           "FTSEMIB.MI",
        "spain":           "^IBEX",
        "netherlands":     "^AEX",
        "switzerland":     "^SSMI",
        "sweden":          "^OMX",
        "norway":          "^OBX",
        "denmark":         "^OMXC25",
        "finland":         "^OMXH25",
        "belgium":         "^BFX",
        "austria":         "^ATX",
        "greece":          "^ATG",
        "turkey":          "^XU100",
        "russia":          "IMOEX.ME",
        "mexico":          "^MXX",
        "argentina":       "^MERV",
        "new_zealand":     "^NZ50",
        "malaysia":        "^KLSE",
        "indonesia":       "^JKSE",
        "thailand":        "^SET.BK",
        "israel":          "^TA125.TA",
        "saudi_arabia":    "^TASI.SR",
        "south_africa":    "^J203",
    }
    key = _resolve_country(country)
    if key in _INDEX_MAP:
        return _INDEX_MAP[key]
    raise ValueError(f"No default index defined for country: '{country}'")
