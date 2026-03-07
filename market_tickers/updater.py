#!/usr/bin/env python3
"""
market_tickers/updater.py
=========================
Updates the bundled CSV data from official exchange sources.

STRATEGY
--------
  The old approach of validating every ticker against Yahoo Finance is
  impractical — 95,000 tickers across 49 countries hits rate limits fast
  and takes hours.

  The new approach:

  TIER 1 — Live sources (fast, complete, no validation needed):
    • India      → NSE official CSV  (updated daily, ~2,000 EQ stocks)
    • USA        → NASDAQ FTP files  (updated daily, ~6,000 common stocks)
    • UK         → Wikipedia FTSE 100 + 250 constituents

  TIER 2 — Dedup only (no network, instant):
    • Germany, France, and any country with multi-exchange inflation
    • Keeps only the canonical exchange suffix (.DE, .PA etc.)
    • No yfinance required, runs in milliseconds

  TIER 3 — yfinance validation (optional, slow, use sparingly):
    • Only when you explicitly pass --validate
    • Recommended for a single country at a time, not all 49

USAGE
-----
  # Recommended — update the three countries with live sources (< 30 sec):
  python -m market_tickers.updater --live

  # Update India only:
  python -m market_tickers.updater --countries india

  # Update India + USA only:
  python -m market_tickers.updater --countries india united_states

  # Dedup all countries (fix multi-exchange inflation, instant, no network):
  python -m market_tickers.updater --dedup

  # Full live fetch + dedup (recommended monthly run, < 1 min):
  python -m market_tickers.updater --live --dedup

  # Optional: yfinance validation for ONE country (slow, needs internet):
  python -m market_tickers.updater --countries india --validate

  # Update indices and ETFs only:
  python -m market_tickers.updater --no-stocks
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

PKG_DIR = Path(__file__).parent
DATA_DIR = PKG_DIR / "data"

# ---------------------------------------------------------------------------
# Canonical exchange suffix per country
# Used by --dedup to pick the right ticker when a company has multiple rows
# ---------------------------------------------------------------------------
CANONICAL_SUFFIX: Dict[str, List[str]] = {
    "india":          [".NS", ".BO"],      # prefer NSE, fallback BSE
    "germany":        [".DE", ".F"],       # prefer Xetra, fallback Frankfurt
    "france":         [".PA", ".F"],
    "united_kingdom": [".L"],
    "australia":      [".AX"],
    "brazil":         [".SA"],
    "canada":         [".TO", ".V", ".CN"],
    "china":          [".SS", ".SZ"],
    "hong_kong":      [".HK"],
    "singapore":      [".SI"],
    "south_korea":    [".KS", ".KQ"],
    "taiwan":         [".TW", ".TWO"],
    "thailand":       [".BK"],
    "malaysia":       [".KL"],
    "indonesia":      [".JK"],
    "new_zealand":    [".NZ"],
    "norway":         [".OL"],
    "sweden":         [".ST"],
    "denmark":        [".CO"],
    "finland":        [".HE"],
    "switzerland":    [".SW", ".VX"],
    "netherlands":    [".AS"],
    "belgium":        [".BR"],
    "austria":        [".VI"],
    "portugal":       [".LS"],
    "italy":          [".MI"],
    "spain":          [".MC"],
    "greece":         [".AT"],
    "turkey":         [".IS"],
    "russia":         [".ME"],
    "mexico":         [".MX"],
    "argentina":      [".BA"],
    "israel":         [".TA"],
    "qatar":          [".QA"],
    "venezuela":      [".CR"],
    "usa":            [""],               # no suffix for US tickers
}


def _log(msg: str, level: str = "INFO") -> None:
    icons = {"INFO": "  ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌"}
    print(f"{icons.get(level, '')} {msg}", flush=True)


def _require(pkg: str):
    try:
        return __import__(pkg)
    except ImportError:
        print(f"❌  '{pkg}' not installed.  Run:  pip install {pkg}", file=sys.stderr)
        sys.exit(1)


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen: Dict[str, Dict] = {}
    for row in rows:
        t = row.get("ticker", "").strip()
        if t:
            seen[t] = row
    out = list(seen.values())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    return len(out)


# ---------------------------------------------------------------------------
# TIER 2: Dedup — remove multi-exchange inflation instantly, no network
# ---------------------------------------------------------------------------

def _suffix_rank(ticker: str, preferred: List[str]) -> int:
    """Lower = more preferred. Returns 999 if no match."""
    for i, sfx in enumerate(preferred):
        if sfx == "":
            if "." not in ticker:
                return i
        elif ticker.endswith(sfx):
            return i
    return 999


def dedup_country(country: str) -> int:
    """
    Remove duplicate and junk tickers for a given country. No network needed.

    Three strategies depending on the country:

    INDIA — ticker-base grouping + segment-code removal
      NSE and BSE use the same symbol for the same company, so
      RELIANCE.NS and RELIANCE.BO share base "RELIANCE".
      We group by base and keep .NS, falling back to .BO.
      Also strips junk NSE segment codes (-EQ, -BE, -BZ etc.)
      and mutual fund codes. Remaining .BO-only entries are kept
      (companies listed only on BSE, no NSE listing — legitimate).

    SUFFIX-FILTER countries (Germany, France, Thailand etc.)
      These datasets include every regional exchange for the same stock.
      We keep only the canonical suffix (.DE for Germany, .PA for France etc.)
      A company without the canonical suffix keeps its best available listing.

    USA — preferred-share / warrant removal only
      US tickers already have no exchange suffix. We just strip derivatives
      (BAC-PL, BAC-PW, -WI, -WS etc.) that are not common stock.

    All other countries — keep as-is (already single-exchange or small enough).
    """
    csv_path = DATA_DIR / "stocks" / f"stocks_{country}.csv"
    rows = _read_csv(csv_path)
    if not rows:
        return 0

    fieldnames = list(rows[0].keys())
    before = len(rows)

    # ── INDIA: segment-code strip + ticker-base dedup ─────────────────────
    if country == "india":
        BAD_SEGS = re.compile(
            r"-(EQ|BE|BZ|IL|SM|IT|BT|BL|RL|IQ|P1|P2|"
            r"SO|SQ|SL|SP|SI|ST|MF)\.",
            re.IGNORECASE,
        )
        rows = [r for r in rows if not BAD_SEGS.search(r.get("ticker", ""))]

        # Group by ticker base (RELIANCE from RELIANCE.NS / RELIANCE.BO)
        base_groups: Dict[str, List[Dict]] = defaultdict(list)
        for r in rows:
            t = r.get("ticker", "")
            base = t.rsplit(".", 1)[0] if "." in t else t
            base_groups[base].append(r)

        deduped = []
        for base, group in base_groups.items():
            if len(group) == 1:
                deduped.append(group[0])
            else:
                # Prefer .NS → .BO → anything
                ns = [r for r in group if r["ticker"].endswith(".NS")]
                bo = [r for r in group if r["ticker"].endswith(".BO")]
                deduped.append(ns[0] if ns else bo[0] if bo else group[0])
        rows = deduped

    # ── USA: strip non-common-stock derivatives ───────────────────────────
    elif country == "usa":
        def _is_derivative(ticker: str) -> bool:
            t = ticker.upper()
            if re.search(r"-P[A-Z]{0,2}$", t):       return True  # preferred
            if re.search(r"-W[SIBT]?$",    t):       return True  # warrants
            if t.endswith("-U"):                      return True  # units
            if t.endswith("-R") or t.endswith("-RI"): return True  # rights
            return False
        rows = [r for r in rows if not _is_derivative(r.get("ticker", ""))]

    # ── SUFFIX-FILTER countries: keep only canonical exchange suffix ───────
    elif country in CANONICAL_SUFFIX and CANONICAL_SUFFIX[country][0] != "":
        canonical = CANONICAL_SUFFIX[country]   # ordered list, first = most preferred

        # Separate rows by whether they match a canonical suffix
        canonical_rows = [
            r for r in rows
            if any(r.get("ticker", "").endswith(s) for s in canonical)
        ]
        # For small countries where everything is already one exchange, skip
        non_canonical = [
            r for r in rows
            if not any(r.get("ticker", "").endswith(s) for s in canonical)
        ]

        if canonical_rows:
            # If we have canonical entries, drop all non-canonical
            rows = canonical_rows
        # else: country only has non-canonical entries — keep everything

        # Within canonical rows, further dedup by ticker base
        # (e.g. Germany: ADS.DE and ADS1.DE are different share classes — keep both;
        #  but ADS.DE and ADS.BE in the canonical set shouldn't happen after filter above)

    n = _write_csv(csv_path, rows, fieldnames)
    removed = before - n
    if removed:
        _log(f"{country}: {before:>6} → {n:>6} rows  (-{removed} duplicates/junk)", "OK")
    else:
        _log(f"{country}: {n:>6} rows  (already clean)", "OK")
    return n


# ---------------------------------------------------------------------------
# TIER 1: Live fetch — India, USA, UK
# ---------------------------------------------------------------------------

def fetch_nse_india() -> List[Dict]:
    """
    Fetch all NSE EQ-series stocks from NSE's official daily CSV.
    No yfinance required. Returns ~2,000 clean rows.
    """
    requests_mod = _require("requests")
    _log("Fetching NSE equity list from nseindia.com ...")
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }
    try:
        resp = requests_mod.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        _log(f"NSE fetch failed: {e}", "ERR")
        _log("Keeping existing India data unchanged.", "WARN")
        return []

    rows_out = []
    reader = csv.DictReader(
        io.StringIO(resp.content.decode("utf-8", errors="replace"))
    )
    for row in reader:
        symbol = row.get("SYMBOL", "").strip()
        name   = row.get("NAME OF COMPANY", "").strip()
        series = row.get("SERIES", "").strip()
        if not symbol or not name or series != "EQ":
            continue
        rows_out.append({
            "ticker":        f"{symbol}.NS",
            "name":          name,
            "exchange":      "NSI",
            "category name": "",
            "country":       "India",
        })
    _log(f"NSE: {len(rows_out)} EQ-series stocks", "OK")
    return rows_out


def fetch_usa_stocks() -> List[Dict]:
    """
    Fetch all common stocks from NASDAQ's official daily FTP files.
    Filters out ETFs, test issues, preferred shares, warrants, rights.
    No yfinance required. Returns ~6,000–7,000 rows.
    """
    requests_mod = _require("requests")
    _log("Fetching US stocks from NASDAQ FTP ...")
    base = "https://ftp.nasdaqtrader.com/dynamic/SymDir/"
    rows_out: List[Dict] = []

    for filename, exchange in [("nasdaqlisted.txt", "NAS"), ("otherlisted.txt", None)]:
        try:
            resp = requests_mod.get(base + filename, timeout=30)
            resp.raise_for_status()
            lines = resp.text.splitlines()
        except Exception as e:
            _log(f"Failed to fetch {filename}: {e}", "WARN")
            continue

        for line in lines[1:]:
            if line.startswith("File Creation Time"):
                continue
            p = line.split("|")

            if filename == "nasdaqlisted.txt":
                # Symbol | Security Name | Market Category | Test Issue | Fin Status | Round Lot | ETF | NextShares
                if len(p) < 7:
                    continue
                symbol, name, is_etf, test = p[0].strip(), p[1].strip(), p[6].strip(), p[3].strip()
                exch = "NAS"
            else:
                # ACT Symbol | Security Name | Exchange | CQS Symbol | ETF | Round Lot | Test Issue | NASDAQ Symbol
                if len(p) < 7:
                    continue
                symbol, name, is_etf, test = p[0].strip(), p[1].strip(), p[4].strip(), p[6].strip()
                exch = p[2].strip() or "NYSE"

            if not symbol or test == "Y" or is_etf == "Y":
                continue
            # Drop preferred shares, warrants, rights, when-issued, units
            t = symbol.upper()
            if re.search(r"-P[A-Z]{0,2}$", t):  continue
            if re.search(r"-W[SIBT]?$",    t):  continue
            if t.endswith("-U"):               continue
            if t.endswith("-R") or t.endswith("-RI"): continue

            rows_out.append({
                "ticker":        symbol,
                "name":          name,
                "exchange":      exch,
                "category name": "",
                "country":       "United States",
            })

    _log(f"USA: {len(rows_out)} common stocks", "OK")
    return rows_out


def fetch_uk_stocks() -> List[Dict]:
    """
    Fetch FTSE 100 + FTSE 250 constituents from Wikipedia.
    No yfinance required. Returns ~350 rows.
    """
    _require("pandas")
    _log("Fetching FTSE 100 + 250 from Wikipedia ...")
    rows_out: List[Dict] = []

    for url, label in [
        ("https://en.wikipedia.org/wiki/FTSE_100_Index", "FTSE 100"),
        ("https://en.wikipedia.org/wiki/FTSE_250_Index", "FTSE 250"),
    ]:
        try:
            import pandas as pd
            tables = pd.read_html(url)
        except Exception as e:
            _log(f"Wikipedia {label} failed: {e}", "WARN")
            continue

        found = 0
        for table in tables:
            cols = [str(c).strip() for c in table.columns]
            t_col = next((c for c in cols if "ticker" in c.lower()), None)
            n_col = next((c for c in cols if "company" in c.lower()), None)
            if not t_col or not n_col:
                continue
            for _, row in table.iterrows():
                sym  = re.sub(r"\[.*?\]|\*|\s", "", str(row[t_col]).strip())
                name = str(row[n_col]).strip()
                if not sym or sym == "nan" or not name or name == "nan":
                    continue
                rows_out.append({
                    "ticker":        f"{sym}.L",
                    "name":          name,
                    "exchange":      "LSE",
                    "category name": "",
                    "country":       "United Kingdom",
                })
                found += 1
            if found:
                break
        _log(f"Wikipedia {label}: {found} stocks", "OK")

    return rows_out


# ---------------------------------------------------------------------------
# TIER 3: Optional yfinance validation (single country, explicit opt-in)
# ---------------------------------------------------------------------------

def validate_country_yf(country: str) -> int:
    """
    Validate existing tickers for ONE country against Yahoo Finance.
    Removes any ticker that returns no price data (delisted/dead).

    This is slow — use only for targeted cleanup, not bulk runs.
    Rate limit tip: yfinance allows ~2,000 tickers/hour reliably.
    For large countries (Germany 21K, France 11K), run --dedup first,
    then validate the smaller deduplicated file.
    """
    yf = _require("yfinance")
    csv_path = DATA_DIR / "stocks" / f"stocks_{country}.csv"
    existing = _read_csv(csv_path)
    if not existing:
        _log(f"No data for '{country}'.", "WARN")
        return 0

    fieldnames = list(existing[0].keys())
    tickers = [r["ticker"] for r in existing if r.get("ticker")]
    total = len(tickers)

    _log(f"Validating {total} tickers for {country} via yfinance ...")
    _log(f"Estimated time: ~{total // 200 + 1} minutes (200 tickers/min)", "INFO")

    active: set = set()
    chunk_size = 100
    for i in range(0, total, chunk_size):
        chunk = tickers[i: i + chunk_size]
        pct = int((i / total) * 100)
        print(f"\r   {i}/{total} ({pct}%)...", end="", flush=True)
        try:
            data = yf.download(
                chunk, period="5d", progress=False,
                auto_adjust=True, threads=True,
            )
            if not data.empty:
                if hasattr(data.columns, "levels"):
                    active.update(data.columns.get_level_values(1))
                else:
                    active.update(chunk)
            time.sleep(0.4)
        except Exception:
            active.update(chunk)   # on error, keep all
    print(f"\r   {total}/{total} (100%)          ")

    filtered = [r for r in existing if r.get("ticker") in active]
    removed = total - len(filtered)
    _log(f"{country}: {total} → {len(filtered)} (removed {removed} delisted)", "OK")
    return _write_csv(csv_path, filtered, fieldnames)


# ---------------------------------------------------------------------------
# Static data: Indices and curated ETFs
# ---------------------------------------------------------------------------

def update_indices() -> int:
    INDICES = [
        # USA
        ("^GSPC","S&P 500","US"), ("^DJI","Dow Jones Industrial Average","US"),
        ("^IXIC","NASDAQ Composite","US"), ("^NDX","NASDAQ 100","US"),
        ("^RUT","Russell 2000","US"), ("^VIX","CBOE Volatility Index","US"),
        ("^MID","S&P MidCap 400","US"), ("^SP600","S&P SmallCap 600","US"),
        # India
        ("^NSEI","Nifty 50","IN"), ("^BSESN","BSE Sensex","IN"),
        ("^NSEBANK","Nifty Bank","IN"), ("^CNXIT","Nifty IT","IN"),
        ("^NSEMDCP50","Nifty Midcap 50","IN"), ("^CNXAUTO","Nifty Auto","IN"),
        ("^CNXFMCG","Nifty FMCG","IN"), ("^CNXPHARMA","Nifty Pharma","IN"),
        ("^CNXMETAL","Nifty Metal","IN"), ("^CNXREALTY","Nifty Realty","IN"),
        ("^CNXSMALLCAP","Nifty Smallcap 100","IN"),
        # Europe
        ("^FTSE","FTSE 100","GB"), ("^FTMC","FTSE 250","GB"),
        ("^FTAS","FTSE All-Share","GB"), ("^GDAXI","DAX 40","DE"),
        ("^MDAXI","MDAX","DE"), ("^FCHI","CAC 40","FR"),
        ("^STOXX50E","Euro Stoxx 50","EU"), ("^STOXX","STOXX 600","EU"),
        ("^AEX","AEX","NL"), ("^IBEX","IBEX 35","ES"),
        ("FTSEMIB.MI","FTSE MIB","IT"), ("^SSMI","SMI","CH"),
        ("^OMX","OMX Stockholm 30","SE"), ("^OMXC25","OMX Copenhagen 25","DK"),
        ("^OMXH25","OMX Helsinki 25","FI"), ("PSI20.LS","PSI 20","PT"),
        ("^ATG","Athens General Composite","GR"), ("^ATX","ATX","AT"),
        ("^BFX","BEL 20","BE"), ("IMOEX.ME","Moscow Exchange Index","RU"),
        ("^XU100","BIST 100","TR"),
        # Asia-Pacific
        ("^N225","Nikkei 225","JP"), ("^TPX","TOPIX","JP"),
        ("^HSI","Hang Seng Index","HK"), ("^HSCE","Hang Seng China Enterprises","HK"),
        ("000001.SS","Shanghai Composite","CN"), ("000300.SS","CSI 300","CN"),
        ("399001.SZ","Shenzhen Component","CN"),
        ("^KS11","KOSPI","KR"), ("^KQ11","KOSDAQ","KR"),
        ("^AXJO","S&P/ASX 200","AU"), ("^AORD","All Ordinaries","AU"),
        ("^STI","Straits Times Index","SG"), ("^TWII","Taiwan Weighted Index","TW"),
        ("^SET.BK","SET Index","TH"), ("^KLSE","FTSE Bursa Malaysia KLCI","MY"),
        ("^JKSE","Jakarta Composite","ID"), ("^NZ50","NZX 50","NZ"),
        # Americas
        ("^BVSP","Bovespa","BR"), ("^MXX","IPC","MX"), ("^MERV","MERVAL","AR"),
        ("^GSPTSE","S&P/TSX Composite","CA"), ("^IPSA","S&P/CLX IPSA","CL"),
        # Middle East / Africa
        ("^TASI.SR","Tadawul All Share","SA"), ("^DFMGI","DFM General Index","AE"),
        ("^ADI","ADX General Index","AE"), ("^TA125.TA","Tel Aviv 125","IL"),
        ("^TA35.TA","Tel Aviv 35","IL"), ("^QSI","Qatar Exchange Index","QA"),
        ("^EGX30","EGX 30","EG"), ("^J203","JSE Top 40","ZA"),
        # Crypto
        ("BTC-USD","Bitcoin USD","CRYPTO"), ("ETH-USD","Ethereum USD","CRYPTO"),
        ("BNB-USD","Binance Coin USD","CRYPTO"), ("SOL-USD","Solana USD","CRYPTO"),
        ("XRP-USD","XRP USD","CRYPTO"),
    ]
    rows = [{"ticker": t, "name": n, "exchange": e} for t, n, e in INDICES]
    return _write_csv(DATA_DIR / "indices" / "indices.csv", rows,
                      ["ticker", "name", "exchange"])


def update_etfs() -> int:
    ETFS = [
        # Broad market — USA
        ("SPY",  "SPDR S&P 500 ETF Trust",                 "PCX"),
        ("IVV",  "iShares Core S&P 500 ETF",               "PCX"),
        ("VOO",  "Vanguard S&P 500 ETF",                   "PCX"),
        ("VTI",  "Vanguard Total Stock Market ETF",         "PCX"),
        ("QQQ",  "Invesco QQQ Trust",                       "NAS"),
        ("IWM",  "iShares Russell 2000 ETF",                "PCX"),
        ("DIA",  "SPDR Dow Jones Industrial Average ETF",   "PCX"),
        ("VUG",  "Vanguard Growth ETF",                     "PCX"),
        ("VTV",  "Vanguard Value ETF",                      "PCX"),
        # Fixed income
        ("AGG",  "iShares Core US Aggregate Bond ETF",      "PCX"),
        ("BND",  "Vanguard Total Bond Market ETF",          "NAS"),
        ("TLT",  "iShares 20+ Year Treasury Bond ETF",      "NAS"),
        ("IEF",  "iShares 7-10 Year Treasury Bond ETF",     "NAS"),
        ("SHY",  "iShares 1-3 Year Treasury Bond ETF",      "NAS"),
        ("LQD",  "iShares Investment Grade Corp Bond ETF",  "PCX"),
        ("HYG",  "iShares High Yield Corp Bond ETF",        "PCX"),
        ("BIL",  "SPDR Bloomberg 1-3 Month T-Bill ETF",     "PCX"),
        ("SGOV", "iShares 0-3 Month Treasury Bond ETF",     "PCX"),
        ("TIPS", "iShares TIPS Bond ETF",                   "PCX"),
        # Commodities
        ("GLD",  "SPDR Gold Shares",                        "PCX"),
        ("IAU",  "iShares Gold Trust",                      "PCX"),
        ("SLV",  "iShares Silver Trust",                    "PCX"),
        ("GDX",  "VanEck Gold Miners ETF",                  "PCX"),
        ("USO",  "United States Oil Fund",                  "PCX"),
        ("PDBC", "Invesco Diversified Commodity ETF",       "NAS"),
        # Sectors
        ("XLF",  "Financial Select Sector SPDR",            "PCX"),
        ("XLK",  "Technology Select Sector SPDR",           "PCX"),
        ("XLE",  "Energy Select Sector SPDR",               "PCX"),
        ("XLV",  "Health Care Select Sector SPDR",          "PCX"),
        ("XLU",  "Utilities Select Sector SPDR",            "PCX"),
        ("XLI",  "Industrial Select Sector SPDR",           "PCX"),
        ("XLY",  "Consumer Discretionary Select Sector SPDR","PCX"),
        ("XLP",  "Consumer Staples Select Sector SPDR",     "PCX"),
        ("XLB",  "Materials Select Sector SPDR",            "PCX"),
        ("XLRE", "Real Estate Select Sector SPDR",          "PCX"),
        ("XLC",  "Communication Services Select Sector SPDR","PCX"),
        ("SOXX", "iShares Semiconductor ETF",               "NAS"),
        ("SMH",  "VanEck Semiconductor ETF",                "NAS"),
        # Real estate
        ("VNQ",  "Vanguard Real Estate ETF",                "PCX"),
        ("REET", "iShares Global REIT ETF",                 "PCX"),
        # International
        ("EFA",  "iShares MSCI EAFE ETF",                   "PCX"),
        ("EEM",  "iShares MSCI Emerging Markets ETF",       "PCX"),
        ("VWO",  "Vanguard FTSE Emerging Markets ETF",      "PCX"),
        ("VEA",  "Vanguard FTSE Developed Markets ETF",     "PCX"),
        ("IEFA", "iShares Core MSCI EAFE ETF",              "PCX"),
        ("IEMG", "iShares Core MSCI Emerging Markets ETF",  "PCX"),
        ("KWEB", "KraneShares CSI China Internet ETF",      "PCX"),
        ("MCHI", "iShares MSCI China ETF",                  "NAS"),
        ("INDA", "iShares MSCI India ETF",                  "PCX"),
        ("EWJ",  "iShares MSCI Japan ETF",                  "PCX"),
        ("EWZ",  "iShares MSCI Brazil ETF",                 "PCX"),
        ("EWG",  "iShares MSCI Germany ETF",                "PCX"),
        ("EWU",  "iShares MSCI United Kingdom ETF",         "PCX"),
        ("EWY",  "iShares MSCI South Korea ETF",            "PCX"),
        ("EWT",  "iShares MSCI Taiwan ETF",                 "PCX"),
        ("EWH",  "iShares MSCI Hong Kong ETF",              "PCX"),
        # Income / dividend
        ("SCHD", "Schwab US Dividend Equity ETF",           "PCX"),
        ("VYM",  "Vanguard High Dividend Yield ETF",        "PCX"),
        ("DVY",  "iShares Select Dividend ETF",             "NAS"),
        ("JEPI", "JPMorgan Equity Premium Income ETF",      "PCX"),
        ("JEPQ", "JPMorgan Nasdaq Equity Premium Income ETF","NAS"),
        # Thematic / leveraged
        ("ARKK", "ARK Innovation ETF",                      "PCX"),
        ("ARKG", "ARK Genomic Revolution ETF",              "PCX"),
        ("ARKW", "ARK Next Generation Internet ETF",        "PCX"),
        ("CLOU", "Global X Cloud Computing ETF",            "NAS"),
        ("BOTZ", "Global X Robotics & Artificial Intelligence ETF","NAS"),
        ("AIQ",  "Global X Artificial Intelligence & Technology ETF","NAS"),
        ("SQQQ", "ProShares UltraPro Short QQQ",            "NAS"),
        ("TQQQ", "ProShares UltraPro QQQ",                  "NAS"),
        # India ETFs (NSE)
        ("NIFTYBEES.NS",  "Nippon India ETF Nifty BeES",    "NSI"),
        ("SETFNIF50.NS",  "SBI ETF Nifty 50",               "NSI"),
        ("BANKBEES.NS",   "Nippon India ETF Bank BeES",      "NSI"),
        ("GOLDBEES.NS",   "Nippon India ETF Gold BeES",      "NSI"),
        ("ITBEES.NS",     "Nippon India ETF Nifty IT",       "NSI"),
        ("JUNIORBEES.NS", "Nippon India ETF Junior BeES",    "NSI"),
        ("MOM100.NS",     "Motilal Oswal NASDAQ 100 ETF",    "NSI"),
        ("LIQUIDBEES.NS", "Nippon India ETF Liquid BeES",    "NSI"),
        # Europe UCITS
        ("CSPX.L",  "iShares Core S&P 500 UCITS ETF",       "LSE"),
        ("VUSA.L",  "Vanguard S&P 500 UCITS ETF",           "LSE"),
        ("IWDA.AS", "iShares Core MSCI World UCITS ETF",    "AMS"),
        ("EIMI.L",  "iShares Core MSCI EM IMI UCITS ETF",   "LSE"),
        ("VWRL.L",  "Vanguard FTSE All-World UCITS ETF",    "LSE"),
        ("SWDA.L",  "iShares Core MSCI World UCITS ETF USD","LSE"),
        ("XDWD.DE", "Xtrackers MSCI World Swap UCITS ETF",  "GER"),
    ]
    rows = [{"ticker": t, "name": n, "exchange": e} for t, n, e in ETFS]
    return _write_csv(DATA_DIR / "etfs" / "etfs.csv", rows,
                      ["ticker", "name", "exchange"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

LIVE_FETCHERS = {
    "india":          (fetch_nse_india,  ["ticker","name","exchange","category name","country"]),
    "united_states":  (fetch_usa_stocks, ["ticker","name","exchange","category name","country"]),
    "usa":            (fetch_usa_stocks, ["ticker","name","exchange","category name","country"]),
    "united_kingdom": (fetch_uk_stocks,  ["ticker","name","exchange","category name","country"]),
    "uk":             (fetch_uk_stocks,  ["ticker","name","exchange","category name","country"]),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update market-tickers data from official exchange sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--countries", nargs="*", metavar="COUNTRY",
        help=(
            "Countries to update with live fetch. "
            "Live sources available: india, united_states, united_kingdom. "
            "Example: --countries india united_states"
        ),
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Fetch live data for all supported countries (india, usa, uk). Fast, ~30 sec.",
    )
    parser.add_argument(
        "--dedup", action="store_true",
        help=(
            "Deduplicate all country files — keeps only canonical exchange suffix "
            "per company (e.g. .NS over .BO for India, .DE over .BE for Germany). "
            "No network required, runs in seconds."
        ),
    )
    parser.add_argument(
        "--validate", action="store_true",
        help=(
            "After fetching/deduping, validate tickers against Yahoo Finance. "
            "SLOW — use with --countries for a single country only. "
            "Do NOT use with --live or --dedup on all countries."
        ),
    )
    parser.add_argument("--no-stocks",  action="store_true", help="Skip stock updates.")
    parser.add_argument("--no-etfs",    action="store_true", help="Skip ETF update.")
    parser.add_argument("--no-indices", action="store_true", help="Skip index update.")

    args = parser.parse_args()

    # Default: if nothing specified, do --live + --dedup
    if not any([args.countries, args.live, args.dedup, args.no_stocks]):
        args.live  = True
        args.dedup = True

    stats: Dict[str, int] = {}

    # ── Indices ─────────────────────────────────────────────────────────────
    if not args.no_indices:
        n = update_indices()
        stats["indices"] = n
        _log(f"indices.csv → {n} rows", "OK")

    # ── ETFs ─────────────────────────────────────────────────────────────────
    if not args.no_etfs:
        n = update_etfs()
        stats["etfs"] = n
        _log(f"etfs.csv → {n} rows", "OK")

    if args.no_stocks:
        _summarise(stats)
        return

    # ── Live fetch ───────────────────────────────────────────────────────────
    live_targets: List[str] = []
    if args.live:
        live_targets = ["india", "united_states", "united_kingdom"]
    if args.countries:
        live_targets += [c.lower().strip() for c in args.countries]
    live_targets = list(dict.fromkeys(live_targets))   # deduplicate, preserve order

    for country in live_targets:
        if country not in LIVE_FETCHERS:
            _log(
                f"No live source for '{country}'. "
                "Available: india, united_states, united_kingdom. "
                "Use --dedup for other countries.",
                "WARN",
            )
            continue
        _log(f"--- {country} (live fetch) ---")
        fetcher, fieldnames = LIVE_FETCHERS[country]
        rows = fetcher()
        if not rows:
            _log(f"No data returned for {country}, skipping.", "WARN")
            continue
        # Normalise country key to file name (usa -> usa, united_states -> usa)
        file_country = "usa" if country in ("united_states", "usa") else \
                       "united_kingdom" if country in ("united_kingdom", "uk") else \
                       country
        csv_path = DATA_DIR / "stocks" / f"stocks_{file_country}.csv"
        n = _write_csv(csv_path, rows, fieldnames)
        stats[country] = n
        _log(f"stocks_{file_country}.csv → {n} rows", "OK")

    # ── Dedup all countries ──────────────────────────────────────────────────
    if args.dedup:
        _log("\n--- Deduplicating all countries ---")
        from market_tickers.loaders import list_available_countries
        all_countries = list_available_countries()
        for c in all_countries:
            if c in ("united_states",):   # alias, not a real file
                continue
            n = dedup_country(c)
            if c not in stats:
                stats[c] = n

    # ── Optional yfinance validation (explicit opt-in only) ─────────────────
    if args.validate:
        targets = args.countries or (live_targets if live_targets else [])
        if not targets:
            _log(
                "--validate requires --countries COUNTRY. "
                "Example: --countries india --validate",
                "WARN",
            )
        else:
            for country in targets:
                file_c = "usa" if country in ("united_states","usa") else country
                _log(f"--- {file_c} (yfinance validation) ---")
                n = validate_country_yf(file_c)
                stats[file_c] = n

    _summarise(stats)


def _summarise(stats: Dict[str, int]) -> None:
    _log(f"\n{'='*52}")
    _log(f"Done. {len(stats)} files updated.", "OK")
    for k, v in sorted(stats.items()):
        print(f"   {k:<25} {v:>6} rows")


if __name__ == "__main__":
    main()
