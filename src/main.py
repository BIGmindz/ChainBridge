"""
Main Orchestrator for the Decision Bot

This is the main entry point that coordinates all other modules:
- Data Provider for market data
- Signal Engine for trading signals 
- Exchange Adapter for order management
"""

import argparse
import os
import signal
import time
import math
import re
from datetime import datetime, timezone
import yaml
from typing import Dict, Any, List

from .data_provider import setup_exchange, validate_symbols, safe_fetch_ohlcv, safe_fetch_ticker, backoff_sleep
from .signal_engine import calculate_rsi_from_ohlcv, generate_signal
from .exchange_adapter import ExchangeAdapter


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML file with environment variable substitution."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found at {path}")
    
    with open(path, "r") as f:
        content = f.read()
    
    # Substitute environment variables in the format ${VAR_NAME}
    def replace_env_vars(match):
        var_name = match.group(1)
        value = os.getenv(var_name, "")
        # Return empty string quoted to prevent YAML from converting to None
        return f'"{value}"' if value == "" else value
    
    content = re.sub(r'\$\{([^}]+)\}', replace_env_vars, content)
    
    return yaml.safe_load(content) or {}


def utc_now_str() -> str:
    """Get current UTC timestamp as string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")


def run_bot(once: bool = False) -> None:
    """Main bot execution logic."""
    print("[DBG] entered run_bot()")
    config_path = os.getenv("BENSON_CONFIG", "config.yaml")
    cfg = load_config(config_path)

    exchange_id = str(cfg.get("exchange", "kraken")).lower()
    
    # Get API configuration
    api_config = cfg.get("api", {})
    
    # Setup exchange and validate symbols
    exchange = setup_exchange(exchange_id, api_config)
    symbols: List[str] = list(cfg.get("symbols", []))
    if not symbols:
        symbols = ["PRO/USD", "BDXN/USD", "KIN/USD", "SOGNI/USD", "ZORA/USD"]  # Kraken volatile crypto defaults
    
    validate_symbols(exchange, symbols)
    
    # Setup exchange adapter
    exchange_adapter = ExchangeAdapter(exchange, cfg)

    # Configuration parameters
    timeframe = str(cfg.get("timeframe", "5m"))
    rsi_period = int(cfg.get("rsi", {}).get("period", 14))
    buy_th = float(cfg.get("rsi", {}).get("buy_threshold", 30))
    sell_th = float(cfg.get("rsi", {}).get("sell_threshold", 70))
    cooldown_min = int(cfg.get("cooldown_minutes", 10))
    poll_seconds = int(cfg.get("poll_seconds", 60))
    log_path = str(cfg.get("csv_log", "benson_signals.csv"))

    # State tracking
    last_signal = {s: "HOLD" for s in symbols}
    last_alert_ts = {s: 0.0 for s in symbols}
    cooldown_sec = cooldown_min * 60

    # Initialize log file
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

    # Signal handling for graceful shutdown
    stop = {"flag": False}
    def handle_sigint(sig, frame):
        stop["flag"] = True
        print("\nStopping gracefully...")
    signal.signal(signal.SIGINT, handle_sigint)

    attempt = 0

    while not stop["flag"]:
        try:
            for symbol in symbols:
                # Fetch market data
                ohlcv = safe_fetch_ohlcv(exchange, symbol, timeframe, limit=200)
                rsi_val = calculate_rsi_from_ohlcv(ohlcv, rsi_period)
                
                if isinstance(rsi_val, float) and math.isnan(rsi_val):
                    print(f"[{utc_now_str()}] {symbol}: insufficient data for RSI yet.")
                    continue

                price = safe_fetch_ticker(exchange, symbol)
                
                # Generate signal
                signal_out = generate_signal(rsi_val, buy_th, sell_th)

                now = time.time()
                cooldown_ok = (now - last_alert_ts[symbol]) >= cooldown_sec
                changed = (signal_out != last_signal[symbol])

                # Status line
                print(
                    f"[{utc_now_str()}] {symbol:>10}: ${price:,.2f} | RSI {rsi_val:5.2f} | {signal_out}"
                    f"{' (new)' if changed else ''}"
                )

                # Alert only on new actionable signals and respecting cooldown
                if signal_out in ("BUY", "SELL") and changed and cooldown_ok:
                    print(f"SIGNAL: {signal_out} {symbol} @ ${price:,.2f} (RSI {rsi_val:0.2f})")
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


def main():
    """CLI entrypoint."""
    print("[DBG] entered main()")
    parser = argparse.ArgumentParser(description="Benson RSI Bot")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    args = parser.parse_args()

    if args.test:
        from . import tests
        tests.run_tests()
        return

    run_bot(once=args.once)


if __name__ == "__main__":
    main()