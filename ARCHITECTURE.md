# market-tickers — Project Architecture

## Directory Structure

```
market-tickers/
│
├── market_tickers/                  ← Python package
│   ├── __init__.py                  ← Public API exports
│   ├── core.py                      ← Resolver logic (get_ticker, search_tickers, get_default_index)
│   ├── loaders.py                   ← Data loading & in-memory caching
│   ├── updater.py                   ← CLI tool to refresh bundled CSVs
│   │
│   └── data/
│       ├── stocks/
│       │   ├── new_data/
│       │   │   └── new_stocks_data.xlsx   ← PRIMARY: Damodaran 2026 (41k companies, 132 countries)
│       │   ├── stocks_india.csv           ← FALLBACK: YF2017 legacy per-country CSVs
│       │   ├── stocks_united_states.csv
│       │   ├── stocks_germany.csv
│       │   └── ... (42 country files)
│       │
│       ├── indices/
│       │   ├── indices.csv               ← 80+ global indices
│       │   ├── indices_india.csv
│       │   ├── indices_usa.csv
│       │   └── indices_global.csv
│       │
│       ├── etfs/
│       │   └── etfs.csv                  ← 21k+ ETFs (YF2017)
│       │
│       └── currencies/
│           └── currencies.csv            ← 4k+ currency pairs (YF2017)
│
├── tests/
│   ├── test_core.py
│   ├── test_countries.py
│   ├── test_currency_etf.py
│   ├── test_fuzzy.py
│   ├── test_indices.py
│   └── test_search.py
│
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md
├── LICENSE
└── .gitignore
```

## Lookup Flow

```
get_ticker(name, country, category)
        │
        ├── category = "index"     → INDEX_ALIASES dict → indices.csv
        ├── category = "etf"       → etfs.csv
        ├── category = "currency"  → 6-char FX fallback → currencies.csv
        │
        └── category = "stock"
                │
                ├── Step 1: new_stocks_data.xlsx  (primary — Damodaran 2026)
                │          Lazy-loaded once, indexed by country + name + ticker
                │          4-tier match: exact name → exact ticker → prefix → contains
                │          fuzzy=True adds difflib typo matching as tier 5
                │
                └── Step 2: stocks_{country}.csv  (fallback — YF2017)
                           India: .NS tickers only (no .BO)
```

## Performance

- **First call**: xlsx loaded once, indexed into 3 hash maps (~1–2s for 41k rows)
- **Subsequent calls**: pure dict lookup — O(1), microseconds
- **Fuzzy fallback**: difflib runs only within the ~1–3k rows of the requested country

## Updating Data

```bash
# Recommended monthly run — live fetch India/USA/UK + dedup all countries
python -m market_tickers.updater --live --dedup

# Refresh indices and ETFs only (fastest, no network for stocks)
python -m market_tickers.updater --no-stocks
```
