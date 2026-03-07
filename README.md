# market-tickers v0.4.0

> **Human-friendly stock, index, ETF and currency names → Yahoo Finance tickers**  
> Faster, smarter and self-updating.

[![PyPI version](https://badge.fury.io/py/market-tickers.svg)](https://pypi.org/project/market-tickers/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

---

## What's new in v0.4.0

| Feature | v0.3.x | v0.4.0 |
|---|---|---|
| In-memory cache | ❌ | ✅ (zero disk I/O on repeated calls) |
| Fuzzy matching | ❌ | ✅ (handles typos) |
| `search_tickers()` | ❌ | ✅ |
| `list_countries()` | ❌ | ✅ |
| `update_data()` | ❌ | ✅ (pulls from yfinance) |
| Index aliases | 10 | **70+** |
| Default index countries | 2 | **35+** |
| ETF list | ~10 | **90+** |
| Country aliases (`uk`, `usa`) | ❌ | ✅ |

---

## Installation

```bash
pip install market-tickers
```

With auto-updater support:

```bash
pip install market-tickers[updater]   # adds yfinance
```

---

## Quick Start

```python
from market_tickers import get_ticker, search_tickers, list_countries, update_data

# ── Stocks ────────────────────────────────────────────────────────────────
get_ticker("Reliance Industries", country="india")    # → 'RELIANCE.NS'
get_ticker("Apple", country="usa")                    # → 'AAPL'
get_ticker("HSBC", country="uk")                      # → 'HSBA.L'
get_ticker("Volkswagen", country="germany")           # → 'VOW3.DE'
get_ticker("Samsung", country="south_korea")          # → '005930.KS'
get_ticker("Tencent", country="hong_kong")            # → '0700.HK'

# ── Indices ────────────────────────────────────────────────────────────────
get_ticker("Nifty 50", category="index")              # → '^NSEI'
get_ticker("S&P 500", category="index")               # → '^GSPC'
get_ticker("NASDAQ 100", category="index")            # → '^NDX'
get_ticker("DAX", category="index")                   # → '^GDAXI'
get_ticker("Nikkei 225", category="index")            # → '^N225'
get_ticker("Hang Seng", category="index")             # → '^HSI'
get_ticker("vix", category="index")                   # → '^VIX'  (alias)
get_ticker("bitcoin", category="index")               # → 'BTC-USD'

# ── ETFs ──────────────────────────────────────────────────────────────────
get_ticker("SPDR S&P 500", category="etf")            # → 'SPY'
get_ticker("QQQ", category="etf")                     # → 'QQQ'
get_ticker("ARK Innovation", category="etf")          # → 'ARKK'

# ── Currencies ────────────────────────────────────────────────────────────
get_ticker("USDINR", category="currency")             # → 'USDINR=X'
get_ticker("EURUSD", category="currency")             # → 'EURUSD=X'
get_ticker("GBPJPY", category="currency")             # → 'GBPJPY=X'

# ── Fuzzy matching (handles typos) ────────────────────────────────────────
get_ticker("Relience", country="india")               # → 'RELIANCE.NS'
get_ticker("Amazn", country="usa")                    # → 'AMZN'

# ── Search ────────────────────────────────────────────────────────────────
results = search_tickers("tata", country="india")
# → [{'ticker': 'TATAMOTORS.NS', 'name': 'Tata Motors', ...}, ...]

# ── List available countries ───────────────────────────────────────────────
list_countries()
# → ['argentina', 'australia', 'austria', ..., 'venezuela']

# ── Default index for a stock ────────────────────────────────────────────
from market_tickers import get_default_index
get_default_index("anything", country="japan")        # → '^N225'
get_default_index("anything", country="uk")           # → '^FTSE'
```

---

## Auto-Update Data

Keep your ticker database fresh by pulling from Yahoo Finance:

### In Python

```python
from market_tickers import update_data

# Update everything
update_data()

# Update only specific countries
update_data(countries=["india", "usa", "uk"])

# Only refresh indices and ETFs (fastest)
update_data(countries=[], update_etfs=True, update_indices=True)
```

### From the command line

```bash
# Update all data
python -m market_tickers.updater

# Update only India and USA stocks
python -m market_tickers.updater --countries india united_states

# Only refresh indices and ETFs
python -m market_tickers.updater --no-stocks

# Skip ETFs
python -m market_tickers.updater --no-etfs
```

### Automate with cron (Linux/Mac)

```cron
# Run every Sunday at 2 AM
0 2 * * 0 /usr/bin/python3 -m market_tickers.updater --no-stocks >> ~/market_tickers_update.log 2>&1
```

---

## Integration with yfinance

```python
import yfinance as yf
from market_tickers import get_ticker

# Get live stock data using a human name
ticker = get_ticker("Infosys", country="india")   # → 'INFY.NS'
data = yf.download(ticker, period="1mo")

# Or use it in a list
companies = ["Reliance Industries", "TCS", "HDFC Bank", "Infosys"]
tickers = [get_ticker(c, country="india") for c in companies]
data = yf.download(tickers, period="1y")
```

---

## API Reference

### `get_ticker(name, country=None, category="stock", fuzzy=True)`

Returns a single Yahoo Finance ticker string.

| Param | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable name, ticker code, or alias |
| `country` | `str \| None` | Required for `category="stock"` |
| `category` | `str` | `"stock"` \| `"index"` \| `"etf"` \| `"currency"` |
| `fuzzy` | `bool` | Enable approximate matching (default `True`) |

Raises `KeyError` if not found.  
Raises `ValueError` on invalid arguments.

---

### `search_tickers(query, country=None, category="stock", limit=10)`

Returns a list of matching ticker dicts: `[{"ticker": ..., "name": ..., ...}]`

---

### `get_default_index(stock_name, country="india")`

Returns the benchmark index ticker for a country.

---

### `list_countries()`

Returns a sorted list of all countries with stock data.

---

### `update_data(countries=None, update_etfs=True, update_indices=True, verbose=True)`

Pulls fresh data from Yahoo Finance and updates the bundled CSVs.  
Requires `yfinance` to be installed.

---

## Supported Countries (stocks)

argentina · australia · austria · belgium · brazil · canada · china · denmark · estonia · finland · france · germany · greece · hong_kong · iceland · india · indonesia · ireland · israel · italy · latvia · lithuania · malaysia · mexico · netherlands · new_zealand · norway · portugal · qatar · russia · singapore · south_korea · spain · sweden · switzerland · taiwan · thailand · turkey · united_kingdom · united_states · venezuela

**Country aliases** (can be used instead of full names):

| Alias | Resolves to |
|---|---|
| `us`, `usa` | `united_states` |
| `uk`, `gb` | `united_kingdom` |
| `hk` | `hong_kong` |
| `nz` | `new_zealand` |
| `kr` | `south_korea` |
| `uae` | `united_arab_emirates` |

---

## Performance

- **First call**: reads CSV from disk, builds normalised lookup tables, caches in memory.
- **Subsequent calls (same category/country)**: pure dict lookup — O(1), microseconds.
- **Fuzzy fallback**: only triggered when exact/prefix/contains matching fails.

---

## License

MIT © Vedant Wade
