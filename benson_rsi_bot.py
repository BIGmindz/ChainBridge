# -*- coding: utf-8 -*-

import argparse
import math
import os
import signal
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import ccxt  # type: ignore
import pandas as pd  # type: ignore
import yaml  # type: ignore

"""
Benson RSI Bot (Coinbase-friendly)
- Config: config/config.yaml  (override with BENSON_CONFIG env var)
- Prints BUY/SELL/HOLD based on RSI
- Ctrl+C exits cleanly
- Flags:
    --once  : one cycle then exit
    --test  : run unit tests then exit
"""

# --------------------
# Helpers
# --------------------


def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found at {path}")
    with open(path, "r") as f:
        content = f.read()
    # Substitute environment variables in the config content
    content = os.path.expandvars(content)
    return yaml.safe_load(content) or {}


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")


def wilder_rsi(close: pd.Series, period: int = 14) -> float:
    """Wilder's RSI using EMA smoothing."""
    if len(close) < max(2, period + 1):
        return float("nan")
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    last_gain = float(avg_gain.iloc[-1])
    last_loss = float(avg_loss.iloc[-1])
    if last_loss == 0 and last_gain == 0:
        return 50.0
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return float(100 - (100 / (1 + rs)))


def calculate_rsi_from_ohlcv(ohlcv: List[List[float]], period: int) -> float:
    """OHLCV rows: [ts, open, high, low, close, volume]."""
    if not ohlcv:
        return float("nan")
    closes = [row[4] for row in ohlcv if len(row) >= 5]
    series = pd.Series(closes, dtype=float)
    if len(series) < period + 5:
        return float("nan")
    return wilder_rsi(series, period=period)


def backoff_sleep(attempt: int, base: float = 2.0, max_wait: float = 60.0):
    wait = min(max_wait, base ** max(1, attempt))
    time.sleep(wait)


def safe_fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int = 200):
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


def safe_fetch_ticker(exchange, symbol: str) -> float:
    t = exchange.fetch_ticker(symbol)
    price = t.get("last") or t.get("close") or t.get("bid") or t.get("ask")
    if price is None:
        raise RuntimeError(f"No price in ticker for {symbol}")
    return float(price)


# --------------------
# Main bot
# --------------------


def run_bot(once: bool = False) -> None:
    print("[DBG] entered run_bot()")
    config_path = os.getenv("BENSON_CONFIG", "config/config.yaml")
    cfg = load_config(config_path)

    exchange_id = str(cfg.get("exchange", "coinbase")).lower()
    if not hasattr(ccxt, exchange_id):
        raise ValueError(f"Unknown exchange id '{exchange_id}' — check your config")

    exchange_cls = getattr(ccxt, exchange_id)
    exchange = exchange_cls({"enableRateLimit": True})

    # Load markets and validate symbols
    exchange.load_markets()
    symbols: List[str] = list(cfg.get("symbols", []))
    if not symbols:
        symbols = ["BTC/USD", "ETH/USD"]  # sensible Coinbase defaults

    invalid = [s for s in symbols if s not in exchange.symbols]
    if invalid:
        raise ValueError(f"Invalid symbols for {exchange_id}: {invalid}")

    timeframe = str(cfg.get("timeframe", "5m"))
    rsi_period = int(cfg.get("rsi", {}).get("period", 14))
    buy_th = float(cfg.get("rsi", {}).get("buy_threshold", 30))
    sell_th = float(cfg.get("rsi", {}).get("sell_threshold", 70))
    cooldown_min = int(cfg.get("cooldown_minutes", 10))
    poll_seconds = int(cfg.get("poll_seconds", 60))
    log_path = str(cfg.get("csv_log", "benson_signals.csv"))

    last_signal = {s: "HOLD" for s in symbols}
    last_alert_ts = {s: 0.0 for s in symbols}
    cooldown_sec = cooldown_min * 60

    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("ts_utc,exchange,symbol,price,rsi,signal,timeframe\n")

    print("Benson Bot Starting...")
    print(f"Exchange: {exchange_id}")
    print(f"Monitoring: {symbols}")
    print(f"Timeframe: {timeframe}")
    print(f"RSI: period={rsi_period} | Buy<{buy_th} | Sell>{sell_th}")
    print(f"Cooldown: {cooldown_min} min")
    print("-" * 60)

    stop = {"flag": False}

    def handle_sigint(sig, frame):
        stop["flag"] = True
        print("\nStopping gracefully...")

    signal.signal(signal.SIGINT, handle_sigint)

    attempt = 0

    while not stop["flag"]:
        try:
            for symbol in symbols:
                ohlcv = safe_fetch_ohlcv(exchange, symbol, timeframe, limit=200)
                rsi_val = calculate_rsi_from_ohlcv(ohlcv, rsi_period)
                if isinstance(rsi_val, float) and math.isnan(rsi_val):
                    print(f"[{utc_now_str()}] {symbol}: insufficient data for RSI yet.")
                    continue

                price = safe_fetch_ticker(exchange, symbol)

                if rsi_val < buy_th:
                    signal_out = "BUY"
                elif rsi_val > sell_th:
                    signal_out = "SELL"
                else:
                    signal_out = "HOLD"

                now = time.time()
                cooldown_ok = (now - last_alert_ts[symbol]) >= cooldown_sec
                changed = signal_out != last_signal[symbol]

                # Status line
                print(
                    f"[{utc_now_str()}] {symbol:>10}: ${price:,.2f} | RSI {rsi_val:5.2f} | {signal_out}"
                    f"{' (new)' if changed else ''}"
                )

                # Alert only on new actionable signals and respecting cooldown
                if signal_out in ("BUY", "SELL") and changed and cooldown_ok:
                    print(
                        f"SIGNAL: {signal_out} {symbol} @ ${price:,.2f} (RSI {rsi_val:0.2f})"
                    )
                    last_alert_ts[symbol] = now

                # Persist log line
                with open(log_path, "a") as f:
                    f.write(
                        f"{utc_now_str()},{exchange_id},{symbol},{price},{rsi_val:.4f},{signal_out},{timeframe}\n"
                    )

                last_signal[symbol] = signal_out

            attempt = 0
            if once:
                break
            print("-" * 60)
            time.sleep(poll_seconds)

        except Exception as e:
            attempt += 1
            print(f"Error (attempt {attempt}): {type(e).__name__}: {e}")
            backoff_sleep(attempt)

    print("Exit complete. Logs saved to:", log_path)


# --------------------
# CLI entrypoint
# --------------------


def main():
    print("[DBG] entered main()")
    parser = argparse.ArgumentParser(description="Benson RSI Bot")
    parser.add_argument(
        "--once", action="store_true", help="Run a single cycle and exit"
    )
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    run_bot(once=args.once)


# --------------------
# Tests
# --------------------


def test_rsi_flatline():
    s = pd.Series([100] * 20, dtype=float)
    rsi = wilder_rsi(s, 14)
    assert 45 <= rsi <= 55, f"Expected RSI near 50, got {rsi}"


def test_rsi_uptrend():
    s = pd.Series(range(1, 30), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi > 60, f"Expected RSI > 60, got {rsi}"


def test_rsi_downtrend():
    s = pd.Series(range(30, 1, -1), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi < 40, f"Expected RSI < 40, got {rsi}"


def test_rsi_no_losses_near_max():
    s = pd.Series(range(1, 60), dtype=float)
    rsi = wilder_rsi(s, 14)
    assert rsi >= 95 or math.isclose(
        rsi, 100.0, rel_tol=0.01
    ), f"Expected RSI near 100, got {rsi}"


def test_insufficient_ohlcv_returns_nan():
    short_ohlcv = [[0, 0, 0, 0, 100.0, 0.0] for _ in range(10)]
    rsi_val = calculate_rsi_from_ohlcv(short_ohlcv, period=14)
    assert isinstance(rsi_val, float) and math.isnan(
        rsi_val
    ), f"Expected NaN, got {rsi_val}"


def run_tests():
    tests = [
        test_rsi_flatline,
        test_rsi_uptrend,
        test_rsi_downtrend,
        test_rsi_no_losses_near_max,
        test_insufficient_ohlcv_returns_nan,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as ae:
            failures += 1
            print(f"FAIL: {t.__name__}: {ae}")
        except Exception as e:
            failures += 1
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
    if failures:
        raise SystemExit(f"Tests failed: {failures}")
    print("All tests passed.")


if __name__ == "__main__":
    main()
