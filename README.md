# market-tickers 📈

[![PyPI version](https://img.shields.io/pypi/v/market-tickers.svg)](https://pypi.org/project/market-tickers/)
[![Python versions](https://img.shields.io/pypi/pyversions/market-tickers.svg)](https://pypi.org/project/market-tickers/)
[![License](https://img.shields.io/pypi/l/market-tickers.svg)](https://github.com/Pr3sencX/market-tickers/blob/main/LICENSE)

A lightweight Python library to resolve **human-readable market names**
into **Yahoo Finance–compatible tickers**.

Built to handle:
- Stocks
- Indices
- ETFs
- Currencies  
with **smart defaults and ambiguity protection**.

---

## Installation

```bash
pip install market-tickers
```

---

## Quick Start

```python
from market_tickers import get

print(get("Nifty"))                 # ^NSEI
print(get("Sensex"))               # ^BSESN
print(get("USDINR"))               # USDINR=X
print(get("Reliance Industries"))  # RELIANCE.NS
```

---

## What problems does this solve?

- No need to remember Yahoo Finance ticker formats
- Handles common aliases (Nifty, Sensex, SP500)
- Auto-detects currencies (USDINR → USDINR=X)
- Safe defaults with ambiguity protection

---

## License

MIT
