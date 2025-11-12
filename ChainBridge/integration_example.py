#!/usr/bin/env python3
"""
Integration Example: Enhanced Multi-Signal Bot with Kraken Paper Trading
========================================================================

This example shows how to integrate the new KrakenPaperLiveBot with the existing
multi-signal bot architecture for enhanced paper trading capabilities.

Key Integration Points:
1. Replace simple paper trading with professional Kraken engine
2. Add ML signal processing and aggregation
3. Implement advanced risk management
4. Enable performance tracking and analytics
5. Export comprehensive trade journals

Usage:
    python integration_example.py

Author: BIGmindz
Version: 1.0.0
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import existing components
try:
    from core.module_manager import ModuleManager
    from MultiSignalBot import MultiSignalBot
except ImportError:
    print(
        "Note: Existing bot components not available. Using mock classes for demonstration."
    )

    class MultiSignalBot:
        def __init__(self, *args, **kwargs):
            self.config = kwargs.get("config", {})
            print("Mock MultiSignalBot initialized")

    class ModuleManager:
        def __init__(self):
            self.modules = {}


# Import new Kraken paper trading components
try:
    from src.kraken_paper_live_bot import create_kraken_paper_bot
    from src.ml_trading_integration import MLTradingIntegration
except ImportError as e:
    print(f"Kraken components not available: {e}")
    print("Run this from the repository root directory.")
    sys.exit(1)


class EnhancedMultiSignalBot:
    """
    Enhanced Multi-Signal Bot with Professional Kraken Paper Trading

    This class integrates the existing multi-signal bot with the new
    Kraken paper trading engine for professional-grade paper trading.
    """

    def __init__(
        self,
        config_path: str = "config.yaml",
        enhanced_config_path: str = "config/kraken_paper_trading.yaml",
    ):
        """
        Initialize enhanced multi-signal bot

        Args:
            config_path: Path to existing bot configuration
            enhanced_config_path: Path to Kraken paper trading configuration
        """
        print("🚀 Initializing Enhanced Multi-Signal Bot with Kraken Paper Trading")
        print("=" * 70)

        # Load configurations
        self.config = self._load_config(config_path)
        self.enhanced_config = self._load_config(enhanced_config_path)

        # Initialize existing bot components
        try:
            self.original_bot = MultiSignalBot(config_path=config_path)
            print("✅ Original MultiSignalBot initialized")
        except Exception as e:
            print(f"⚠️  Original bot unavailable: {e}")
            self.original_bot = None

        # Initialize enhanced Kraken paper trading
        self.kraken_bot = create_kraken_paper_bot(config_dict=self.enhanced_config)
        print(
            f"✅ Kraken Paper Trading Bot initialized with ${self.kraken_bot.budget_manager.initial_capital:,.2f}"
        )

        # Initialize ML integration
        self.module_manager = ModuleManager()
        self.ml_integration = MLTradingIntegration(
            self.kraken_bot,
            self.module_manager,
            self.enhanced_config.get("ml_integration", {}),
        )
        print("✅ ML Integration layer initialized")

        # Trading state
        self.is_running = False
        self.symbols = self.enhanced_config.get("symbols", ["BTC/USD", "ETH/USD"])

        # Setup logging
        self.logger = self._setup_logging()

        print(f"📈 Trading symbols: {', '.join(self.symbols)}")
        print("=" * 70)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            import yaml

            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
        except ImportError:
            self.logger.warning("PyYAML not available, using default config")
            return {
                "initial_capital": 10000.0,
                "symbols": ["BTC/USD", "ETH/USD"],
                "risk_management": {"max_position_size": 0.1},
            }

    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("enhanced_multi_signal_bot.log"),
            ],
        )
        return logging.getLogger(__name__)

    async def initialize_exchange(self):
        """Initialize exchange connections"""
        print("🔌 Initializing exchange connections...")

        # Mock exchange for demonstration
        class MockExchange:
            def fetch_ticker(self, symbol):
                prices = {
                    "BTC/USD": {
                        "last": 45000,
                        "bid": 44950,
                        "ask": 45050,
                        "quoteVolume": 1500000,
                        "timestamp": datetime.now().timestamp() * 1000,
                    },
                    "ETH/USD": {
                        "last": 3200,
                        "bid": 3195,
                        "ask": 3205,
                        "quoteVolume": 800000,
                        "timestamp": datetime.now().timestamp() * 1000,
                    },
                }
                return prices.get(
                    symbol,
                    {
                        "last": 100,
                        "bid": 99.5,
                        "ask": 100.5,
                        "quoteVolume": 100000,
                        "timestamp": datetime.now().timestamp() * 1000,
                    },
                )

            def fetch_ohlcv(self, symbol, timeframe, limit=100):
                # Return mock OHLCV data
                return [
                    [
                        datetime.now().timestamp() * 1000,
                        45000,
                        45100,
                        44900,
                        45050,
                        1000,
                    ]
                    for _ in range(limit)
                ]

        mock_exchange = MockExchange()
        await self.kraken_bot.initialize_exchange(mock_exchange)
        print("✅ Exchange connections initialized")

    async def run_enhanced_trading_cycle(self) -> Dict[str, Any]:
        """
        Run one enhanced trading cycle with both original and new features

        Returns:
            Dictionary containing cycle results
        """
        cycle_start = datetime.now(timezone.utc)
        print(f"\n⏰ Starting trading cycle at {cycle_start.strftime('%H:%M:%S')}")

        results = {
            "timestamp": cycle_start.isoformat(),
            "symbols_processed": 0,
            "signals_generated": 0,
            "trades_executed": 0,
            "errors": [],
        }

        try:
            # Step 1: Update price data (simulate real-time updates)
            await self._update_price_data()

            # Step 2: Process ML signals for all symbols
            print("🧠 Processing ML signals...")
            ml_results = await self.ml_integration.process_trading_signals(self.symbols)

            results["symbols_processed"] = len(ml_results)

            # Step 3: Execute trading decisions
            for symbol, result in ml_results.items():
                try:
                    if "decision" in result and result["decision"]["action"] != "HOLD":
                        decision = result["decision"]
                        print(
                            f"📊 {symbol}: {decision['action']} signal (confidence: {decision['confidence']:.2f})"
                        )

                        results["signals_generated"] += 1

                        if "execution" in result and result["execution"].get("success"):
                            results["trades_executed"] += 1
                            position = result["execution"]["position"]
                            print(f"   ✅ Trade executed: Position {position.id}")

                    elif "error" in result:
                        error_msg = f"{symbol}: {result['error']}"
                        results["errors"].append(error_msg)  # type: ignore
                        print(f"   ❌ {error_msg}")

                except Exception as e:
                    error_msg = f"Error processing {symbol}: {e}"
                    results["errors"].append(error_msg)  # type: ignore
                    print(f"   ❌ {error_msg}")

            # Step 4: Update performance metrics
            dashboard = self.kraken_bot.get_performance_dashboard()
            results["portfolio_value"] = dashboard["account"]["portfolio_value"]
            results["total_return_pct"] = dashboard["account"]["total_return_pct"]
            results["active_positions"] = dashboard["positions"]["active_count"]

            # Step 5: Log cycle summary
            print("📈 Cycle Summary:")
            print(f"   Symbols Processed: {results['symbols_processed']}")
            print(f"   Signals Generated: {results['signals_generated']}")
            print(f"   Trades Executed: {results['trades_executed']}")
            print(f"   Portfolio Value: ${results['portfolio_value']:,.2f}")
            print(f"   Total Return: {results['total_return_pct']:+.2f}%")
            print(f"   Active Positions: {results['active_positions']}")

        except Exception as e:
            error_msg = f"Cycle error: {e}"
            results["errors"].append(error_msg)  # type: ignore
            self.logger.error(error_msg)

        return results

    async def _update_price_data(self):
        """Update price data for all symbols"""
        import random

        # Simulate price updates
        for symbol in self.symbols:
            if symbol not in self.kraken_bot.price_data:
                # Initialize with base prices
                base_prices = {"BTC/USD": 45000, "ETH/USD": 3200, "ADA/USD": 0.45}
                base_price = base_prices.get(symbol, 100.0)
            else:
                base_price = self.kraken_bot.price_data[symbol].price

            # Add small random movement
            change_pct = random.uniform(-0.005, 0.005)  # ±0.5%
            new_price = base_price * (1 + change_pct)

            # Create price data object
            from src.kraken_paper_live_bot import PriceData

            price_data = PriceData(
                symbol=symbol,
                price=new_price,
                bid=new_price * 0.9995,
                ask=new_price * 1.0005,
                volume_24h=random.uniform(800000, 2000000),
                timestamp=datetime.now(timezone.utc),
                spread=new_price * 0.001,
            )

            self.kraken_bot.price_data[symbol] = price_data

            # Update existing positions
            if symbol in [pos.symbol for pos in self.kraken_bot.positions.values()]:
                self.kraken_bot._update_positions_pnl(symbol, new_price)

    async def run_continuous_trading(self, duration_minutes: int = 60):
        """
        Run continuous trading for specified duration

        Args:
            duration_minutes: How long to run trading
        """
        print(f"🔄 Starting continuous trading for {duration_minutes} minutes")
        print("=" * 70)

        self.is_running = True
        cycle_count = 0
        start_time = datetime.now(timezone.utc)

        try:
            while self.is_running:
                cycle_count += 1
                print(f"\n--- Trading Cycle {cycle_count} ---")

                # Run trading cycle
                _cycle_results = await self.run_enhanced_trading_cycle()

                # Check if we should stop
                elapsed_minutes = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() / 60
                if elapsed_minutes >= duration_minutes:
                    print(
                        f"\n⏹️  Stopping after {elapsed_minutes:.1f} minutes ({cycle_count} cycles)"
                    )
                    break

                # Wait before next cycle
                await asyncio.sleep(10)  # 10 second intervals for demo

        except KeyboardInterrupt:
            print("\n⏸️  Trading interrupted by user")
        except Exception as e:
            print(f"\n❌ Trading error: {e}")
        finally:
            self.is_running = False
            await self._shutdown_trading()

    async def _shutdown_trading(self):
        """Shutdown trading and generate final reports"""
        print("\n🛑 Shutting down enhanced trading...")

        # Stop Kraken bot
        self.kraken_bot.stop_trading()

        # Generate final performance report
        print("\n📊 FINAL PERFORMANCE REPORT")
        print("=" * 50)

        dashboard = self.kraken_bot.get_performance_dashboard()
        account = dashboard["account"]
        performance = dashboard["performance"]

        print(f"Initial Capital: ${account['initial_capital']:,.2f}")
        print(f"Final Portfolio: ${account['portfolio_value']:,.2f}")
        print(
            f"Total Return: ${account['total_return']:+,.2f} ({account['total_return_pct']:+.2f}%)"
        )
        print(f"Active Positions: {dashboard['positions']['active_count']}")

        if performance["total_trades"] > 0:
            print(f"Total Trades: {performance['total_trades']}")
            print(f"Win Rate: {performance['win_rate']:.1f}%")
            print(f"Profit Factor: {performance['profit_factor']:.2f}")
            print(f"Largest Win: ${performance['largest_win']:,.2f}")
            print(f"Largest Loss: ${performance['largest_loss']:,.2f}")
            print(f"Max Drawdown: {performance['max_drawdown']:.2%}")

        # Generate ML performance report
        ml_report = self.ml_integration.get_signal_performance_report()
        print("\n🧠 ML Performance:")
        print(f"Active Modules: {ml_report['summary']['active_modules']}")
        print(f"Avg Success Rate: {ml_report['summary']['avg_success_rate']:.2f}")

        # Export trade journal
        journal_path = self.kraken_bot.export_trade_journal()
        print(f"\n📋 Trade journal exported to: {journal_path}")

        print("✅ Shutdown complete")


async def demo_integration():
    """Demonstrate the enhanced multi-signal bot integration"""
    print("🎯 ENHANCED MULTI-SIGNAL BOT INTEGRATION DEMO")
    print("=" * 70)

    try:
        # Create enhanced bot
        _enhanced_bot = EnhancedMultiSignalBot()

        # Initialize exchange connections
        await _enhanced_bot.initialize_exchange()

        # Run a few trading cycles
        print("\n🔄 Running demo trading cycles...")

        for i in range(3):
            print(f"\n--- Demo Cycle {i + 1} ---")
            results = await _enhanced_bot.run_enhanced_trading_cycle()

            # Show results
            print(f"Portfolio: ${results['portfolio_value']:,.2f}")
            print(f"Return: {results['total_return_pct']:+.2f}%")

            # Wait between cycles
            await asyncio.sleep(2)

        # Shutdown and generate reports
        await _enhanced_bot._shutdown_trading()

        print("\n✅ Integration demo completed successfully!")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        raise


async def main():
    """Main function"""
    print("🚀 ENHANCED MULTI-SIGNAL BOT WITH KRAKEN PAPER TRADING")
    print("=" * 70)
    print("This example demonstrates integration of the new Kraken paper trading")
    print("module with the existing multi-signal bot architecture.")
    print("=" * 70)

    try:
        # Run integration demo
        await demo_integration()

        print("\n🎉 INTEGRATION COMPLETE!")
        print("=" * 50)
        print("Key benefits of the enhanced integration:")
        print("✅ Professional paper trading engine")
        print("✅ Advanced risk management")
        print("✅ ML signal processing")
        print("✅ Comprehensive performance tracking")
        print("✅ Detailed trade journaling")
        print("✅ Real-time correlation monitoring")
        print("✅ Emergency risk controls")

    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Integration demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
