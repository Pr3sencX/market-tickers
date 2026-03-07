import pytest
from market_tickers import get_ticker


def test_us_stock():
    assert get_ticker("Apple Inc.", country="usa") == "AAPL"


def test_us_stock_by_ticker():
    assert get_ticker("AAPL", country="usa") == "AAPL"


def test_india_stock():
    assert get_ticker("Reliance Industries", country="india") == "RELIANCE.NS"


def test_india_stock_by_ticker():
    assert get_ticker("TCS", country="india") == "TCS.NS"


def test_uk_stock_alias():
    # 'uk' should resolve same as 'united_kingdom'
    result = get_ticker("HSBC", country="uk")
    assert result.endswith(".L")


def test_country_alias_usa():
    result = get_ticker("Microsoft", country="usa")
    assert result == "MSFT"


def test_country_alias_united_states():
    result = get_ticker("Microsoft", country="united_states")
    assert result == "MSFT"


def test_requires_country_for_stock():
    with pytest.raises(ValueError):
        get_ticker("Apple")


def test_invalid_category():
    with pytest.raises(ValueError):
        get_ticker("Apple", country="usa", category="unknown")


def test_empty_name():
    with pytest.raises(ValueError):
        get_ticker("")


def test_invalid_stock():
    with pytest.raises(KeyError):
        get_ticker("Random Fake Company XYZ 99999", country="usa")
