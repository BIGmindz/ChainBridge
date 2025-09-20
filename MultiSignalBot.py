#!/usr/bin/env python3
"""
MultiSignalBot Class Implementation

This class encapsulates the functionality of the multi_signal_bot.py script
in a proper class structure for easier integration with the paper trading training system.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from budget_manager import BudgetManager

# Import core components
from core.module_manager import ModuleManager
from modules.adoption_tracker_module import AdoptionTrackerModule
from modules.bollinger_bands_module import BollingerBandsModule
from modules.global_macro_module import GlobalMacroModule
from modules.logistics_signal_module import LogisticsSignalModule
from modules.macd_module import MACDModule
from modules.multi_signal_aggregator_module import MultiSignalAggregatorModule

# Import signal modules
from modules.rsi_module import RSIModule
from modules.sentiment_analysis_module import SentimentAnalysisModule
from modules.volume_profile_module import VolumeProfileModule
from src.data_provider import setup_exchange, validate_symbols
from src.exchange_adapter import ExchangeAdapter


class MultiSignalBot:
    """
    MultiSignalBot class that implements the multi-signal trading system with
    support for paper trading simulation and data collection for ML training.
    """

    def __init__(self, config_path: str = "config.yaml", paper_mode: bool = True):
        """
        Initialize the MultiSignalBot with the specified configuration.

        Args:
            config_path: Path to the configuration file
            paper_mode: Whether to run in paper trading mode
        """
        self.config_path = config_path
        self.paper_mode = paper_mode

        # Load configuration
        self.cfg = self._load_config(config_path)

        # Exchange setup
        self.exchange_id = str(self.cfg.get("exchange", "kraken")).lower()
        self.api_config = self.cfg.get("api", {})
        self.exchange = setup_exchange(self.exchange_id, self.api_config)

        # Symbols and timeframe
        self.symbols = list(self.cfg.get("symbols", []))
        if not self.symbols:
            self.symbols = ["SOL/USD", "DOGE/USD", "SHIB/USD", "AVAX/USD", "ATOM/USD"]
        validate_symbols(self.exchange, self.symbols)

        # Trading parameters
        self.timeframe = str(self.cfg.get("timeframe", "5m"))
        self.poll_seconds = int(self.cfg.get("poll_seconds", 60))
        self.cooldown_min = int(self.cfg.get("cooldown_minutes", 10))
        self.log_path = str(
            self.cfg.get("multi_signal_log", "multi_signal_trades.json")
        )
        self.metrics_file = str(self.cfg.get("metrics_file", "trading_metrics.json"))

        # Setup exchange adapter
        self.exchange_adapter = ExchangeAdapter(self.exchange, self.cfg)

        # Initialize budget manager
        self.initial_capital = float(self.cfg.get("initial_capital", 10000.0))
        self.budget_manager = BudgetManager(initial_capital=self.initial_capital)

        # Initialize modules
        self._init_modules()

        # State tracking
        self.last_signals = {
            s: {"aggregated": "HOLD", "modules": {}} for s in self.symbols
        }
        self.last_alert_ts = {s: 0.0 for s in self.symbols}
        self.trades = self._load_trades()

        # Metrics tracking
        self.metrics_data = {
            "system_start_time": datetime.now(timezone.utc).isoformat(),
            "trades_tracked": 0,
        }

        print(f"🚀 MultiSignalBot initialized with {len(self.symbols)} symbols")
        print(f"Exchange: {self.exchange_id}")
        print(
            "Signal Modules: RSI, MACD, Bollinger Bands, Volume Profile, Sentiment Analysis, Logistics Signals, Global Macro"
        )

    def _load_config(self, path: str) -> Dict[str, Any]:
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

    def _init_modules(self):
        """Initialize all signal modules."""
        self.manager = ModuleManager()

        # Create module instances
        self.rsi = RSIModule()
        self.macd = MACDModule()
        self.bollinger = BollingerBandsModule()
        self.volume = VolumeProfileModule()
        self.sentiment = SentimentAnalysisModule()
        self.logistics = LogisticsSignalModule()
        self.global_macro = GlobalMacroModule()
        self.adoption_tracker = AdoptionTrackerModule()
        self.aggregator = MultiSignalAggregatorModule()

        # Register modules with manager
        self.manager.register_module("rsi", self.rsi)
        self.manager.register_module("macd", self.macd)
        self.manager.register_module("bollinger", self.bollinger)
        self.manager.register_module("volume", self.volume)
        self.manager.register_module("sentiment", self.sentiment)
        self.manager.register_module("logistics", self.logistics)
        self.manager.register_module("global_macro", self.global_macro)
        self.manager.register_module("adoption_tracker", self.adoption_tracker)
        self.manager.register_module("aggregator", self.aggregator)

    def _load_trades(self) -> List[Dict[str, Any]]:
        """Load existing trades from the log file."""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading trades: {e}")
        return []

    def _save_trades(self):
        """Save trades to the log file."""
        try:
            with open(self.log_path, "w") as f:
                json.dump(self.trades, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving trades: {e}")

    def _save_metrics(self):
        """Save metrics to the metrics file."""
        try:
            with open(self.metrics_file, "w") as f:
                # Create a serializable version of the metrics
                serializable_metrics = {
                    "system_start_time": self.metrics_data["system_start_time"],
                    "trades_tracked": len(self.trades),
                    "symbols": self.symbols,
                    "last_update": datetime.now(timezone.utc).isoformat(),
                    "trades": self.trades,
                }
                json.dump(serializable_metrics, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving metrics: {e}")

    def _prepare_price_data(self, ohlcv_data):
        """Convert OHLCV data to the format expected by signal modules."""
        if ohlcv_data is None or len(ohlcv_data) < 5:
            # Generate synthetic data for testing
            now = datetime.now()
            base_price = 30000.0  # For BTC
            ohlcv_data = []
            for i in range(100):
                # timestamp, open, high, low, close, volume
                ts = int((now - timedelta(minutes=5 * (100 - i))).timestamp() * 1000)
                # Create some random price movements
                price_change = 0.0005 * (i % 10 - 5)
                price = base_price * (1 + price_change)
                ohlcv_data.append(
                    [
                        ts,
                        price * 0.99,  # open
                        price * 1.01,  # high
                        price * 0.98,  # low
                        price,  # close
                        100 + i * 2,  # volume
                    ]
                )

        price_data = []
        for candle in ohlcv_data:
            # Extract OHLCV values
            if len(candle) >= 6:
                timestamp, open_price, high, low, close, volume = candle[:6]
            else:
                # Handle missing data
                continue

            # Convert timestamp to datetime if it's an integer
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp / 1000.0)
                timestamp = dt.isoformat()

            # Create candle dictionary
            candle_dict = {
                "timestamp": timestamp,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
            price_data.append(candle_dict)

        return price_data

    def _process_module(self, module, name, input_data, default_signal="HOLD"):
        """Process a module safely with error handling."""
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
            return {"signal": default_signal, "confidence": 0.5, "value": 0}

    def run_once(self, timestamp: Optional[str] = None) -> Dict[str, Any]:
        """
        Run one trading cycle for all symbols.

        Args:
            timestamp: Optional timestamp for the cycle

        Returns:
            Dictionary with results of the cycle
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        now_ts = time.time()
        now_utc = timestamp
        cycle_results = {}

        try:
            print(f"\n[{now_utc}] Running trading cycle...")

            for symbol in self.symbols:
                try:
                    print(f"\nProcessing {symbol}...")

                    # Get current price data
                    try:
                        ticker_data = self.exchange_adapter.exchange.fetch_ticker(
                            symbol
                        )
                        last_price = ticker_data["last"]
                        print(f"Last price for {symbol}: ${last_price:,.2f}")
                    except Exception as e:
                        print(f"Error fetching price for {symbol}: {e}")
                        last_price = (
                            30000.0
                            if "BTC" in symbol
                            else 2000.0 if "ETH" in symbol else 100.0
                        )
                        print(f"Using mock price for {symbol}: ${last_price}")

                    # Generate mock OHLCV data instead of fetching
                    # This ensures we have proper data structure for testing
                    print(f"Generating mock OHLCV data for {symbol}")
                    ohlcv_data = None  # Will trigger mock data generation

                    # Format data for signal modules
                    price_data = self._prepare_price_data(ohlcv_data)
                    print(f"Generated {len(price_data)} candles of mock data")

                    # Process signals with each module
                    module_signals = {}

                    # Run each signal module
                    print(f"Running signal modules for {symbol}...")

                    # RSI signal
                    module_signals["RSI"] = self._process_module(
                        self.rsi, "RSI", {"price_data": price_data}
                    )

                    # MACD signal
                    module_signals["MACD"] = self._process_module(
                        self.macd, "MACD", {"price_data": price_data}
                    )

                    # Bollinger Bands signal
                    module_signals["BollingerBands"] = self._process_module(
                        self.bollinger, "BollingerBands", {"price_data": price_data}
                    )

                    # Volume Profile signal
                    module_signals["VolumeProfile"] = self._process_module(
                        self.volume, "VolumeProfile", {"price_data": price_data}
                    )

                    # Sentiment Analysis signal
                    module_signals["SentimentAnalysis"] = self._process_module(
                        self.sentiment,
                        "SentimentAnalysis",
                        {"symbol": symbol, "timeframe": self.timeframe},
                    )

                    # Logistics signal
                    module_signals["LogisticsSignal"] = self._process_module(
                        self.logistics,
                        "LogisticsSignal",
                        {"price_data": price_data, "symbol": symbol},
                    )

                    # Global Macro signal
                    module_signals["GlobalMacro"] = self._process_module(
                        self.global_macro,
                        "GlobalMacro",
                        {"price_data": price_data, "symbol": symbol},
                    )

                    # Chainalysis Adoption Tracker signal
                    module_signals["AdoptionTracker"] = self._process_module(
                        self.adoption_tracker, "AdoptionTracker", {"symbol": symbol}
                    )

                    # Aggregate signals with error handling
                    try:
                        agg_input = {
                            "signals": module_signals,
                            "price_data": (
                                price_data[-1] if price_data else {"close": last_price}
                            ),
                        }
                        print("Aggregating signals...")
                        agg_result = self.aggregator.process(agg_input)

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
                    self.last_signals[symbol]["modules"] = module_signals
                    self.last_signals[symbol]["aggregated"] = agg_result.get(
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

                    # Record the results
                    cycle_results[symbol] = {
                        "price": last_price,
                        "signals": module_signals,
                        "aggregated_result": agg_result,
                        "timestamp": now_utc,
                    }

                    # Check if we should execute a trade (not during cooldown period)
                    cooldown_sec = self.cooldown_min * 60
                    if (
                        now_ts - self.last_alert_ts[symbol] >= cooldown_sec
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
                        position_calc = self.budget_manager.calculate_position_size(
                            symbol=symbol,
                            signal_confidence=agg_result["confidence"],
                            volatility=volatility,
                        )

                        # Check if we can open a position
                        if position_calc["size"] > 0:
                            if agg_result["signal"] == "BUY":
                                # Execute paper buy with budget manager
                                budget_result = self.budget_manager.open_position(
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
                                    self.trades.append(trade_record)

                                    # Also execute the order in the exchange adapter for compatibility
                                    self.exchange_adapter.place_order(
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
                                budget_result = self.budget_manager.open_position(
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
                                    self.trades.append(trade_record)

                                    # Also execute the order in the exchange adapter for compatibility
                                    self.exchange_adapter.place_order(
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
                        self.last_alert_ts[symbol] = now_ts

                        # Save trades to file
                        self._save_trades()

                except Exception as e:
                    print(f"Error processing {symbol}: {e}")

            # Save metrics
            self._save_metrics()

            # Save budget state
            self.budget_manager.save_state("budget_state.json")

            # Display budget dashboard
            self.budget_manager.display_dashboard()

        except Exception as e:
            print(f"Error in trading cycle: {type(e).__name__}: {e}")

        return cycle_results

    def get_latest_market_data(self) -> Dict[str, Any]:
        """
        Get the latest market data for all symbols.

        Returns:
            Dictionary with market data
        """
        market_data = {}

        for symbol in self.symbols:
            try:
                ticker_data = self.exchange_adapter.exchange.fetch_ticker(symbol)
                market_data[symbol] = {
                    "last": ticker_data["last"],
                    "bid": ticker_data.get("bid", 0),
                    "ask": ticker_data.get("ask", 0),
                    "volume": ticker_data.get("volume", 0),
                    "timestamp": ticker_data.get("timestamp", time.time() * 1000),
                }
            except Exception as e:
                print(f"Error fetching market data for {symbol}: {e}")
                # Use mock data
                market_data[symbol] = {
                    "last": (
                        30000.0
                        if "BTC" in symbol
                        else 2000.0 if "ETH" in symbol else 100.0
                    ),
                    "bid": (
                        29950.0
                        if "BTC" in symbol
                        else 1990.0 if "ETH" in symbol else 99.5
                    ),
                    "ask": (
                        30050.0
                        if "BTC" in symbol
                        else 2010.0 if "ETH" in symbol else 100.5
                    ),
                    "volume": 1000.0,
                    "timestamp": time.time() * 1000,
                }

        return market_data

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the trading bot.

        Returns:
            Dictionary with performance metrics
        """
        # Get metrics from budget manager
        budget_metrics = self.budget_manager.get_metrics()

        # Additional custom metrics
        signal_metrics = {}
        for symbol, data in self.last_signals.items():
            signal_metrics[symbol] = {
                "last_signal": data["aggregated"],
                "module_signals": data["modules"],
            }

        # Combine metrics
        metrics = {
            "budget": budget_metrics,
            "signals": signal_metrics,
            "trades_count": len(self.trades),
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

        return metrics


# If this script is run directly, run a test
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Multi-Signal Bot")
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--paper", action="store_true", help="Run in paper trading mode"
    )
    args = parser.parse_args()

    print("Initializing MultiSignalBot...")
    bot = MultiSignalBot(config_path=args.config, paper_mode=args.paper)

    print("Running one trading cycle...")
    results = bot.run_once()

    print("\n✅ Test complete!")
