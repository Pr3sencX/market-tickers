# market-tickers 📈

[![PyPI version](https://img.shields.io/pypi/v/market-tickers.svg)](https://pypi.org/project/market-tickers/)
[![Python versions](https://img.shields.io/pypi/pyversions/market-tickers.svg)](https://pypi.org/project/market-tickers/)
[![License](https://img.shields.io/pypi/l/market-tickers.svg)](https://github.com/Pr3sencX/market-tickers/blob/main/LICENSE)

A lightweight Python library to resolve **human-readable market names**
into **Yahoo Finance–compatible tickers**.

Designed for **accuracy, determinism, and safety**, with no guessing.

Supports:
- **Stocks**
- **Indices**
- **ETFs**
- **Currencies**

---

## Installation

```bash
pip install market-tickers
```

---

## Quick Start (New Version)

```python
from market_tickers import get

tickers = [
    get("Nvidia Corporation", country="us"),
    get("Intel Corporation", country="us"),
    get("Nifty 50"),
    get("Nasdaq 100"),
    get("S&P 500"),
    get("Dow Jones"),
]

print(tickers)
```

**Output**
```python
['NVDA', 'INTC', '^NSEI', '^NDX', '^GSPC', '^DJI']
```

---

## How Resolution Works

### Stocks
- Requires `country`
- Resolves to the **primary tradable equity**
- Automatically avoids funds, trusts, and derivative instruments

```python
get("Reliance Industries", country="india")   # RELIANCE.NS
get("Apple Inc", country="us")                # AAPL
```

---

### Indices (Strict & Dataset-Based)
- Resolved **only** from the built-in indices dataset
- No Yahoo Finance guessing
- Prevents numeric collisions

Resolution order:
1. Exact **Index Name**
2. Exact alias from **Fuzzy Names**
3. Controlled token similarity (safe threshold)

```python
get("Nifty 50")        # ^NSEI
get("Nasdaq 100")      # ^NDX
get("S&P 500")         # ^GSPC
```

If an index is not present in the dataset, an error is raised instead of guessing.

---

### ETFs
- Explicit ETF resolution
- Prevents ETFs from being mistaken for stocks or indices

```python
get("Vanguard S&P 500 ETF", category="etf")   # VOO
```

---

### Currencies
- Automatically detects FX pairs
- Returns Yahoo Finance–compatible symbols

```python
get("USDINR")   # USDINR=X
get("EURUSD")   # EURUSD=X
```

---

## Resolution Priority

When `category` is not specified, resolution happens in the following order:

```
Index → Stock → ETF → Currency
```

This guarantees:
- Indices never resolve as stocks
- ETFs do not override indices
- No unexpected or inactive Yahoo Finance symbols

---

## What Problems Does This Solve?

- ❌ No need to remember Yahoo Finance ticker formats  
- ❌ No browsing Yahoo Finance to find symbols  
- ❌ No accidental resolution to inactive or incorrect tickers  
- ❌ No fuzzy chaos for index names  

- ✅ Human-friendly inputs  
- ✅ Deterministic results  
- ✅ Dataset-driven behavior  
- ✅ Safe for automation and production use  

---

## Breaking Changes (Latest Version)

- Index resolution is now **strictly dataset-based**
- Removed implicit Yahoo Finance guessing for indices
- Improved handling of numeric index names (e.g. *50 vs 500*)
- Cleaner separation between stocks, indices, ETFs, and currencies

These changes significantly improve correctness and long-term stability.

---

## License

MIT
