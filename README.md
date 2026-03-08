# market-tickers v0.4.1

> **Human-friendly stock, index, ETF and currency names → Yahoo Finance tickers**  
> Faster, smarter and self-updating.

[![PyPI version](https://badge.fury.io/py/market-tickers.svg)](https://pypi.org/project/market-tickers/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

---

## What's new in v0.4.1

| Feature | v0.4.0 | v0.4.1 |
|---|---|---|
| Batch lookup (list in → list out) | ❌ | ✅ |
| Case-insensitive countries | ❌ | ✅ (`"United States"`, `"USA"`, `"usa"` all work) |
| Currency slash format | ❌ | ✅ (`"USD/INR"`, `"USDINR"`, `"usdinr"` all work) |
| Cleaned currency dataset | ❌ | ✅ (removed 400+ junk/invalid entries) |
| `search_tickers()` | ✅ | ✅ |
| `list_countries()` | ✅ | ✅ |
| Fuzzy / typo matching | ✅ | ✅ |

---

## Installation

```bash
pip install market-tickers
```

With auto-updater support:

```bash
pip install market-tickers[updater]   # adds yfinance + requests
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
get_ticker("USD/INR", category="currency")            # → 'USDINR=X'  (slash format)
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

# ── Default index for a country ───────────────────────────────────────────
from market_tickers import get_default_index
get_default_index("anything", country="japan")        # → '^N225'
get_default_index("anything", country="uk")           # → '^FTSE'
```

---

## Batch Lookup

Pass a list instead of a single name — get a list back in the same order.  
Not-found names are silently skipped, so the result is always clean and ready for `yf.download()`.

```python
import yfinance as yf
from market_tickers import get_ticker

# ── Stocks ────────────────────────────────────────────────────────────────
companies = ["Reliance Industries", "TCS", "HDFC Bank", "Infosys"]
tickers = get_ticker(companies, country="india")
# → ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS']

yf.download(tickers, period="1y")   # plug straight in — no filtering needed

# ── Currencies ────────────────────────────────────────────────────────────
pairs = ["USD/INR", "EUR/USD", "GBP/JPY", "AUD/USD"]
tickers = get_ticker(pairs, category="currency")
# → ['USDINR=X', 'EURUSD=X', 'GBPJPY=X', 'AUDUSD=X']

# ── Indices ───────────────────────────────────────────────────────────────
indices = ["Nifty 50", "S&P 500", "NASDAQ 100", "DAX", "Nikkei 225"]
tickers = get_ticker(indices, category="index")
# → ['^NSEI', '^GSPC', '^NDX', '^GDAXI', '^N225']

# ── ETFs ──────────────────────────────────────────────────────────────────
etfs = ["SPY", "QQQ", "ARKK", "GLD", "VTI"]
tickers = get_ticker(etfs, category="etf")
# → ['SPY', 'QQQ', 'ARKK', 'GLD', 'VTI']

# ── Not-found names are skipped, not None ─────────────────────────────────
tickers = get_ticker(["Apple Inc.", "FakeXYZ999", "Microsoft"], country="usa")
# → ['AAPL', 'MSFT']   ← FakeXYZ999 silently dropped
```

---

## Case-Insensitive Countries

Country names are fully case-insensitive and accept spaces or underscores:

```python
# All of these resolve identically
get_ticker("Microsoft", country="United States")   # → 'MSFT'
get_ticker("Microsoft", country="united states")   # → 'MSFT'
get_ticker("Microsoft", country="united_states")   # → 'MSFT'
get_ticker("Microsoft", country="USA")             # → 'MSFT'
get_ticker("Microsoft", country="usa")             # → 'MSFT'

get_default_index("x", country="South Korea")      # → '^KS11'
get_default_index("x", country="south korea")      # → '^KS11'
get_default_index("x", country="south_korea")      # → '^KS11'
```

---

## Currency Format Flexibility

Currencies accept any reasonable input format — useful when reading pairs straight from Excel or CSV files:

```python
get_ticker("USDINR",   category="currency")   # → 'USDINR=X'
get_ticker("USD/INR",  category="currency")   # → 'USDINR=X'  ← Excel/CSV format
get_ticker("usdinr",   category="currency")   # → 'USDINR=X'
get_ticker("usd/inr",  category="currency")   # → 'USDINR=X'
get_ticker("USDINR=X", category="currency")   # → 'USDINR=X'  ← already a ticker

# Batch from Excel column
pairs = ["USD/INR", "EUR/USD", "GBP/JPY"]
get_ticker(pairs, category="currency")
# → ['USDINR=X', 'EURUSD=X', 'GBPJPY=X']
```

---

## Auto-Update Data

Keep your ticker database fresh by pulling from official exchange sources:

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
# Recommended — live fetch India/USA/UK + dedup all countries
python -m market_tickers.updater --live --dedup

# Update only India and USA stocks
python -m market_tickers.updater --countries india united_states

# Only refresh indices and ETFs
python -m market_tickers.updater --no-stocks

# Dedup all country files (remove duplicate exchange listings, no network needed)
python -m market_tickers.updater --dedup
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

# Single stock
ticker = get_ticker("Infosys", country="india")      # → 'INFY.NS'
data = yf.download(ticker, period="1mo")

# Batch — plug directly into yfinance, no filtering needed
companies = ["Reliance Industries", "TCS", "HDFC Bank", "Infosys"]
tickers = get_ticker(companies, country="india")
data = yf.download(tickers, period="1y")

# Mixed asset types
indices   = get_ticker(["Nifty 50", "S&P 500"], category="index")
currencies = get_ticker(["USD/INR", "EUR/USD"], category="currency")
```

---

## API Reference

### `get_ticker(name, country=None, category="stock", fuzzy=True)`

Accepts a **single name** (returns `str`) or a **list of names** (returns `list[str]`).

| Param | Type | Description |
|---|---|---|
| `name` | `str` or `list[str]` | Name(s), ticker code(s), or alias(es) |
| `country` | `str \| None` | Required for `category="stock"`. Case-insensitive. |
| `category` | `str` | `"stock"` \| `"index"` \| `"etf"` \| `"currency"` |
| `fuzzy` | `bool` | Enable approximate / typo-tolerant matching (default `True`) |

Single name → raises `KeyError` if not found.  
List of names → not-found entries are silently skipped (never raises).

---

### `search_tickers(query, country=None, category="stock", limit=10)`

Returns a list of matching ticker dicts: `[{"ticker": ..., "name": ..., ...}]`

---

### `get_default_index(stock_name, country="india")`

Returns the benchmark index ticker for a country. Country name is case-insensitive.

---

### `list_countries()`

Returns a sorted list of all countries with stock data.

---

### `update_data(countries=None, update_etfs=True, update_indices=True, verbose=True)`

Pulls fresh data from official exchange sources and updates the bundled CSVs.  
Requires: `pip install market-tickers[updater]`

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

Country names also accept spaces and any casing — `"South Korea"`, `"south korea"`, `"south_korea"` all work.

---

## Performance

- **First call**: reads data from disk, builds normalised lookup tables, caches in memory.
- **Subsequent calls (same category/country)**: pure dict lookup — O(1), microseconds.
- **Batch lookup**: country data loaded once and reused across all names in the list.
- **Fuzzy fallback**: token-based difflib, only triggered when exact/prefix/contains matching fails.

---

## License

MIT © Vedant Wade
