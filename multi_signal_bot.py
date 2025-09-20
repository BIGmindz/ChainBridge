#!/usr/bin/env python3
"""
Multi-Signal Paper Trading Bot

This script runs a paper trading bot that uses multiple signal modules
(RSI, MACD, Bollinger Bands, Volume Profile, Sentiment Analysis)
and aggregates them to make more informed trading decisions.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import yaml

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from budget_manager import BudgetManager

# Import core components
from core.module_manager import ModuleManager
from src.data_provider import setup_exchange, validate_symbols


# Define our own safe fetch methods since they might not be available
def safe_fetch_ticker(exchange, symbol):
    """Safely fetch ticker data with error handling. NEVER returns mock data."""
    try:
        ticker = exchange.fetch_ticker(symbol)
        if not ticker or not isinstance(ticker, dict):
            raise ValueError(f"Invalid ticker data format for {symbol}")
        price = (
            ticker.get("last")
            or ticker.get("close")
            or ticker.get("bid")
            or ticker.get("ask")
        )
        if price is None or price <= 0:
            raise ValueError(f"No valid price in ticker data for {symbol}")
        return {"last": float(price)}
    except Exception as e:
        error_msg = (
            f"🚨 CRITICAL: Failed to fetch live ticker data for {symbol}: {str(e)}"
        )
        print(error_msg)
        print(
            "🚨 LIVE TRADING REQUIRES REAL MARKET DATA - Check your connection and API!"
        )
        raise RuntimeError(f"Live ticker fetch failed for {symbol}: {str(e)}")


def safe_fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    """Safely fetch OHLCV data with error handling. NEVER returns mock data."""
    try:
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv_data or len(ohlcv_data) == 0:
            raise ValueError(f"No OHLCV data received from exchange for {symbol}")
        return ohlcv_data
    except Exception as e:
        error_msg = (
            f"🚨 CRITICAL: Failed to fetch live OHLCV data for {symbol}: {str(e)}"
        )
        print(error_msg)
        print(
            "🚨 LIVE TRADING REQUIRES REAL MARKET DATA - Check your connection and API!"
        )
        raise RuntimeError(f"Live data fetch failed for {symbol}: {str(e)}")


from modules.adoption_tracker_module import (
    AdoptionTrackerModule,
)  # Chainalysis adoption tracker  # noqa: E402
from modules.bollinger_bands_module import BollingerBandsModule  # noqa: E402
from modules.global_macro_module import (
    GlobalMacroModule,
)  # Global macro predictor  # noqa: E402
from modules.logistics_signal_module import (
    LogisticsSignalModule,
)  # Ultra-low correlation predictor  # noqa: E402
from modules.macd_module import MACDModule  # noqa: E402
from modules.multi_signal_aggregator_module import (
    MultiSignalAggregatorModule,
)  # noqa: E402
from modules.new_listings_radar_module import (
    NewListingsRadar,
)  # New listings monitoring  # noqa: E402
from modules.region_specific_crypto_module import (
    RegionSpecificCryptoModule,
)  # Region-specific crypto mapper  # noqa: E402

# Import signal modules
from modules.rsi_module import RSIModule  # noqa: E402
from modules.sentiment_analysis_module import SentimentAnalysisModule  # noqa: E402
from modules.volume_profile_module import VolumeProfileModule  # noqa: E402
from src.exchange_adapter import ExchangeAdapter  # noqa: E402
from src.market_utils import check_markets_have_minima  # noqa: E402


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
        return f'"{value}"' if value == "" else value

    content = re.sub(r"\$\{([^}]+)\}", replace_env_vars, content)

    return yaml.safe_load(content) or {}


def utc_now_str() -> str:
    """Get current UTC timestamp as string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")


def prepare_price_data(ohlcv_data, symbol: str = ""):
    """Convert OHLCV data to the format expected by signal modules.

    Args:
        ohlcv_data: Raw OHLCV data from exchange (MUST be real data)
        symbol: Trading symbol for logging

    Raises:
        RuntimeError: If no real OHLCV data is available
    """

    # CRITICAL: Never use mock data in live trading
    if not ohlcv_data or isinstance(ohlcv_data, float):
        error_msg = f"🚨 CRITICAL ERROR: No live OHLCV data available for {symbol}!"
        print(error_msg)
        print(
            "🚨 This bot requires LIVE market data. Check your internet connection and exchange API."
        )
        raise RuntimeError(f"Live trading requires real market data for {symbol}")

    # Parse real OHLCV data
    try:
        price_data = []
        for candle in ohlcv_data:
            if len(candle) >= 6:  # [timestamp, open, high, low, close, volume]
                price_data.append(
                    {
                        "timestamp": candle[0],
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]) if len(candle) > 5 else 0.0,
                    }
                )

        if not price_data:
            raise ValueError("No valid price data parsed")

        print(f"✅ Successfully parsed {len(price_data)} live candles for {symbol}")
        return price_data

    except Exception as e:
        error_msg = f"🚨 ERROR parsing live price data for {symbol}: {str(e)}"
        print(error_msg)
        raise RuntimeError(f"Failed to parse live market data for {symbol}: {str(e)}")


def run_multi_signal_bot(
    once: bool = False, dry_preflight: bool = False, markets_file: str = None
) -> None:
    """Main bot execution logic."""
    print("\n🚀 Multi-Signal Paper Trading Bot Starting...")

    # Load configuration
    config_path = os.getenv("BENSON_CONFIG", "config.yaml")
    cfg = load_config(config_path)

    # Determine monitored symbols early so preflight and live checks can use them
    symbols: List[str] = list(cfg.get("symbols", []))
    if not symbols:
        symbols = ["SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "ATOM/USD"]

    exchange_id = str(cfg.get("exchange", "kraken")).lower()

    # Get API configuration from config file
    api_config = cfg.get("api", {})

    # Override with environment variables if available (for live trading)
    env_api_key = os.getenv("API_KEY", "").strip()
    env_api_secret = os.getenv("API_SECRET", "").strip()

    if env_api_key and env_api_secret:
        api_config = {"key": env_api_key, "secret": env_api_secret}
        print("🔑 Using API credentials from environment variables")
    elif api_config.get("key") and api_config.get("secret"):
        print("🔑 Using API credentials from config file")
    else:
        print("⚠️  No API credentials found - running in read-only mode")

    # Setup exchange and validate symbols
    exchange = setup_exchange(exchange_id, api_config)

    # If requested, run a dry preflight to check market minima and exit
    if dry_preflight:
        try:
            if markets_file:
                # Load markets from a local JSON file
                with open(markets_file, "r") as f:
                    markets = json.load(f)
            else:
                markets = exchange.load_markets()

            # Produce a diagnostic report showing detected minima per symbol
            from src.market_utils import get_minima_report

            report = get_minima_report(markets, symbols if symbols else [])
            print("\nDry Preflight - Minima Diagnostic Report:\n")
            for s, info in report.items():
                if info.get("found_as") is None:
                    print(f"{s}: NOT FOUND in markets dump")
                else:
                    cm = info.get("cost_min")
                    am = info.get("amount_min")
                    print(
                        f"{s}: found_as={info.get('found_as')}, cost_min={cm}, amount_min={am}"
                    )

            # Determine missing symbols as before
            missing = check_markets_have_minima(markets, symbols if symbols else [])
            if missing:
                print(
                    f"\n🚨 PREFLIGHT FAILED: missing minima/limits for symbols: {missing}"
                )
                sys.exit(1)
            print("\n✅ PREFLIGHT PASSED: minima/limits present for monitored symbols")
            sys.exit(0)
        except Exception as e:
            print(f"🚨 PREFLIGHT FAILED: {e}")
            sys.exit(2)

    # If running live, perform a preflight check to ensure markets report minima
    is_live_mode = os.getenv("PAPER", "true").lower() == "false"
    if is_live_mode:
        try:
            markets = exchange.load_markets()
            missing = check_markets_have_minima(markets, symbols if symbols else [])
            if missing:
                print(
                    f"🚨 LIVE PRECHECK FAILED: missing minima/limits for symbols: {missing}"
                )
                print(
                    "🚨 Aborting live mode. Set PAPER=true to continue in paper mode or fix market metadata."
                )
                return
            print(
                "✅ Live preflight checks passed: required minima/limits present for monitored symbols"
            )
        except Exception as e:
            print(f"🚨 LIVE PRECHECK FAILED: {e}")
            print(
                "🚨 Aborting live mode. Set PAPER=true to continue in paper mode or fix markets."
            )
            return
    # Remove problematic symbols that have unreliable price feeds
    filtered = [s for s in symbols if s.upper() != "KIN/USD"]
    if len(filtered) != len(symbols):
        print("⚠️ Removing KIN/USD from symbols due to unreliable price feed")
    symbols = filtered

    # Validate symbols and gracefully handle symbols unsupported by the exchange
    try:
        validate_symbols(exchange, symbols)
    except Exception as e:
        # Filter to symbols supported by the exchange and warn
        supported = [s for s in symbols if s in getattr(exchange, "symbols", [])]
        removed = [s for s in symbols if s not in getattr(exchange, "symbols", [])]
        if removed:
            print(f"⚠️ Removing unsupported symbols for {exchange_id}: {removed}")
        symbols = supported
        if not symbols:
            raise RuntimeError(
                f"No valid symbols remain for {exchange_id} after filtering: {removed}"
            )

    # Setup exchange adapter
    exchange_adapter = ExchangeAdapter(exchange, cfg)

    # Configuration parameters
    timeframe = str(cfg.get("timeframe", "5m"))
    poll_seconds = int(cfg.get("poll_seconds", 60))
    cooldown_min = int(cfg.get("cooldown_minutes", 10))
    log_path = str(cfg.get("multi_signal_log", "multi_signal_trades.json"))
    metrics_file = str(cfg.get("metrics_file", "trading_metrics.json"))

    # Create module manager and load signal modules
    manager = ModuleManager()
    rsi = RSIModule()
    macd = MACDModule()
    bollinger = BollingerBandsModule()
    volume = VolumeProfileModule()
    sentiment = SentimentAnalysisModule()
    logistics = LogisticsSignalModule()  # Updated to ultra-low correlation predictor
    global_macro = GlobalMacroModule()  # Global macro predictor
    adoption_tracker = AdoptionTrackerModule()  # Chainalysis adoption tracker
    region_crypto = RegionSpecificCryptoModule()  # Region-specific crypto mapper
    new_listings_radar = NewListingsRadar(cfg)  # New listings radar monitoring
    aggregator = MultiSignalAggregatorModule()

    manager.register_module("rsi", rsi)
    manager.register_module("macd", macd)
    manager.register_module("bollinger", bollinger)
    manager.register_module("volume", volume)
    manager.register_module("sentiment", sentiment)
    manager.register_module("logistics", logistics)
    manager.register_module("global_macro", global_macro)
    manager.register_module("adoption_tracker", adoption_tracker)
    manager.register_module("region_crypto", region_crypto)
    manager.register_module("new_listings_radar", new_listings_radar)
    manager.register_module("aggregator", aggregator)

    # Instead of MetricsCollector, we'll directly manage our metrics
    _metrics_data = {
        "system_start_time": datetime.now(timezone.utc).isoformat(),
        "trades_tracked": 0,
    }

    # Initialize budget manager with $10,000 starting capital
    initial_capital = float(cfg.get("initial_capital", 10000.0))

    # RADICAL FIX: Detect live mode and fetch real balance
    is_live_mode = os.getenv("PAPER", "true").lower() == "false"
    if is_live_mode:
        budget_manager = BudgetManager(
            initial_capital=initial_capital, exchange=exchange, live_mode=True
        )
    else:
        budget_manager = BudgetManager(initial_capital=initial_capital)

    # State tracking
    last_signals = {s: {"aggregated": "HOLD", "modules": {}} for s in symbols}
    last_alert_ts = {s: 0.0 for s in symbols}
    cooldown_sec = cooldown_min * 60
    trades = []

    # Initialize log file
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                trades = json.load(f)
        except Exception:
            trades = []

    print(f"Exchange: {exchange_id}")
    print(f"Monitoring: {symbols}")
    print(f"Timeframe: {timeframe}")
    print(
        "Signal Modules: RSI, MACD, Bollinger Bands, Volume Profile, Sentiment Analysis,"
    )
    print(
        "  Logistics Signals, Global Macro, Region-Specific Crypto, New Listings Radar"
    )
    print(f"Cooldown: {cooldown_min} min")
    print("-" * 80)

    # Signal handling for graceful shutdown
    stop = {"flag": False}

    def signal_handler(sig, frame):
        print("\nStopping gracefully...")
        stop["flag"] = True

    import signal

    signal.signal(signal.SIGINT, signal_handler)

    # Main trading loop
    attempt = 0

    while not stop["flag"]:
        try:
            # Time of this iteration
            now_ts = time.time()
            now_utc = utc_now_str()

            for symbol in symbols:
                try:
                    # In restricted environment, we'll simulate the data
                    print(f"Processing {symbol}...")

                    try:
                        # CRITICAL: Always fetch real ticker data
                        ticker = safe_fetch_ticker(exchange, symbol)
                        if isinstance(ticker, dict) and "last" in ticker:
                            last_price = ticker["last"]
                            print(f"📊 LIVE PRICE for {symbol}: ${last_price:,.2f}")
                        else:
                            raise ValueError(f"Invalid ticker data format for {symbol}")
                    except Exception as e:
                        # CRITICAL: Never use mock data - fail if we can't get real data
                        error_msg = f"🚨 CRITICAL: Cannot fetch live price for {symbol}: {str(e)}"
                        print(error_msg)
                        print(
                            "🚨 LIVE TRADING REQUIRES REAL MARKET DATA - Check your connection!"
                        )
                        raise RuntimeError(
                            f"Live trading failed: No real price data for {symbol}"
                        )

                    # CRITICAL: Always fetch real OHLCV data - never use mock data
                    try:
                        ohlcv_data = safe_fetch_ohlcv(
                            exchange, symbol, timeframe, limit=200
                        )
                        if not ohlcv_data or len(ohlcv_data) == 0:
                            raise ValueError(f"No OHLCV data received for {symbol}")
                        print(
                            f"📊 LIVE OHLCV data fetched for {symbol}: {len(ohlcv_data)} candles"
                        )
                    except Exception as e:
                        error_msg = f"🚨 CRITICAL: Cannot fetch live OHLCV data for {symbol}: {str(e)}"
                        print(error_msg)
                        print(
                            "🚨 LIVE TRADING REQUIRES REAL MARKET DATA - Check your connection!"
                        )
                        raise RuntimeError(
                            f"Live trading failed: No real OHLCV data for {symbol}"
                        )

                    # Format data for signal modules
                    price_data = prepare_price_data(ohlcv_data, symbol)

                    # --- NEW: Update existing open positions with current price and auto-close if needed ---
                    # Use a copy of keys to avoid mutation during iteration
                    open_positions_ids = list(budget_manager.positions.keys())
                    for pos_id in open_positions_ids:
                        pos = budget_manager.positions.get(pos_id)
                        if pos and pos.get("symbol") == symbol:
                            update_result = budget_manager.update_position(
                                pos_id, last_price
                            )
                            if (
                                isinstance(update_result, dict)
                                and update_result.get("status") is None
                                and update_result.get("success")
                            ):
                                # A position was closed; record trade in trades log
                                trade = update_result.get("trade")
                                if trade:
                                    trades.append(
                                        {
                                            "timestamp": now_utc,
                                            "symbol": trade["symbol"],
                                            "action": (
                                                "SELL"
                                                if trade["side"] == "BUY"
                                                else "BUY"
                                            ),
                                            "price": float(last_price),
                                            "size": trade["size"],
                                            "quantity": trade["quantity"],
                                            "pnl": trade["pnl"],
                                            "reason": trade.get(
                                                "reason", "TAKE_PROFIT"
                                            ),
                                        }
                                    )
                                    # Also notify exchange adapter (paper)
                                    try:
                                        exchange_adapter.place_order(
                                            symbol,
                                            "sell" if trade["side"] == "BUY" else "buy",
                                            trade["quantity"],
                                            last_price,
                                        )
                                    except Exception:
                                        pass
                                # Update last_alert to avoid re-triggering immediately
                                last_alert_ts[symbol] = now_ts
                    # --- END auto-close logic ---

                    # Process signals with each module
                    module_signals = {}

                    # Use a simple helper function to safely process each module
                    def process_module(module, name, input_data, default_signal="HOLD"):
                        """Process a module safely with error handling"""
                        try:
                            print(f"Processing {name} module...")
                            result = module.process(input_data)

                            # Check for required fields
                            if "signal" not in result:
                                print(
                                    f"Warning: {name} module didn't return a 'signal' field, using {default_signal}"
                                )
                                result["signal"] = default_signal

                            return {
                                "signal": result.get("signal", default_signal),
                                "confidence": result.get("confidence", 0.5),
                                "value": result.get(f"{name.lower()}_value", 0),
                            }
                        except Exception as e:
                            print(f"Error processing {name} module: {e}")
                            return {
                                "signal": default_signal,
                                "confidence": 0.5,
                                "value": 0,
                            }

                    # Process each signal module
                    print(f"Running signal modules for {symbol}...")

                    # RSI signal
                    module_signals["RSI"] = process_module(
                        rsi, "RSI", {"price_data": price_data}
                    )

                    # MACD signal
                    module_signals["MACD"] = process_module(
                        macd, "MACD", {"price_data": price_data}
                    )

                    # Bollinger Bands signal
                    module_signals["BollingerBands"] = process_module(
                        bollinger, "BollingerBands", {"price_data": price_data}
                    )

                    # Volume Profile signal
                    module_signals["VolumeProfile"] = process_module(
                        volume, "VolumeProfile", {"price_data": price_data}
                    )

                    # Sentiment Analysis signal
                    module_signals["SentimentAnalysis"] = process_module(
                        sentiment,
                        "SentimentAnalysis",
                        {"symbol": symbol, "timeframe": timeframe},
                    )

                    # Logistics signal (ultra-low correlation, forward-looking indicator)
                    module_signals["LogisticsSignal"] = process_module(
                        logistics,
                        "LogisticsSignal",
                        {"price_data": price_data, "symbol": symbol},
                    )

                    # Global Macro signal (worldwide crypto adoption, regulations predictor)
                    module_signals["GlobalMacro"] = process_module(
                        global_macro,
                        "GlobalMacro",
                        {"price_data": price_data, "symbol": symbol},
                    )

                    # Chainalysis Adoption Tracker signal (regional and country adoption growth)
                    module_signals["AdoptionTracker"] = process_module(
                        adoption_tracker, "AdoptionTracker", {"symbol": symbol}
                    )

                    # Region-specific crypto mapping (matches macro/adoption signals to specific cryptos)
                    # Generate sample macro signals for testing
                    macro_test_signals = {
                        "inflation_ARG": 142 if "ARG" in symbol else 3.2,
                        "stablecoin_growth_LATAM": 0.63 if "USD" in symbol else 0.2,
                        "adoption_rank_IND": (
                            1 if "BTC" in symbol or "ETH" in symbol else 5
                        ),
                        "sbi_ripple_news": True if "XRP" in symbol else False,
                        "port_congestion": (
                            1.4 if "VET" in symbol or "XDC" in symbol else 0.9
                        ),
                        "el_salvador_btc_news": True if "BTC" in symbol else False,
                    }

                    module_signals["RegionCryptoMapper"] = process_module(
                        region_crypto,
                        "RegionCryptoMapper",
                        {"symbol": symbol, "macro_signals": macro_test_signals},
                    )

                    # New listings radar (monitors exchanges for new coin listings)
                    try:
                        # Get the listing signal from the New Listings Radar
                        listing_signal = new_listings_radar.get_signal()

                        # If the signal is for the current symbol, use it; otherwise use a neutral signal
                        if listing_signal.get("coin", "").upper() in symbol:
                            module_signals["NewListingsRadar"] = {
                                "signal": listing_signal.get("action", "HOLD"),
                                "confidence": listing_signal.get("confidence", 0.0),
                                "value": 0,
                                "metadata": {
                                    "exchange": listing_signal.get("exchange", ""),
                                    "position_size": listing_signal.get(
                                        "position_size", 0.0
                                    ),
                                    "expected_return": listing_signal.get(
                                        "expected_return", 0.0
                                    ),
                                    "risk_level": listing_signal.get(
                                        "risk_level", "MEDIUM"
                                    ),
                                },
                            }
                        else:
                            module_signals["NewListingsRadar"] = {
                                "signal": "HOLD",
                                "confidence": 0.0,
                                "value": 0,
                            }
                    except Exception as e:
                        print(f"Error processing New Listings Radar: {e}")
                        module_signals["NewListingsRadar"] = {
                            "signal": "HOLD",
                            "confidence": 0.0,
                            "value": 0,
                        }

                    # Aggregate signals with error handling
                    try:
                        agg_input = {
                            "signals": module_signals,
                            "price_data": (
                                price_data[-1] if price_data else {"close": last_price}
                            ),
                        }
                        print("Aggregating signals...")
                        agg_result = aggregator.process(agg_input)

                        if (
                            not isinstance(agg_result, dict)
                            or "signal" not in agg_result
                        ):
                            print(
                                "Aggregator didn't return a proper result, using default HOLD"
                            )
                            agg_result = {"signal": "HOLD", "confidence": 0.5}
                    except Exception as e:
                        print(f"Error in signal aggregation: {e}")
                        agg_result = {"signal": "HOLD", "confidence": 0.5}

                    # Update last signals
                    last_signals[symbol]["modules"] = module_signals
                    last_signals[symbol]["aggregated"] = agg_result.get(
                        "signal", "HOLD"
                    )

                    # Format signal outputs for display
                    signal_str = ""
                    signal_info = ""

                    if agg_result["signal"] == "BUY":
                        signal_str = "🟢 BUY"
                        signal_info = f"(Conf: {agg_result['confidence']:.2f})"
                    elif agg_result["signal"] == "SELL":
                        signal_str = "🔴 SELL"
                        signal_info = f"(Conf: {agg_result['confidence']:.2f})"
                    else:
                        signal_str = "⚪ HOLD"
                        signal_info = ""

                    # Display current status
                    print(
                        f"[{now_utc}]    {symbol}: ${last_price:,.2f} | {signal_str} {signal_info}"
                    )

                    # Display individual signal indicators
                    indicators = []
                    for mod_name, data in module_signals.items():
                        if data["signal"] == "BUY":
                            indicators.append(f"🟢 {mod_name}")
                        elif data["signal"] == "SELL":
                            indicators.append(f"🔴 {mod_name}")
                        else:
                            indicators.append(f"⚪ {mod_name}")

                    print(f"            Signals: {' | '.join(indicators)}")

                    # Check if we should execute a trade (not during cooldown period)
                    if (
                        now_ts - last_alert_ts[symbol] >= cooldown_sec
                        and agg_result["signal"] != "HOLD"
                    ):
                        # Calculate optimal position size using BudgetManager
                        # Extract volatility from any of our modules if available, or use a default
                        volatility = 0.02  # Default volatility
                        if "BollingerBands" in module_signals:
                            if "band_width" in module_signals["BollingerBands"]:
                                volatility = module_signals["BollingerBands"][
                                    "band_width"
                                ]

                        # Get position size recommendation from budget manager
                        position_calc = budget_manager.calculate_position_size(
                            symbol=symbol,
                            signal_confidence=agg_result["confidence"],
                            volatility=volatility,
                            price=last_price,
                        )

                        # Check if we can open a position
                        if position_calc["size"] > 0:
                            if agg_result["signal"] == "BUY":
                                # Execute paper buy with budget manager
                                budget_result = budget_manager.open_position(
                                    symbol=symbol,
                                    side="BUY",
                                    entry_price=last_price,
                                    position_size=position_calc["size"],
                                )

                                if budget_result["success"]:
                                    # Record trade
                                    trade_record = {
                                        "timestamp": now_utc,
                                        "symbol": symbol,
                                        "action": "BUY",
                                        "price": last_price,
                                        "size": position_calc["size"],
                                        "confidence": agg_result["confidence"],
                                        "signals": module_signals,
                                        "id": budget_result["position"]["id"],
                                        "stop_loss": budget_result["position"][
                                            "stop_loss"
                                        ],
                                        "take_profit": budget_result["position"][
                                            "take_profit"
                                        ],
                                    }
                                    trades.append(trade_record)

                                    # Also execute the order in the exchange adapter for compatibility
                                    exchange_adapter.place_order(
                                        symbol,
                                        "buy",
                                        position_calc["size"] / last_price,
                                        last_price,
                                    )
                                else:
                                    print(
                                        f"⚠️ Could not open BUY position: {budget_result.get('error', 'Unknown error')}"
                                    )

                            elif agg_result["signal"] == "SELL":
                                # Execute paper sell with budget manager
                                budget_result = budget_manager.open_position(
                                    symbol=symbol,
                                    side="SELL",
                                    entry_price=last_price,
                                    position_size=position_calc["size"],
                                )

                                if budget_result["success"]:
                                    # Record trade
                                    trade_record = {
                                        "timestamp": now_utc,
                                        "symbol": symbol,
                                        "action": "SELL",
                                        "price": last_price,
                                        "size": position_calc["size"],
                                        "confidence": agg_result["confidence"],
                                        "signals": module_signals,
                                        "id": budget_result["position"]["id"],
                                        "stop_loss": budget_result["position"][
                                            "stop_loss"
                                        ],
                                        "take_profit": budget_result["position"][
                                            "take_profit"
                                        ],
                                    }
                                    trades.append(trade_record)

                                    # Also execute the order in the exchange adapter for compatibility
                                    exchange_adapter.place_order(
                                        symbol,
                                        "sell",
                                        position_calc["size"] / last_price,
                                        last_price,
                                    )
                                else:
                                    print(
                                        f"⚠️ Could not open SELL position: {budget_result.get('error', 'Unknown error')}"
                                    )
                        else:
                            print(
                                f"⚠️ Cannot open position: {position_calc.get('reason', 'Unknown reason')}"
                            )

                        # Update last alert timestamp
                        last_alert_ts[symbol] = now_ts

                        # Save trades to file
                        with open(log_path, "w") as f:
                            json.dump(trades, f, indent=2, default=str)

                except Exception as e:
                    print(f"Error processing {symbol}: {e}")

            # Save trades to the metrics file
            try:
                with open(metrics_file, "w") as f:
                    # Create a serializable version of the metrics object state
                    serializable_metrics = {
                        "trades": trades,
                        "last_update": datetime.now(timezone.utc).isoformat(),
                    }
                    json.dump(serializable_metrics, f, indent=2, default=str)
            except Exception as e:
                print(f"Error saving metrics: {e}")

            # Save budget state
            budget_manager.save_state("budget_state.json")

            # Display budget dashboard every 5 iterations
            if attempt % 5 == 0:
                budget_manager.display_dashboard()

            # Print separator
            print("-" * 80)

            # Exit if running once
            if once:
                # Always display dashboard on exit
                budget_manager.display_dashboard()
                break

            # Reset backoff
            attempt = 0

            # Sleep until next poll
            time.sleep(poll_seconds)

        except Exception as e:
            attempt += 1
            print(f"Error (attempt {attempt}): {type(e).__name__}: {e}")
            # Exponential backoff
            backoff_time = min(60, 2**attempt)
            print(f"Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)

    print(f"Exit complete. Trades saved to: {log_path}")


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Multi-Signal Paper Trading Bot")
    parser.add_argument(
        "--once", action="store_true", help="Run a single cycle and exit"
    )
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit")
    parser.add_argument(
        "--dry-preflight",
        action="store_true",
        help="Run market minima preflight and exit",
    )
    parser.add_argument(
        "--markets-file",
        type=str,
        default=None,
        help="Optional local markets JSON file to use for preflight",
    )
    args = parser.parse_args()

    if args.test:
        print("Testing functionality not implemented yet.")
        return

    run_multi_signal_bot(
        once=args.once, dry_preflight=args.dry_preflight, markets_file=args.markets_file
    )


if __name__ == "__main__":
    main()
