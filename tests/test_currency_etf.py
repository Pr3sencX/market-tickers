from market_tickers import get_ticker


def test_currency_usdinr():
    assert get_ticker("USDINR", category="currency") == "USDINR=X"


def test_currency_eurusd():
    assert get_ticker("EURUSD", category="currency") == "EURUSD=X"


def test_currency_gbpjpy():
    assert get_ticker("GBPJPY", category="currency") == "GBPJPY=X"


def test_currency_audusd():
    assert get_ticker("AUDUSD", category="currency") == "AUDUSD=X"


def test_etf_by_ticker():
    assert get_ticker("SPY", category="etf") == "SPY"


def test_etf_qqq():
    assert get_ticker("QQQ", category="etf") == "QQQ"


def test_etf_by_name():
    # SPDR S&P 500 — should resolve to SPY (US-listed, appears first in dataset)
    result = get_ticker("SPDR S&P 500", category="etf")
    assert "SPY" in result   # SPY, SPY.MX, SPY5.MI all acceptable


def test_etf_ark_innovation():
    result = get_ticker("ARK Innovation", category="etf")
    assert result == "ARKK"
