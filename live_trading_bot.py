#!/usr/bin/env python3
"""
LIVE TRADING BOT WITH AUTO-LIQUIDATION
Automatically liquidates positions when capital runs low
"""

import os
import sys
import time
from datetime import datetime

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
from modules.new_listings_radar import NewListingsRadar
from modules.multi_signal_aggregator_module import MultiSignalAggregatorModule


# Preflight check to ensure API keys are loaded
def preflight_check():
    api_key = os.environ.get("API_KEY")
    api_secret = os.environ.get("API_SECRET")
    if not api_key or not api_secret:
        print("❌ Missing API_KEY or API_SECRET in environment.")
        sys.exit(1)
    else:
        print(f"✅ API keys loaded. API_KEY: {api_key[:10]}..., API_SECRET: {api_secret[:10]}...")


class LiveTradingBot:
    def __init__(self):
        print("🚀 INITIALIZING LIVE TRADING BOT WITH MULTI-SIGNAL AGGREGATION")

        # Setup exchange with API keys
        self.exchange = setup_exchange("kraken", api_config)

        # Initialize budget manager with live mode
        self.budget_manager = BudgetManager(initial_capital=10000.0, exchange=self.exchange, live_mode=True)

        # Initialize exchange adapter
        self.exchange_adapter = ExchangeAdapter(exchange=self.exchange, config={})

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
        print("🔄 MULTI-SIGNAL AGGREGATION ENABLED - All signals flow through aggregator")
        print("📈 Signal Modules: RSI, MACD, Bollinger Bands, Volume Profile, Sentiment Analysis,")
        print("   Logistics Signals, Global Macro, Region-Specific Crypto, New Listings Radar")

    def _initialize_signal_modules(self):
        """Initialize all signal modules and aggregator"""
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
        self.new_listings_radar = NewListingsRadar({})
        self.aggregator = MultiSignalAggregatorModule()

        # Register modules with manager
        self.module_manager.register_module("rsi", self.rsi)
        self.module_manager.register_module("macd", self.macd)
        self.module_manager.register_module("bollinger", self.bollinger)
        self.module_manager.register_module("volume", self.volume)
        self.module_manager.register_module("sentiment", self.sentiment)
        self.module_manager.register_module("logistics", self.logistics)
        self.module_manager.register_module("global_macro", self.global_macro)
        self.module_manager.register_module("adoption_tracker", self.adoption_tracker)
        self.module_manager.register_module("region_crypto", self.region_crypto)
        self.module_manager.register_module("new_listings_radar", self.new_listings_radar)
        self.module_manager.register_module("aggregator", self.aggregator)

        print("✅ All signal modules initialized and registered")

    def run_trading_cycle(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === TRADING CYCLE ===")

        # Check if we need to liquidate due to low capital
        self._check_and_liquidate_if_needed()

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

                # Check if we have enough capital for a trade
                min_trade_size = 50.0  # $50 minimum
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

                # Execute trade if confidence is high enough
                if confidence >= 0.25 and signal != "HOLD":
                    self._execute_trade(symbol, signal, price, confidence)

            except Exception as e:
                print(f"❌ Error with {symbol}: {e}")

        # Show portfolio status
        self._show_portfolio_status()

        print("✅ Cycle completed")

    def _check_and_liquidate_if_needed(self):
        """Check capital levels and liquidate if needed"""
        try:
            # Check if capital is below threshold
            threshold = 100.0  # $100 minimum
            if self.budget_manager.available_capital < threshold:
                print(f"⚠️  LOW CAPITAL ALERT: ${self.budget_manager.available_capital:.2f} < ${threshold:.2f}")

                # Trigger automatic liquidation
                liquidation_result = self.budget_manager.check_low_capital_and_liquidate(self.exchange_adapter)

                if liquidation_result["status"] == "recovered":
                    print(f"💰 CAPITAL RECOVERED: ${liquidation_result['available_capital']:,.2f}")
                else:
                    print(f"⚠️  CAPITAL STILL LOW: ${liquidation_result['available_capital']:,.2f}")

        except Exception as e:
            print(f"❌ Error checking liquidation: {e}")

    def _execute_trade(self, symbol, signal, price, confidence):
        try:
            # Calculate position size using budget manager
            position_info = self.budget_manager.calculate_position_size(symbol=symbol, signal_confidence=confidence, price=price)

            position_size = position_info["size"]

            if position_size < 10.0:  # Minimum $10 trade
                print(f"⚠️  Position size too small: ${position_size:.2f}")
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

            if order:
                # Record the position in budget manager
                self.budget_manager.open_position(
                    symbol=symbol,
                    side=signal,
                    entry_price=price,
                    position_size=position_size,
                    stop_loss=price * 0.97,  # 3% stop loss
                    take_profit=price * 1.06,  # 6% take profit
                )

                print(f"✅ {signal} order placed for {symbol} at ${price}")
            else:
                print(f"❌ Failed to place {signal} order for {symbol}")

        except Exception as e:
            print(f"❌ Trade execution error: {e}")

    def _calculate_rsi(self, ohlcv, period=14):
        """Calculate RSI using Wilder's smoothing method"""
        if len(ohlcv) < period + 1:
            return 50.0  # Default neutral RSI

        # Extract closing prices
        closes = [candle[4] for candle in ohlcv]  # OHLCV format: [timestamp, open, high, low, close, volume]

        # Calculate price changes
        changes = []
        for i in range(1, len(closes)):
            changes.append(closes[i] - closes[i - 1])

        # Calculate gains and losses
        gains = [max(change, 0) for change in changes]
        losses = [max(-change, 0) for change in changes]

        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

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

    def _generate_multi_signal(self, symbol, ohlcv, price):
        """Generate aggregated signal from all modules"""
        try:
            # Prepare price data for modules
            price_data = self._prepare_price_data(ohlcv, symbol)

            # Run all individual signal modules
            module_signals = {}

            # RSI signal
            module_signals["RSI"] = self._process_module(self.rsi, "RSI", {"price_data": price_data})

            # MACD signal
            module_signals["MACD"] = self._process_module(self.macd, "MACD", {"price_data": price_data})

            # Bollinger Bands signal
            module_signals["BollingerBands"] = self._process_module(self.bollinger, "BollingerBands", {"price_data": price_data})

            # Volume Profile signal
            module_signals["VolumeProfile"] = self._process_module(self.volume, "VolumeProfile", {"price_data": price_data})

            # Sentiment Analysis signal
            module_signals["SentimentAnalysis"] = self._process_module(self.sentiment, "SentimentAnalysis", {"price_data": price_data})

            # Logistics signal
            module_signals["LogisticsSignal"] = self._process_module(
                self.logistics, "LogisticsSignal", {"price_data": price_data, "symbol": symbol}
            )

            # Global Macro signal
            module_signals["GlobalMacro"] = self._process_module(
                self.global_macro, "GlobalMacro", {"price_data": price_data, "symbol": symbol}
            )

            # Adoption Tracker signal
            module_signals["AdoptionTracker"] = self._process_module(self.adoption_tracker, "AdoptionTracker", {"symbol": symbol})

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
                self.region_crypto, "RegionCryptoMapper", {"symbol": symbol, "macro_signals": macro_test_signals}
            )

            # New Listings Radar
            try:
                listing_signal = self.new_listings_radar.get_signal()
                if listing_signal.get("coin", "").upper() in symbol:
                    module_signals["NewListingsRadar"] = {
                        "signal": listing_signal.get("action", "HOLD"),
                        "confidence": listing_signal.get("confidence", 0.0),
                        "value": 0,
                    }
                else:
                    module_signals["NewListingsRadar"] = {"signal": "HOLD", "confidence": 0.0, "value": 0}
            except:
                module_signals["NewListingsRadar"] = {"signal": "HOLD", "confidence": 0.0, "value": 0}

            # Aggregate all signals through MultiSignalAggregatorModule
            agg_input = {
                "signals": module_signals,
                "price_data": price_data[-1] if price_data else {"close": price},
            }

            agg_result = self.aggregator.process(agg_input)

            if not isinstance(agg_result, dict) or "signal" not in agg_result:
                agg_result = {"signal": "HOLD", "confidence": 0.5}

            return {"signal": agg_result.get("signal", "HOLD"), "confidence": agg_result.get("confidence", 0.5), "modules": module_signals}

        except Exception as e:
            print(f"❌ Error in multi-signal generation: {e}")
            return {"signal": "HOLD", "confidence": 0.0, "modules": {}}

    def _process_module(self, module, name, data):
        """Process individual signal module with error handling"""
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

    def _prepare_price_data(self, ohlcv, symbol):
        """Prepare OHLCV data in format expected by signal modules"""
        if not ohlcv:
            return []

        price_data = []
        for candle in ohlcv:
            price_data.append(
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

    def _display_module_signals(self, module_signals):
        """Display individual module signals"""
        indicators = []
        for mod_name, data in module_signals.items():
            if data["signal"] == "BUY":
                indicators.append(f"🟢 {mod_name}")
            elif data["signal"] == "SELL":
                indicators.append(f"🔴 {mod_name}")
            else:
                indicators.append(f"⚪ {mod_name}")

        print(f"            Signals: {' | '.join(indicators)}")

    def _show_portfolio_status(self):
        """Show current portfolio status"""
        status = self.budget_manager.get_portfolio_status()

        print("\n💼 PORTFOLIO STATUS:")
        print(f"   💰 Current Capital: ${status['current_capital']:,.2f}")
        print(f"   💵 Available Capital: ${status['available_capital']:,.2f}")
        print(f"   📊 Open Positions: {status['open_positions']}")
        print(f"   💚 Total P&L: ${status['total_pnl']:+,.2f} ({status['total_pnl_pct']:+.1f}%)")
        print(f"   📈 Win Rate: {status['win_rate']:.1f}%")
        print(f"   🎯 Total Trades: {status['total_trades']}")


def main():
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
