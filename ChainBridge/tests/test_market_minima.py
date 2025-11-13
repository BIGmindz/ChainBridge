from src.market_utils import check_markets_have_minima


def test_missing_markets_detected() -> None:
    markets = {}
    symbols = ["BTC/USD", "ETH/USD"]
    missing = check_markets_have_minima(markets, symbols)
    assert set(missing) == set(symbols)


def test_cost_min_present_dict_shape() -> None:
    markets = {
        "BTC/USD": {"limits": {"cost": {"min": 1.0}}},
        "ETH/USD": {"limits": {"amount": {"min": 0.001}}},
    }
    missing = check_markets_have_minima(markets, ["BTC/USD", "ETH/USD"])
    assert missing == []


def test_numeric_limits_present() -> None:
    markets = {
        "BTC/USD": {"limits": {"cost": 5.0}},
        "ETH/USD": {"limits": {"amount": 0.01}},
    }
    missing = check_markets_have_minima(markets, ["BTC/USD", "ETH/USD"])
    assert missing == []


def test_missing_limit_fields() -> None:
    markets = {"BTC/USD": {"limits": {"cost": {}}}, "ETH/USD": {"limits": {}}}
    missing = check_markets_have_minima(markets, ["BTC/USD", "ETH/USD"])
    assert set(missing) == {"BTC/USD", "ETH/USD"}


def test_exchange_variant_matching() -> None:
    # Kraken uses XBT instead of BTC
    markets = {
        "XBT/USD": {"limits": {"cost": {"min": 1.0}}},
        "ETH-USD": {"limits": {"amount": {"min": 0.001}}},
    }
    missing = check_markets_have_minima(markets, ["BTC/USD", "ETH/USD"])
    assert missing == []


def test_kraken_like_markets() -> None:
    # Kraken market keys and shapes
    markets = {
        "XBT/USD": {"limits": {"cost": {"min": 5.0}}},
        "ETH/USD": {"limits": {"amount": {"min": 0.01}}},
        "ADA-USD": {"limits": {"cost": {"min": 0.5}}},
    }
    symbols = ["BTC/USD", "ETH/USD", "ADA/USD"]
    missing = check_markets_have_minima(markets, symbols)
    assert missing == []


def test_hyphenated_markets() -> None:
    # Some exchanges use hyphenated symbols and numeric limits
    markets = {
        "BTC-USD": {"limits": {"cost": 10.0}},
        "ETH-USD": {"limits": {"amount": 0.01}},
    }
    symbols = ["BTC/USD", "ETH/USD"]
    missing = check_markets_have_minima(markets, symbols)
    assert missing == []
