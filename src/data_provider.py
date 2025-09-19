"""
Data Provider Module

This module is dedicated to fetching market data from exchanges.
Handles OHLCV data, ticker prices, and exchange connectivity.
"""

import ccxt
import time
from typing import List, Dict, Any


def safe_fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int = 200):
    """Safely fetch OHLCV data from exchange."""
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


def safe_fetch_ticker(exchange, symbol: str) -> float:
    """Safely fetch current ticker price from exchange."""
    t = exchange.fetch_ticker(symbol)
    price = t.get("last") or t.get("close") or t.get("bid") or t.get("ask")
    if price is None:
        raise RuntimeError(f"No price in ticker for {symbol}")
    return float(price)


def setup_exchange(exchange_id: str, api_config: Dict[str, Any] = None) -> ccxt.Exchange:
    """Set up and configure exchange connection with optional API credentials."""
    if not hasattr(ccxt, exchange_id):
        raise ValueError(f"Unknown exchange id '{exchange_id}' — check your config")

    exchange_cls = getattr(ccxt, exchange_id)
    
    # Start with basic configuration
    config = {"enableRateLimit": True}
    
    # Add API credentials if provided and not empty
    if api_config:
        api_key = api_config.get("key", "").strip()
        api_secret = api_config.get("secret", "").strip()
        
        if api_key and api_secret:
            config["apiKey"] = api_key
            config["secret"] = api_secret
            print(f"[CONFIG] Using API credentials for {exchange_id}")
        else:
            print("[CONFIG] No API credentials provided - running in read-only mode")
    
    exchange = exchange_cls(config)
    
    # Load markets and return configured exchange
    exchange.load_markets()
    return exchange


def validate_symbols(exchange: ccxt.Exchange, symbols: List[str]) -> List[str]:
    """Validate that symbols exist on the exchange."""
    invalid = [s for s in symbols if s not in exchange.symbols]
    if invalid:
        raise ValueError(f"Invalid symbols for {exchange.id}: {invalid}")
    return symbols


def backoff_sleep(attempt: int, base: float = 2.0, max_wait: float = 60.0):
    """Exponential backoff sleep for error recovery."""
    wait = min(max_wait, base ** max(1, attempt))
    time.sleep(wait)