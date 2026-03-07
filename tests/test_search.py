from market_tickers import search_tickers


def test_search_returns_list():
    results = search_tickers("tata", country="india")
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_result_has_ticker_and_name():
    results = search_tickers("tata", country="india")
    assert "ticker" in results[0]
    assert "name" in results[0]


def test_search_limit():
    results = search_tickers("tata", country="india", limit=3)
    assert len(results) <= 3


def test_search_etf():
    results = search_tickers("iShares", category="etf")
    assert len(results) > 0


def test_search_index():
    results = search_tickers("nifty", category="index")
    assert len(results) > 0


def test_search_no_results():
    results = search_tickers("xyznonexistent999", country="india")
    assert results == []


def test_search_requires_country_for_stock():
    import pytest
    with pytest.raises(ValueError):
        search_tickers("tata")
