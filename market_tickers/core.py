# market_tickers/core.py

from market_tickers.loaders import (
    load_india_stocks,
    load_usa_stocks,
    load_indices,
)


def _normalize(text):
    return (
        text.lower()
        .replace("&", "and")
        .replace("-", "")
        .replace(" ", "")
    )


def _build_india_ticker(symbol, exchange):
    return f"{symbol}.NS" if exchange == "NSE" else f"{symbol}.BO"


# Load once (fast)
_INDIA_STOCKS = load_india_stocks()
_USA_STOCKS = load_usa_stocks()
_INDICES = load_indices()


def get_ticker(name: str) -> str:
    norm = _normalize(name)

    # Indices
    for row in _INDICES:
        if _normalize(row["name"]) == norm:
            return row["ticker"]

    # India stocks
    for row in _INDIA_STOCKS:
        if _normalize(row["name"]) == norm:
            return _build_india_ticker(row["symbol"], row["exchange"])

    # USA stocks
    for row in _USA_STOCKS:
        if _normalize(row["name"]) == norm:
            return row["symbol"]

    raise ValueError(f"Ticker not found for: {name}")


def get_default_index(stock_name: str) -> str:
    norm = _normalize(stock_name)

    for row in _INDIA_STOCKS + _USA_STOCKS:
        if _normalize(row["name"]) == norm:
            index_name = row["default_index"]
            return get_ticker(index_name)

    raise ValueError(f"No default index found for: {stock_name}")
