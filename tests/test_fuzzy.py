import pytest
from market_tickers import get_ticker


def test_fuzzy_india_typo():
    # "Relience" is a common misspelling of "Reliance"
    # Should return some Reliance company on NSE
    result = get_ticker("Relience", country="india")
    assert result.endswith(".NS")
    assert "RELIANC" in result or "RCOM" in result or "RPOWER" in result or "RHFL" in result or "RIIL" in result


def test_fuzzy_us_typo():
    # "Amazn" → should find Amazon or similar
    result = get_ticker("Amazn", country="usa")
    assert result is not None
    assert len(result) > 0


def test_fuzzy_enabled_by_default():
    # Exact match still works fine with fuzzy=True
    result = get_ticker("Infosys", country="india")
    assert result == "INFY.NS"


def test_disable_fuzzy_raises_on_typo():
    # fuzzy=False must raise KeyError on a typo that has no exact match
    with pytest.raises(KeyError):
        get_ticker("Relience", country="india", fuzzy=False)


def test_disable_fuzzy_exact_still_works():
    # fuzzy=False must still return a result for an exact name
    result = get_ticker("Reliance Industries", country="india", fuzzy=False)
    assert result == "RELIANCE.NS"
