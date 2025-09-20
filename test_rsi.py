import ccxt
import pandas as pd


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


# ---- Coinbase smoke test ----
exchange = ccxt.coinbase({"enableRateLimit": True})
symbol = "BTC/USD"  # Coinbase uses USD
timeframe = "5m"

try:
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
except ccxt.NotSupported:
    timeframe = "1m"
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)

closes = pd.Series([c[4] for c in ohlcv])
rsi_val = wilder_rsi(closes, 14)
current_price = closes.iloc[-1]

print(f"{symbol} ({timeframe}) price: ${current_price:,.2f}")
print(f"RSI (14): {rsi_val:.2f}")
