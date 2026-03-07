# market_tickers/core.py
# v0.4.0 — Damodaran 2026 primary dataset + YF2017 per-country CSV fallback

import re
import difflib
from typing import List, Dict, Optional

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
    if dot != -1 and len(t) - dot <= 4:   # .NS, .BO, .L, .PA etc.
        t = t[:dot]
    return _normalize(t)


# Suffix preference for tie-breaking when multiple tickers share a base
_SUFFIX_PREF = {"": 0, "ns": 1, "l": 2, "to": 3, "ax": 4}


# Common index aliases
INDEX_ALIASES = {
    "nifty":      "^NSEI",
    "nifty50":    "^NSEI",
    "nifty 50":   "^NSEI",
    "sensex":     "^BSESN",
    "bse":        "^BSESN",
    "sp500":      "^GSPC",
    "s&p500":     "^GSPC",
    "sandp500":   "^GSPC",
    "s&p 500":    "^GSPC",
    "dow":        "^DJI",
    "dowjones":   "^DJI",
    "nasdaq":     "^IXIC",
    "nasdaq100":  "^NDX",
    "nasdaq 100": "^NDX",
    "russell2000":"^RUT",
    "vix":        "^VIX",
    "dax":        "^GDAXI",
    "ftse":       "^FTSE",
    "ftse100":    "^FTSE",
    "cac40":      "^FCHI",
    "cac 40":     "^FCHI",
    "nikkei":     "^N225",
    "nikkei225":  "^N225",
    "hangseng":   "^HSI",
    "hang seng":  "^HSI",
    "kospi":      "^KS11",
    "asx200":     "^AXJO",
    "asx 200":    "^AXJO",
    "bitcoin":    "BTC-USD",
    "btc":        "BTC-USD",
    "ethereum":   "ETH-USD",
    "eth":        "ETH-USD",
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
    4-tier matching pipeline against a list of rows.

    Tiers
    -----
    1. Exact name   – normalized full company name equals query
    2. Exact ticker – base ticker (suffix stripped) equals query
    3. Prefix       – normalized name starts with query  (single match required)
    4. Contains     – query is substring of normalized name
       - Single match → return it
       - Multiple matches + fuzzy=True → return shortest name (most specific)
       - Multiple matches + fuzzy=False → raise KeyError
    5. Fuzzy (difflib) – only when fuzzy=True and nothing found above
       Catches common typos like "Relience" → "Reliance Industries"

    Returns ticker string on unambiguous match.
    Raises KeyError on unresolvable ambiguity.
    Returns None if nothing matches.
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
            # Among multiple contains matches, prefer the entry where the query
            # covers the largest fraction of the name (query fills most of the name).
            # This favours shorter, more focused names AND preserves dataset order
            # for equal scores (US-listed ETFs/stocks appear first in YF2017 CSVs).
            def _match_fraction(r):
                nlen = len(_normalize(r["name"]))
                return -len(norm_name) / nlen if nlen else 0   # negative = sort descending
            contains.sort(key=_match_fraction)
            return contains[0]["ticker"]
        raise KeyError(
            f"Multiple tickers found for '{raw_name}'. Please refine your query."
        )

    # 5. Fuzzy / typo matching — token-based difflib
    #
    # Compares query against each meaningful word token in the name, not the
    # full normalized string. Splits on spaces AND punctuation so that
    # "Amazon.com, Inc." → tokens ["amazon", "com", "inc"] and
    # "amazn" vs "amazon" → 0.909 ✓
    if fuzzy:
        FUZZY_CUTOFF = 0.82

        scored: list = []
        for r in valid:
            # Split on whitespace AND punctuation (dot, comma, hyphen, slash)
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
            # Highest token-score wins; ties broken by dataset order
            scored.sort(key=lambda x: -x[0])
            return scored[0][1]["ticker"]

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_ticker(
    name: str,
    country: Optional[str] = None,
    category: str = "stock",
    fuzzy: bool = True,
) -> str:
    """
    Get Yahoo Finance ticker by human-readable name or code.

    Lookup order for stocks
    -----------------------
    1. Damodaran 2026 dataset (primary — 41 k companies, 132 countries)
    2. Legacy YF2017 per-country CSV (fallback)
       For India: only .NS tickers are considered (BSE/.BO excluded)

    Parameters
    ----------
    name    : Human-readable name or ticker code (e.g. "Reliance Industries")
    country : Required for stocks  (e.g. "india", "usa", "uk", "germany")
    category: One of: stock | index | etf | currency
    fuzzy   : Enable approximate / typo-tolerant matching (default True)
    """
    if not name:
        raise ValueError("name cannot be empty")

    raw_name  = name.strip()
    norm_name = _normalize(raw_name.lower().replace("=x", ""))

    # ── Index ──────────────────────────────────────────────────────────────────
    if category == "index":
        alias = INDEX_ALIASES.get(norm_name) or INDEX_ALIASES.get(raw_name.lower())
        if alias:
            return alias
        rows = load_indices()
        result = _match_rows(norm_name, raw_name, rows, fuzzy=fuzzy)
        if result:
            return result
        raise KeyError(f"Index not found: '{raw_name}'")

    # ── ETF ────────────────────────────────────────────────────────────────────
    if category == "etf":
        rows = load_etfs()
        result = _match_rows(norm_name, raw_name, rows, fuzzy=fuzzy)
        if result:
            return result
        raise KeyError(f"ETF not found: '{raw_name}'")

    # ── Currency ───────────────────────────────────────────────────────────────
    if category == "currency":
        # Guaranteed FX fallback — standard Yahoo Finance 6-letter pair
        if len(norm_name) == 6 and norm_name.isalpha():
            return f"{norm_name.upper()}=X"
        rows = load_currencies()
        result = _match_rows(norm_name, raw_name, rows, fuzzy=fuzzy)
        if result:
            return result
        raise KeyError(f"Currency not found: '{raw_name}'")

    # ── Stock ──────────────────────────────────────────────────────────────────
    if category == "stock":
        if not country:
            raise ValueError("country is required for stock lookup")

        # Resolve country aliases
        _ALIASES = {
            "us":  "united_states",
            "usa": "united_states",
            "uk":  "united_kingdom",
            "gb":  "united_kingdom",
            "hk":  "hong_kong",
            "nz":  "new_zealand",
            "kr":  "south_korea",
            "uae": "united_arab_emirates",
        }
        country_clean = _ALIASES.get(country.lower().strip(), country.lower().strip())
        is_india = country_clean == "india"

        # Step 1: Damodaran 2026 (primary) — country-scoped
        dam_rows = get_damodaran_rows_for_country(country_clean)
        if dam_rows:
            result = _match_rows(norm_name, raw_name, dam_rows, fuzzy=fuzzy)
            if result:
                return result

        # Step 2: Legacy YF2017 per-country CSV (fallback)
        legacy_rows = load_stocks(country_clean)
        if is_india and legacy_rows:
            legacy_rows = [r for r in legacy_rows if r.get("ticker", "").endswith(".NS")]
        if legacy_rows:
            result = _match_rows(norm_name, raw_name, legacy_rows, fuzzy=fuzzy)
            if result:
                return result

        raise KeyError(
            f"Ticker not found for '{raw_name}' in country '{country}'. "
            f"Searched Damodaran 2026 ({len(dam_rows)} rows) and "
            f"legacy dataset ({len(legacy_rows)} rows)."
        )

    raise ValueError(
        f"Unknown category: '{category}'. Use one of: stock, index, etf, currency"
    )


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
    country  : Required for category="stock"
    category : One of: stock | index | etf | currency
    limit    : Max results to return (default 10)
    """
    if not query:
        raise ValueError("query cannot be empty")

    norm_query = _normalize(query)

    # Load the right row set
    if category == "stock":
        if not country:
            raise ValueError("country is required for stock search")
        _ALIASES = {
            "us": "united_states", "usa": "united_states",
            "uk": "united_kingdom", "gb": "united_kingdom",
            "hk": "hong_kong", "nz": "new_zealand", "kr": "south_korea",
        }
        country_clean = _ALIASES.get(country.lower().strip(), country.lower().strip())
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

    # Match: ticker exact → name contains → ticker contains
    results = []
    seen: set = set()

    for r in valid:
        t = r["ticker"]
        if t in seen:
            continue
        norm_name   = _normalize(r["name"])
        norm_ticker = _normalize(t.replace("=x", ""))
        if norm_query in norm_name or norm_query in norm_ticker:
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
    country    : str  country key (e.g. "india", "united_states", "japan", "uk")
    """
    _ALIASES = {
        "us": "united_states", "usa": "united_states",
        "uk": "united_kingdom", "gb": "united_kingdom",
        "hk": "hong_kong",
    }
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
    key = _ALIASES.get(country.lower().strip(), country.lower().strip().replace(" ", "_"))
    if key in _INDEX_MAP:
        return _INDEX_MAP[key]
    raise ValueError(f"No default index defined for country: '{country}'")
