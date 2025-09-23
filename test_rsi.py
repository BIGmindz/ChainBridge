import os

import ccxt

import pandas as pd
import pytest
from ccxt.base.errors import NetworkError
from dotenv import load_dotenv


def wilder_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    if avg_loss.iloc[-1] == 0:
        return 100.0
    rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
    return 100 - (100 / (1 + rs))


# ---- Kraken smoke test ----
load_dotenv()


def _build_exchange() -> ccxt.Exchange:
    kraken_config = {"enableRateLimit": True}

    api_key = os.getenv("KRAKEN_API_KEY")
    api_secret = os.getenv("KRAKEN_API_SECRET")
    if api_key and api_secret:
        kraken_config.update({"apiKey": api_key, "secret": api_secret})

    return ccxt.kraken(kraken_config)


def test_wilder_rsi_smoke() -> None:
    exchange = _build_exchange()
    symbol = "BTC/USD"
    timeframe = "5m"

    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    except ccxt.NotSupported:
        timeframe = "1m"
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
    except NetworkError as exc:
        pytest.skip(f"Kraken API unreachable: {exc}")

    closes = pd.Series([c[4] for c in ohlcv])
    rsi_val = wilder_rsi(closes, 14)

    assert 0.0 <= rsi_val <= 100.0
