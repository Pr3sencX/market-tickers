from market_tickers import list_countries, get_default_index


def test_list_countries_returns_list():
    countries = list_countries()
    assert isinstance(countries, list)
    assert len(countries) > 0


def test_list_countries_contains_expected():
    countries = list_countries()
    assert "india" in countries
    assert "united_states" in countries or "usa" in countries


def test_list_countries_is_sorted():
    countries = list_countries()
    assert countries == sorted(countries)


def test_default_index_india():
    assert get_default_index("anything", country="india") == "^NSEI"


def test_default_index_usa():
    assert get_default_index("anything", country="usa") == "^GSPC"


def test_default_index_united_states():
    assert get_default_index("anything", country="united_states") == "^GSPC"


def test_default_index_japan():
    assert get_default_index("anything", country="japan") == "^N225"


def test_default_index_uk():
    assert get_default_index("anything", country="uk") == "^FTSE"


def test_default_index_germany():
    assert get_default_index("anything", country="germany") == "^GDAXI"


def test_default_index_australia():
    assert get_default_index("anything", country="australia") == "^AXJO"


def test_default_index_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        get_default_index("anything", country="narnia")
