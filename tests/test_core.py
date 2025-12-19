import pytest
from market_tickers import get


def test_index_resolution():
    assert get("Nifty") == "^NSEI"
    assert get("Sensex") == "^BSESN"


def test_currency_resolution():
    assert get("USDINR") == "USDINR=X"
    assert get("EURUSD") == "EURUSD=X"


def test_stock_resolution():
    ticker = get("Reliance Industries")
    assert ticker.endswith(".NS") or ticker.endswith(".BO")


def test_invalid_name():
    with pytest.raises(KeyError):
        get("ThisIsNotARealCompany123")
