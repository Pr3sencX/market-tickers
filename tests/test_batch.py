import pytest
from market_tickers import get_ticker


# ── Single still works unchanged ──────────────────────────────────────────────

def test_single_still_returns_str():
    assert get_ticker("Reliance Industries", country="india") == "RELIANCE.NS"


def test_single_usa():
    assert get_ticker("Microsoft", country="usa") == "MSFT"


# ── Batch returns a plain list of strings, no None ───────────────────────────

def test_batch_returns_list():
    result = get_ticker(["Apple Inc.", "Microsoft"], country="usa")
    assert isinstance(result, list)


def test_batch_no_none_in_result():
    result = get_ticker(["Apple Inc.", "FakeCorpXYZ999", "Microsoft"], country="usa")
    assert None not in result


def test_batch_usa():
    result = get_ticker(["Apple Inc.", "Microsoft"], country="usa")
    assert result == ["AAPL", "MSFT"]


def test_batch_india():
    result = get_ticker(
        ["Reliance Industries", "TCS", "Infosys", "HDFC Bank"],
        country="india",
    )
    assert result == ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]


def test_batch_not_found_skipped():
    result = get_ticker(["Apple Inc.", "FakeCorpXYZ999", "Microsoft"], country="usa")
    assert result == ["AAPL", "MSFT"]


def test_batch_all_not_found_returns_empty():
    result = get_ticker(["FakeA999", "FakeB999"], country="usa")
    assert result == []


def test_batch_empty_input_returns_empty():
    assert get_ticker([], country="usa") == []


def test_batch_yfinance_ready():
    # Should plug straight into yf.download() with no filtering needed
    tickers = get_ticker(["Apple Inc.", "FakeXYZ999", "Microsoft"], country="usa")
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert None not in tickers


# ── Case-insensitive countries ────────────────────────────────────────────────

def test_country_mixed_case():
    assert get_ticker("Microsoft", country="United States") == "MSFT"


def test_country_with_spaces():
    assert get_ticker("Microsoft", country="united states") == "MSFT"


def test_country_uppercase_alias():
    assert get_ticker("Microsoft", country="USA") == "MSFT"


def test_batch_mixed_case_country():
    result = get_ticker(["Apple Inc.", "Microsoft"], country="United States")
    assert result == ["AAPL", "MSFT"]
