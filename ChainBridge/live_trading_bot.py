#!/usr/bin/env python3
"""
LIVE TRADING BOT WITH AUTO-LIQUIDATION
Automatically liquidates positions when capital runs low
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

import yaml

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Radical method: Manually load .env variables
    import os

    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(dotenv_path):
        with open(dotenv_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key, value)
    else:
        print("❌ .env file not found. API keys missing!")

# Load API config from environment
CONFIG_PATHS = ["config/config.yaml", "config.yaml"]

api_config = {"key": os.getenv("API_KEY", ""), "secret": os.getenv("API_SECRET", "")}

# Set live trading mode
os.environ["PAPER"] = "false"

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from budget_manager import BudgetManager
from src.data_provider import setup_exchange
from src.exchange_adapter import ExchangeAdapter

# Import multi-signal modules
from core.module_manager import ModuleManager
from modules.rsi_module import RSIModule
from modules.macd_module import MACDModule
from modules.bollinger_bands_module import BollingerBandsModule
from modules.volume_profile_module import VolumeProfileModule
from modules.sentiment_analysis_module import SentimentAnalysisModule
from modules.logistics_signal_module import LogisticsSignalModule
from modules.global_macro_module import GlobalMacroModule
from modules.adoption_tracker_module import AdoptionTrackerModule
from modules.region_specific_crypto_module import RegionSpecificCryptoModule
from modules.new_listings_radar import ListingsMonitor
from modules.multi_signal_aggregator_module import MultiSignalAggregatorModule


def load_bot_config() -> dict:
    """Load YAML configuration, falling back to defaults when missing."""
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
                data.setdefault("_config_path", path)
                print(f"✅ Loaded configuration from {path}")
                return data
            except Exception as exc:
                print(f"⚠️  Failed to load configuration from {path}: {exc}")
                break

    print(
        "⚠️  No configuration file found (expected config/config.yaml or config.yaml). Using defaults."
    )
    return {}


# Preflight check to ensure API keys are loaded
def preflight_check() -> None:
    """Verify that API keys are loaded in environment before trading."""
    api_key = os.environ.get("API_KEY")
    api_secret = os.environ.get("API_SECRET")
    if not api_key or not api_secret:
        print("❌ Missing API_KEY or API_SECRET in environment.")
        sys.exit(1)
    else:
        print(
            f"✅ API keys loaded. API_KEY: {api_key[:10]}..., API_SECRET: {api_secret[:10]}..."
        )


class LiveTradingBot:
    """Live trading bot with multi-signal aggregation and auto-liquidation.

    Coordinates multiple technical analysis modules to generate trading signals,
    manages positions, and automatically liquidates when capital runs low.
    """

    def __init__(self, config: dict | None = None) -> None:
        print("🚀 INITIALIZING LIVE TRADING BOT WITH MULTI-SIGNAL AGGREGATION")

        self.config = config or load_bot_config()

        # Setup exchange with API keys
        self.exchange = setup_exchange("kraken", api_config)

        # Initialize budget manager with live mode
        raw_initial_capital = (self.config.get("risk") or {}).get(
            "initial_capital", 10000.0
        )
        initial_capital = 10000.0
        try:
            # Some configs may have accidental trailing text (e.g. '426.60loaded from env')
            if isinstance(raw_initial_capital, str):
                import re

                match = re.search(r"[-+]?[0-9]*\.?[0-9]+", raw_initial_capital)
                if match:
                    initial_capital = float(match.group(0))
                else:
                    raise ValueError(
                        f"No numeric value found in initial_capital string: {raw_initial_capital}"
                    )
            else:
                initial_capital = float(raw_initial_capital)
        except Exception as parse_exc:
            print(
                f"⚠️  Warning: Failed to parse initial_capital '{raw_initial_capital}' ({parse_exc}); using default {initial_capital}."
            )
        self.budget_manager = BudgetManager(
            initial_capital=initial_capital, exchange=self.exchange, live_mode=True
        )

        # Initialize exchange adapter
        self.exchange_adapter = ExchangeAdapter(exchange=self.exchange, config={})

        configured_symbols = (
            self.config.get("symbols") if isinstance(self.config, dict) else None
        )
        if isinstance(configured_symbols, list) and configured_symbols:
            self.symbols = [str(symbol) for symbol in configured_symbols]
        else:
            # Trading symbols (20 USD pairs on Kraken)
            self.symbols = [
                "BTC/USD",
                "ETH/USD",
                "SOL/USD",
                "XRP/USD",
                "ADA/USD",
                "DOGE/USD",
                "LTC/USD",
                "DOT/USD",
                "LINK/USD",
                "AVAX/USD",
                "ATOM/USD",
                "ARB/USD",
                "TRX/USD",
                "XLM/USD",
                "FIL/USD",
                "NEAR/USD",
                "AAVE/USD",
                "ETC/USD",
                "BCH/USD",
                "UNI/USD",
            ]

        # Initialize multi-signal system
        self._initialize_signal_modules()

        print(f"💰 Initial Capital: ${self.budget_manager.initial_capital:,.2f}")
        print(f"📊 Trading Symbols: {', '.join(self.symbols)}")
        print("⚠️  LIVE TRADING MODE - REAL ORDERS WILL BE PLACED!")
        print(
            "🔄 MULTI-SIGNAL AGGREGATION ENABLED - All signals flow through aggregator"
        )
        print(
            "📈 Signal Modules: RSI, MACD, Bollinger Bands, Volume Profile, Sentiment Analysis,"
        )
        print(
            "   Logistics Signals, Global Macro, Region-Specific Crypto, New Listings Radar"
        )

        # Runtime overrides (injected by orchestrator via config["runtime_overrides"])
        overrides = (self.config or {}).get("runtime_overrides", {})
        self.force_execution = bool(overrides.get("force_execution"))
        self.min_confidence = float(overrides.get("min_confidence", 0.25))
        self.min_trade_usd = float(overrides.get("min_trade_usd", 50.0))
        if self.force_execution:
            print(
                f"⚡ Force execution override ENABLED (min_confidence={self.min_confidence}, min_trade_usd={self.min_trade_usd})"
            )
        else:
            print(
                f"🔧 Runtime thresholds: min_confidence={self.min_confidence} min_trade_usd={self.min_trade_usd}"
            )

        # Trade event log path / recent trades buffer
        self.trade_log_path = Path("logs/trades.jsonl")
        self.trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.recent_trades = []  # in-memory ring buffer for snapshot (last 25)
        self._forced_trade_done = False

    def _initialize_signal_modules(self) -> None:
        """Initialize all signal modules and register with manager."""
        print("🔧 Initializing multi-signal modules...")

        # Create module manager
        self.module_manager = ModuleManager()

        # Initialize all signal modules
        self.rsi = RSIModule()
        self.macd = MACDModule()
        self.bollinger = BollingerBandsModule()
        self.volume = VolumeProfileModule()
        self.sentiment = SentimentAnalysisModule()
        self.logistics = LogisticsSignalModule()
        self.global_macro = GlobalMacroModule()
        self.adoption_tracker = AdoptionTrackerModule()
        self.region_crypto = RegionSpecificCryptoModule()
        self.new_listings_radar = ListingsMonitor()  # type: ignore
        self.aggregator = MultiSignalAggregatorModule()

        # Register modules with manager
        self.module_manager.register_module("rsi", self.rsi)
        self.module_manager.register_module("macd", self.macd)
        self.module_manager.register_module("bollinger", self.bollinger)
        self.module_manager.register_module("volume", self.volume)
        self.module_manager.register_module("sentiment", self.sentiment)
        self.module_manager.register_module("logistics", self.logistics)  # type: ignore
        self.module_manager.register_module("global_macro", self.global_macro)  # type: ignore
        self.module_manager.register_module("adoption_tracker", self.adoption_tracker)
        self.module_manager.register_module("region_crypto", self.region_crypto)  # type: ignore
        self.module_manager.register_module("new_listings_radar", self.new_listings_radar)  # type: ignore
        self.module_manager.register_module("aggregator", self.aggregator)

        print("✅ All signal modules initialized and registered")

    def run_trading_cycle(self) -> None:
        """Execute one complete trading cycle with signal generation and execution."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === TRADING CYCLE ===")

        # Check if we need to liquidate due to low capital
        self._check_and_liquidate_if_needed()

        # Collect per-symbol snapshots for UI
        per_symbol_snapshots = []

        for symbol in self.symbols:
            try:
                # Get OHLCV data for signal analysis
                timeframe = "5m"  # 5-minute candles
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=200)

                # Get current price from latest OHLCV candle
                if ohlcv:
                    price = ohlcv[-1][4]  # Close price of latest candle
                else:
                    # Fallback to ticker if OHLCV fails
                    ticker = self.exchange.fetch_ticker(symbol)
                    price = ticker["last"]

                print(f"📊 {symbol}: ${price:.4f}")

                # Check if we have enough capital for a trade (dynamic min)
                min_trade_size = self.min_trade_usd
                if self.budget_manager.available_capital < min_trade_size:
                    print(
                        f"⚠️  Insufficient capital for {symbol} (need ${min_trade_size}, have ${self.budget_manager.available_capital:.2f})"
                    )
                    continue

                # Generate multi-signal analysis through aggregator
                signal_result = self._generate_multi_signal(symbol, ohlcv, price)
                signal = signal_result["signal"]
                confidence = signal_result["confidence"]

                print(f"🎯 Aggregated Signal: {signal} (Confidence: {confidence:.2f})")

                # Show individual module signals
                self._display_module_signals(signal_result["modules"])

                # Append UI snapshot element
                try:
                    per_symbol_snapshots.append(
                        {
                            "symbol": symbol,
                            "price": price,
                            "aggregated_signal": signal,
                            "aggregated_confidence": confidence,
                            "modules": {
                                m: {
                                    "signal": d.get("signal"),
                                    "confidence": d.get("confidence"),
                                    "value": d.get("value"),
                                }
                                for m, d in signal_result.get("modules", {}).items()
                            },
                        }
                    )
                except Exception as snap_exc:
                    print(f"⚠️  Failed to record snapshot for {symbol}: {snap_exc}")

                # Determine effective signal under force-execution override
                effective_signal = signal
                effective_conf = confidence
                if self.force_execution and not self._forced_trade_done:
                    if signal == "HOLD":
                        effective_signal = "BUY"  # Demonstration forced BUY
                        effective_conf = max(confidence, self.min_confidence)
                        print(
                            "⚡ Force-execution override: converting HOLD -> BUY for demonstration"
                        )
                    # else keep existing non-HOLD actionable signal
                # Decide if we trade
                if effective_signal != "HOLD" and (
                    self.force_execution
                    and not self._forced_trade_done
                    or effective_conf >= self.min_confidence
                ):
                    self._execute_trade(symbol, effective_signal, price, effective_conf)
                    if self.force_execution and not self._forced_trade_done:
                        self._forced_trade_done = True  # limit to one forced trade

            except Exception as e:
                print(f"❌ Error with {symbol}: {e}")

        # Show portfolio status
        self._show_portfolio_status()

        # Persist UI snapshot
        try:
            self._write_ui_snapshot(per_symbol_snapshots)
        except Exception as w_exc:
            print(f"⚠️  Failed to write UI snapshot: {w_exc}")

        print("✅ Cycle completed")

    def _check_and_liquidate_if_needed(self) -> None:
        """Check capital levels and liquidate positions if capital is low."""
        try:
            # Check if capital is below threshold
            threshold = 100.0  # $100 minimum
            if self.budget_manager.available_capital < threshold:
                print(
                    f"⚠️  LOW CAPITAL ALERT: ${self.budget_manager.available_capital:.2f} < ${threshold:.2f}"
                )

                # Trigger automatic liquidation
                liquidation_result = self.budget_manager.check_low_capital_and_liquidate(self.exchange_adapter)  # type: ignore

                if liquidation_result["status"] == "recovered":
                    print(
                        f"💰 CAPITAL RECOVERED: ${liquidation_result['available_capital']:,.2f}"
                    )
                else:
                    print(
                        f"⚠️  CAPITAL STILL LOW: ${liquidation_result['available_capital']:,.2f}"
                    )

        except Exception as e:
            print(f"❌ Error checking liquidation: {e}")

    def _execute_trade(
        self, symbol: str, signal: str, price: float, confidence: float
    ) -> None:
        """Execute a trade order for the given symbol and signal."""
        try:
            # Calculate position size using budget manager
            position_info = self.budget_manager.calculate_position_size(
                symbol=symbol, signal_confidence=confidence, price=price
            )

            position_size = position_info["size"]

            if position_size < self.min_trade_usd:  # Dynamic minimum trade size
                print(
                    f"⚠️  Position size too small: ${position_size:.2f} (< {self.min_trade_usd})"
                )
                return

            print(f"📈 Executing {signal} for {symbol}")
            print(f"💰 Position Size: ${position_size:.2f}")
            print(f"💵 Cost: ${position_size:.2f}")

            # Place the order
            order = self.exchange_adapter.place_order(
                symbol=symbol,
                side=signal.lower(),
                amount=position_size / price,  # Convert to quantity
                price=price,
            )

            if not order:
                print(f"❌ Failed to place {signal} order for {symbol}")
                self._log_trade_event(
                    {
                        "ts": self._utc_now(),
                        "symbol": symbol,
                        "side": signal,
                        "price": price,
                        "status": "submit_failed",
                        "confidence": confidence,
                        "position_size": position_size,
                    }
                )
                return

            order_id = (
                order.get("id") or order.get("orderId") or order.get("clientOrderId")
            )
            print(f"📝 Submitted {signal} order id={order_id} for {symbol} @ {price}")
            self._log_trade_event(
                {
                    "ts": self._utc_now(),
                    "symbol": symbol,
                    "side": signal,
                    "price": price,
                    "status": "submitted",
                    "confidence": confidence,
                    "position_size": position_size,
                    "order_id": order_id,
                }
            )

            # Poll for fill
            final_status, fill_price = self._poll_order_fill(
                order_id, symbol, signal.lower(), price
            )
            if final_status == "filled":
                # Record the position in budget manager (using fill price if available)
                entry_price = fill_price or price
                self.budget_manager.open_position(
                    symbol=symbol,
                    side=signal,
                    entry_price=entry_price,
                    position_size=position_size,
                    stop_loss=entry_price * 0.97,
                    take_profit=entry_price * 1.06,
                )
                print(f"✅ {signal} FILLED for {symbol} at ${entry_price}")
                self._log_trade_event(
                    {
                        "ts": self._utc_now(),
                        "symbol": symbol,
                        "side": signal,
                        "price": entry_price,
                        "status": "filled",
                        "confidence": confidence,
                        "position_size": position_size,
                        "order_id": order_id,
                    }
                )
            elif final_status == "canceled":
                print(
                    f"⚠️  {signal} order {order_id} canceled / not filled; releasing capital"
                )
                self._log_trade_event(
                    {
                        "ts": self._utc_now(),
                        "symbol": symbol,
                        "side": signal,
                        "price": price,
                        "status": "canceled",
                        "confidence": confidence,
                        "position_size": position_size,
                        "order_id": order_id,
                    }
                )
            else:
                print(
                    f"⚠️  {signal} order {order_id} unfilled after timeout; marking as expired"
                )
                self._log_trade_event(
                    {
                        "ts": self._utc_now(),
                        "symbol": symbol,
                        "side": signal,
                        "price": price,
                        "status": "expired",
                        "confidence": confidence,
                        "position_size": position_size,
                        "order_id": order_id,
                    }
                )

        except Exception as e:
            print(f"❌ Trade execution error: {e}")
            self._log_trade_event(
                {
                    "ts": self._utc_now(),
                    "symbol": symbol,
                    "side": signal,
                    "price": price,
                    "status": "error",
                    "error": str(e),
                    "confidence": confidence,
                }
            )

    def _calculate_rsi(self, ohlcv: list, period: int = 14) -> float:
        """Calculate RSI using Wilder's smoothing method."""
        if len(ohlcv) < period + 1:
            return 50.0  # Default neutral RSI

        # Extract closing prices
        closes = [
            candle[4] for candle in ohlcv
        ]  # OHLCV format: [timestamp, open, high, low, close, volume]

        # Calculate price changes
        changes = []
        for i in range(1, len(closes)):
            changes.append(closes[i] - closes[i - 1])  # type: ignore

        # Calculate gains and losses
        gains = [max(change, 0) for change in changes]
        losses = [max(-change, 0) for change in changes]

        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period  # type: ignore
        avg_loss = sum(losses[:period]) / period  # type: ignore

        # Calculate Wilder's smoothed averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # Calculate RS and RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _generate_multi_signal(self, symbol: str, ohlcv: list, price: float) -> dict:
        """Generate aggregated signal from all modules."""
        try:
            # Prepare price data for modules
            price_data = self._prepare_price_data(ohlcv, symbol)

            # Run all individual signal modules
            module_signals = {}

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
                self.sentiment, "SentimentAnalysis", {"price_data": price_data}
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

            # Adoption Tracker signal
            module_signals["AdoptionTracker"] = self._process_module(
                self.adoption_tracker, "AdoptionTracker", {"symbol": symbol}
            )

            # Region-specific crypto mapping
            macro_test_signals = {
                "inflation_ARG": 142 if "ARG" in symbol else 3.2,
                "stablecoin_growth_LATAM": 0.63 if "USD" in symbol else 0.2,
                "adoption_rank_IND": (1 if "BTC" in symbol or "ETH" in symbol else 5),
                "sbi_ripple_news": True if "XRP" in symbol else False,
                "port_congestion": (1.4 if "VET" in symbol or "XDC" in symbol else 0.9),
                "el_salvador_btc_news": True if "BTC" in symbol else False,
            }
            module_signals["RegionCryptoMapper"] = self._process_module(
                self.region_crypto,
                "RegionCryptoMapper",
                {"symbol": symbol, "macro_signals": macro_test_signals},
            )

            # New Listings Radar
            try:
                listing_signal = self.new_listings_radar.get_signal() if hasattr(self.new_listings_radar, "get_signal") else None  # type: ignore
                if listing_signal and listing_signal.get("coin", "").upper() in symbol:  # type: ignore
                    module_signals["NewListingsRadar"] = {
                        "signal": listing_signal.get("action", "HOLD"),  # type: ignore
                        "confidence": listing_signal.get("confidence", 0.0),  # type: ignore
                        "value": 0,
                    }
                else:
                    module_signals["NewListingsRadar"] = {
                        "signal": "HOLD",
                        "confidence": 0.0,
                        "value": 0,
                    }
            except Exception:
                module_signals["NewListingsRadar"] = {
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "value": 0,
                }

            # Aggregate all signals through MultiSignalAggregatorModule
            agg_input = {
                "signals": module_signals,
                "price_data": price_data[-1] if price_data else {"close": price},
            }

            agg_result = self.aggregator.process(agg_input)

            if not isinstance(agg_result, dict) or "signal" not in agg_result:
                agg_result = {"signal": "HOLD", "confidence": 0.5}

            return {
                "signal": agg_result.get("signal", "HOLD"),
                "confidence": agg_result.get("confidence", 0.5),
                "modules": module_signals,
            }

        except Exception as e:
            print(f"❌ Error in multi-signal generation: {e}")
            return {"signal": "HOLD", "confidence": 0.0, "modules": {}}

    def _process_module(self, module: object, name: str, data: dict) -> dict:
        """Process individual signal module with error handling."""
        try:
            result = module.process(data)
            if not isinstance(result, dict):
                result = {"signal": "HOLD", "confidence": 0.5, "value": 0}
            return {
                "signal": result.get("signal", "HOLD"),
                "confidence": result.get("confidence", 0.5),
                "value": result.get(f"{name.lower()}_value", 0),
            }
        except Exception as e:
            print(f"❌ Error processing {name} module: {e}")
            return {"signal": "HOLD", "confidence": 0.5, "value": 0}

    def _prepare_price_data(self, ohlcv: list, symbol: str) -> list:
        """Prepare OHLCV data in format expected by signal modules."""
        if not ohlcv:
            return []

        price_data = []
        for candle in ohlcv:
            price_data.append(  # type: ignore
                {
                    "timestamp": candle[0],
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                    "symbol": symbol,
                }
            )
        return price_data

    def _display_module_signals(self, module_signals: dict) -> None:
        """Display individual module signals."""
        indicators = []
        for mod_name, data in module_signals.items():
            if data["signal"] == "BUY":
                indicators.append(f"🟢 {mod_name}")  # type: ignore
            elif data["signal"] == "SELL":
                indicators.append(f"🔴 {mod_name}")  # type: ignore
            else:
                indicators.append(f"⚪ {mod_name}")  # type: ignore

        print(f"            Signals: {' | '.join(indicators)}")

    # ---------------- Trade Logging & Order Polling -----------------
    def _utc_now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _log_trade_event(self, event: dict) -> None:
        """Log a trade event to JSONL file and memory buffer."""
        try:
            line = json.dumps(event)
            with self.trade_log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            self.recent_trades.append(event)
            if len(self.recent_trades) > 25:
                self.recent_trades = self.recent_trades[-25:]
        except Exception as exc:
            print(f"⚠️  Failed to log trade event: {exc}")

    def _poll_order_fill(
        self,
        order_id: str,
        symbol: str,
        side: str,
        submitted_price: float,
        timeout_seconds: int = 60,
    ) -> tuple[str, float | None]:
        """Poll exchange for order fill status.

        Returns: (status, fill_price)
        status ∈ {filled, canceled, open, expired}
        """
        if not order_id:
            return ("unknown", None)
        start = time.time()
        last_status = "submitted"
        while time.time() - start < timeout_seconds:
            try:
                # Attempt to fetch order status via ccxt if available
                if hasattr(self.exchange, "fetch_order"):
                    info = self.exchange.fetch_order(order_id, symbol)  # type: ignore
                    status = (info.get("status") or "").lower()
                    price = info.get("price") or submitted_price
                    if status in {"closed", "filled"}:
                        return ("filled", price)
                    if status in {"canceled", "cancelled"}:
                        return ("canceled", None)
                    last_status = status or last_status
                time.sleep(3)
            except Exception:
                time.sleep(5)
        return (last_status if last_status != "submitted" else "open", None)

    # ---------------------------------------------------------------
    # UI Snapshot Support
    # ---------------------------------------------------------------
    def _write_ui_snapshot(self, per_symbol_snapshots: list) -> None:
        """Write latest cycle snapshot for external UI consumption."""
        snapshot_dir = Path(".")
        snapshot_path = snapshot_dir / "ui_snapshot.json"
        history_path = snapshot_dir / "ui_history.jsonl"

        portfolio_status = self.budget_manager.get_portfolio_status()

        # --- P&L enrichment ---
        # Expect per_symbol_snapshots entries to contain at least:
        #   { symbol, action, confidence, price, position(optional) }
        # We'll compute unrealized P&L per open position referencing latest price.
        total_unrealized = 0.0
        total_cost_basis = 0.0
        enriched_positions = []
        try:
            open_positions = portfolio_status.get("open_positions") or []
            # open_positions might already contain dictionaries with entry_price & position_size_usd
            # We will attempt to find latest price from per_symbol_snapshots mapping by symbol.
            price_lookup = {}
            for sym_entry in per_symbol_snapshots:
                sym = (
                    sym_entry.get("symbol")
                    or sym_entry.get("pair")
                    or sym_entry.get("ticker")
                )
                if sym:
                    price_lookup[sym] = (
                        sym_entry.get("price")
                        or sym_entry.get("last_price")
                        or sym_entry.get("close")
                    )

            for pos in open_positions:
                sym = pos.get("symbol")
                entry = pos.get("entry_price") or pos.get("avg_entry") or 0.0
                size_usd = (
                    pos.get("position_size_usd")
                    or pos.get("usd_value")
                    or pos.get("size_usd")
                    or 0.0
                )
                qty = pos.get("quantity") or pos.get("base_size") or 0.0
                side = (pos.get("side") or "").upper()
                last_price = price_lookup.get(sym)
                unrealized = 0.0
                pct = 0.0
                if last_price and entry and qty:
                    # Reconstruct USD cost basis if not provided
                    if size_usd == 0.0:
                        size_usd = qty * entry
                    direction = 1 if side == "BUY" else -1
                    unrealized = direction * (last_price - entry) * qty
                    total_unrealized += unrealized
                    total_cost_basis += size_usd
                    if size_usd:
                        pct = (unrealized / size_usd) * 100.0
                enriched = dict(pos)
                enriched.update(
                    {
                        "last_price": last_price,
                        "unrealized_pnl": unrealized,
                        "unrealized_pnl_pct": pct,
                    }
                )
                enriched_positions.append(enriched)
        except Exception as exc:
            print(f"⚠️  P&L enrichment failed: {exc}")

        total_unrealized_pct = (
            (total_unrealized / total_cost_basis * 100.0) if total_cost_basis else 0.0
        )
        portfolio_status["unrealized_pnl"] = total_unrealized
        portfolio_status["unrealized_pnl_pct"] = total_unrealized_pct
        if enriched_positions:
            portfolio_status["open_positions_enriched"] = enriched_positions

        snapshot = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "symbols": per_symbol_snapshots,
            "portfolio": portfolio_status,
            "config": {
                "min_trade_size": 50.0,
                "initial_capital": self.budget_manager.initial_capital,
            },
            "recent_trades": self.recent_trades,
        }

        # Atomic write
        tmp_path = snapshot_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as tmp:
            json.dump(snapshot, tmp, indent=2)
        os.replace(tmp_path, snapshot_path)

        # Append to history (best-effort)
        try:
            with open(history_path, "a", encoding="utf-8") as hist:
                hist.write(json.dumps(snapshot) + "\n")
        except Exception:
            pass

    def _show_portfolio_status(self) -> None:
        """Show current portfolio status and metrics."""
        status = self.budget_manager.get_portfolio_status()

        print("\n💼 PORTFOLIO STATUS:")
        print(f"   💰 Current Capital: ${status['current_capital']:,.2f}")
        print(f"   💵 Available Capital: ${status['available_capital']:,.2f}")
        print(f"   📊 Open Positions: {status['open_positions']}")
        print(
            f"   💚 Total P&L: ${status['total_pnl']:+,.2f} ({status['total_pnl_pct']:+.1f}%)"
        )
        print(f"   📈 Win Rate: {status['win_rate']:.1f}%")
        print(f"   🎯 Total Trades: {status['total_trades']}")


def main() -> None:
    """Start the live trading bot with auto-liquidation."""
    print("🔥 STARTING LIVE TRADING BOT WITH AUTO-LIQUIDATION")
    print("⚠️  PAPER=false - This will place REAL orders!")
    print("🔄 Auto-liquidation enabled for low capital situations")
    print("Press Ctrl+C to stop")

    # Run preflight check to verify API keys
    preflight_check()

    bot = LiveTradingBot()

    while True:
        try:
            bot.run_trading_cycle()
            time.sleep(60)  # 1 minute between cycles
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
