from market_tickers import get_ticker


def test_sp500():
    assert get_ticker("S&P 500", category="index") == "^GSPC"


def test_sp500_alias():
    assert get_ticker("sp500", category="index") == "^GSPC"


def test_nasdaq100():
    assert get_ticker("NASDAQ 100", category="index") == "^NDX"


def test_nifty_alias():
    assert get_ticker("Nifty", category="index") == "^NSEI"


def test_nifty50():
    assert get_ticker("Nifty 50", category="index") == "^NSEI"


def test_sensex():
    assert get_ticker("Sensex", category="index") == "^BSESN"


def test_vix_alias():
    assert get_ticker("vix", category="index") == "^VIX"


def test_dax_alias():
    assert get_ticker("dax", category="index") == "^GDAXI"


def test_bitcoin_alias():
    assert get_ticker("bitcoin", category="index") == "BTC-USD"


def test_index_not_found():
    import pytest
    with pytest.raises(KeyError):
        get_ticker("FakeIndex999", category="index")
