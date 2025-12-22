import re
from typing import Optional

from market_tickers.loaders import (
    load_stocks,
    load_indices,
    load_etfs,
    load_currencies,
)

# ======================================================
# Helpers
# ======================================================

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _token_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _normalize_country(country: str) -> str:
    c = country.lower().strip()
    if c in ("us", "usa"):
        return "usa"
    if c in ("uk", "gb"):
        return "united_kingdom"
    if c == "nz":
        return "new_zealand"
    if c in ("kr", "korea", "south korea", "south_korea"):
        return "south_korea"
    return re.sub(r"[^a-z]", "", c)


# ======================================================
# Core resolver
# ======================================================

def get_ticker(
    name: str,
    country: Optional[str] = None,
    category: Optional[str] = None,
):
    if not name:
        raise ValueError("name is required")

    raw = name.strip()
    norm = _normalize(raw)
    tokens = _tokens(raw)

    # --------------------------------------------------
    # Currency shortcut
    # --------------------------------------------------
    if category in (None, "currency"):
        if len(norm) == 6 and norm.isalpha():
            return f"{norm.upper()}=X"

    if category is None:
        category = "stock"

    # ==================================================
    # ✅ INDEX — STRICTLY indices.csv ONLY
    # ==================================================
    if category == "index":
        rows = load_indices()

        best_ticker = None
        best_score = 0.0

        for r in rows:
            idx_name = r.get("Index Name", "")
            ticker = r.get("yfinance Ticker")
            fuzzy = r.get("Fuzzy Names", "")

            if not idx_name or not ticker:
                continue

            # 1️⃣ EXACT Index Name match (STRONGEST)
            if _normalize(idx_name) == norm:
                return ticker

            # 2️⃣ EXACT alias match (comma-separated)
            for alias in fuzzy.split(","):
                if _normalize(alias.strip()) == norm:
                    return ticker

            # 3️⃣ Controlled fuzzy (token similarity ≥ 0.75)
            score = _token_similarity(tokens, _tokens(idx_name))
            for alias in fuzzy.split(","):
                score = max(score, _token_similarity(tokens, _tokens(alias)))

            if score >= 0.75 and score > best_score:
                best_score = score
                best_ticker = ticker

        if best_ticker:
            return best_ticker

        raise KeyError(f"Index not found: {raw}")

    # ==================================================
    # STOCK
    # ==================================================
    if category == "stock":
        if not country:
            raise ValueError("country is required for stocks")

        rows = load_stocks(_normalize_country(country))
        matches = [r for r in rows if norm in _normalize(r["name"])]

        if not matches:
            raise KeyError(f"Stock not found: {raw}")

        # Prefer primary-looking tickers (shorter)
        matches.sort(key=lambda r: len(r["ticker"]))
        return matches[0]["ticker"]

    # ==================================================
    # ETF
    # ==================================================
    if category == "etf":
        for r in load_etfs():
            if _normalize(r["name"]) == norm:
                return r["ticker"]
            if tokens.issubset(_tokens(r["name"])):
                return r["ticker"]
        raise KeyError(f"ETF not found: {raw}")

    # ==================================================
    # CURRENCY
    # ==================================================
    if category == "currency":
        for r in load_currencies():
            if norm in _normalize(r["name"]):
                return r["ticker"]
        raise KeyError(f"Currency not found: {raw}")

    raise ValueError(f"Unknown category: {category}")


# ======================================================
# Smart wrapper — FINAL PRIORITY ORDER
# ======================================================

def get(name: str, country: Optional[str] = None, category: Optional[str] = None):
    if category:
        return get_ticker(name, country=country, category=category)

    # ✅ FINAL agreed priority
    for cat in ("index", "stock", "etf", "currency"):
        try:
            return get_ticker(name, country=country, category=cat)
        except Exception:
            pass

    raise KeyError(f"Ticker not found for: {name}")
