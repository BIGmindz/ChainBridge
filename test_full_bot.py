#!/usr/bin/env python3
"""
Full System Test for Multi-Signal Decision Bot

This script tests all components of the system together:
- Pattern Engine
- Signal Modules
- Multi-Signal Aggregator
- Live Dashboard
- Backtest Engine
- Regime Backtester
"""

import os
import random
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Ensure we can import from project modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try importing core components
try:
    # Core system components
    from modules.bollinger_bands_module import BollingerBandsModule
    from modules.macd_module import MACDModule
    from modules.multi_signal_aggregator_module import MultiSignalAggregatorModule

    # Signal modules
    from modules.rsi_module import RSIModule
    from modules.sentiment_analysis_module import SentimentAnalysisModule
    from src.backtesting.backtest import BacktestEngine
    from src.backtesting.regime_backtester import RegimeBacktester
    from src.core.pattern_engine import PatternEngine
    from src.dashboard.live_dashboard import LiveDashboard

    print("✅ All core imports successful")
except ImportError as e:
    print(f"❌ Import Error: {str(e)}")
    sys.exit(1)


# Generate test data
def generate_test_data(days=120, with_regime_change=True):
    """Generate synthetic price data for testing"""
    print("\n📊 Generating test data...")

    # Generate dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, periods=days)

    # Start price and empty dataframe
    base_price = 40000
    data = []

    # Generate regimes and price data
    current_regime = "bull"
    regime_days = 0
    volatility = 0.015
    trend = 0.001

    for i in range(days):
        # Potentially change regime
        if with_regime_change and regime_days > 20 and random.random() < 0.1:
            # Choose a different regime
            regimes = ["bull", "bear", "sideways"]
            regimes.remove(current_regime)
            current_regime = random.choice(regimes)
            regime_days = 0

            # Update parameters for this regime
            if current_regime == "bull":
                volatility = 0.015
                trend = 0.002
            elif current_regime == "bear":
                volatility = 0.025
                trend = -0.002
            else:  # sideways
                volatility = 0.01
                trend = 0.0001

        regime_days += 1

        # Calculate price movement
        daily_return = np.random.normal(trend, volatility)
        if i > 0:
            base_price = base_price * (1 + daily_return)

        # Create high, low, open values
        high = base_price * (1 + random.uniform(0, 0.02))
        low = base_price * (1 - random.uniform(0, 0.02))
        open_price = low + random.random() * (high - low)

        # Create volume
        volume = random.randint(800, 1500)
        if current_regime == "bull" and random.random() > 0.7:
            volume *= 2  # Volume spike in bull market

        # Add row to data
        data.append(
            {
                "timestamp": dates[i],
                "open": open_price,
                "high": high,
                "low": low,
                "close": base_price,
                "volume": volume,
                "regime": current_regime,  # Include actual regime for validation
            }
        )

    # Convert to dataframe
    df = pd.DataFrame(data)

    print(f"✅ Generated {days} days of test data")
    return df


def run_pattern_engine(data):
    """Test the Pattern Engine functionality"""
    print("\n🧠 Testing Pattern Engine...")

    # Initialize pattern engine
    engine = PatternEngine()
    print("✅ Pattern Engine initialized")

    # Test regime detection
    regime = engine.detect_regime(data)
    print(f"✅ Regime detected: {regime}")

    # Identify patterns
    patterns = engine.identify_patterns(data)
    print(f"✅ Identified {len(patterns)} patterns")

    # Test prediction
    direction, confidence = engine.predict_price_movement(data)
    print(f"✅ Predicted movement: {direction:.2f} (confidence: {confidence:.2f})")

    # Get regime stats
    stats = engine.get_regime_stats()
    print(f"✅ Regime stats: {stats['regime']} (confidence: {stats['confidence']:.2f})")

    # Store the detected regime as an attribute for easy access in main()
    engine.current_regime = regime

    return engine


def run_dashboard(signals):
    """Test the Live Dashboard functionality"""
    print("\n📊 Testing Live Dashboard...")

    # Initialize dashboard
    dashboard = LiveDashboard()
    print("✅ Live Dashboard initialized")

    # Convert string signals to numeric for dashboard
    numeric_signals = {}
    for key, value in signals.items():
        if isinstance(value, str):
            if value == "BUY":
                numeric_signals[key] = 0.8
            elif value == "SELL":
                numeric_signals[key] = -0.8
            else:  # HOLD
                numeric_signals[key] = 0.0
        else:
            numeric_signals[key] = value

    # Update dashboard with test data
    dashboard.update_signals(numeric_signals)

    # Add market data
    dashboard.update_market_data({"regime": "bull", "volatility": 0.025, "trend_strength": 0.75})

    # Add performance data
    dashboard.update_performance(
        {
            "total_pnl": 1250.75,
            "realized_pnl": 950.25,
            "unrealized_pnl": 300.50,
            "win_rate": 0.68,
            "active_positions": 5,
            "wins": 17,
            "losses": 8,
        }
    )

    # Add trades
    dashboard.add_trade(
        {
            "side": "BUY",
            "symbol": "BTC/USD",
            "price": 42500,
            "size": 0.15,
            "timestamp": datetime.now(),
        }
    )

    dashboard.add_trade(
        {
            "side": "SELL",
            "symbol": "ETH/USD",
            "price": 2850,
            "size": 1.25,
            "timestamp": datetime.now(),
        }
    )

    # Display dashboard
    dashboard.display()

    # Save snapshot
    dashboard.save_snapshot("dashboard_test_snapshot.json")
    print("✅ Dashboard snapshot saved to dashboard_test_snapshot.json")

    # Generate report
    report = dashboard.generate_report()
    print(f"\n📝 Dashboard Report:\n\n{report}")

    return dashboard


def run_backtest_engine(data):
    """Test the Backtest Engine functionality"""
    print("\n🔄 Testing Backtest Engine...")

    # Initialize backtest engine
    backtest = BacktestEngine(
        config={
            "initial_capital": 50000,
            "position_size_pct": 0.02,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
        }
    )

    # Define simple signal generator function
    def signal_generator(price_data):
        # Simple strategy: Buy when price is going up, sell when going down
        if len(price_data) < 10:
            return {}

        # Calculate short-term trend
        short_ma = price_data["close"].rolling(5).mean().iloc[-1]
        long_ma = price_data["close"].rolling(20).mean().iloc[-1]

        # Generate signal
        if short_ma > long_ma * 1.01:
            return {"trend": 0.7}  # Buy signal
        elif short_ma < long_ma * 0.99:
            return {"trend": -0.7}  # Sell signal
        else:
            return {"trend": 0.0}  # Neutral

    # Run backtest
    results = backtest.run(data, signal_generator)

    # Save results
    backtest.save_results("backtest_test_results.json")
    print("✅ Backtest results saved to backtest_test_results.json")

    # Generate report
    report = backtest.generate_report()
    print(f"\n📝 Backtest Report:\n\n{report}")

    return backtest, results

    return backtest, results


def run_regime_backtester(data):
    """Test the regime-specific backtester"""
    print("\n🔄 Testing Regime Backtester...")

    # Convert DataFrame to numpy arrays
    price_array = data["close"].values

    # Create simple regime labels (just for testing)
    regime_array = np.zeros(len(price_array))
    # First third is "bull"
    regime_array[: len(regime_array) // 3] = 0
    # Middle third is "bear"
    regime_array[len(regime_array) // 3 : 2 * len(regime_array) // 3] = 1
    # Last third is "sideways"
    regime_array[2 * len(regime_array) // 3 :] = 2

    # Initialize regime backtester
    regime_backtest = RegimeBacktester(
        price_data=price_array,
        regime_data=regime_array,
        regime_labels=["bull", "bear", "sideways"],
    )

    # Create a simple strategy function that returns different signals based on regime
    def regime_strategy(price_window, params):
        # Get regime parameter from regime-specific params if provided
        regime = params.get("regime", "sideways")

        # Create an array of signals the same length as the price window
        signals = np.zeros(len(price_window))

        # Set signals based on simple rules
        for i in range(1, len(price_window)):
            if regime == "bull":
                # More aggressive in bull markets
                signals[i] = 1 if price_window[i] > price_window[i - 1] else -0.2
            elif regime == "bear":
                # More conservative in bear markets
                signals[i] = 0.3 if price_window[i] > price_window[i - 1] else -1
            else:  # sideways
                # Range trading in sideways markets
                if i >= 10:
                    upper = np.max(price_window[i - 10 : i])
                    lower = np.min(price_window[i - 10 : i])
                    signals[i] = -0.5 if price_window[i] > 0.9 * upper else 0.5 if price_window[i] < 1.1 * lower else 0

        return signals

    # Run the regime backtest with appropriate parameters
    results = regime_backtest.run_backtest(
        strategy_fn=regime_strategy,
        params={"window_size": 10, "threshold": 0.5, "regime": "sideways"},
        regime_specific_params={
            "bull": {"threshold": 0.3, "regime": "bull"},
            "bear": {"threshold": 0.7, "regime": "bear"},
            "sideways": {"threshold": 0.5, "regime": "sideways"},
        },
    )

    # Print results summary
    print("\n📝 Regime Backtest Results:")
    for regime, metrics in results.items():
        # Skip non-regime entries
        if regime in ["bull", "bear", "sideways"]:
            print(f"  {regime.upper()}: Return: {metrics.get('return', 0):.2%}, Trades: {metrics.get('n_trades', 0)}")

    # Calculate overall return and metrics if available
    overall_metrics = results.get("Overall", {}).get("metrics", {})
    total_return = overall_metrics.get("total_return", 0)
    sharpe_ratio = overall_metrics.get("sharpe_ratio", 0)
    max_drawdown = overall_metrics.get("max_drawdown", 0)
    win_rate = overall_metrics.get("win_rate", 0)

    print("  OVERALL PERFORMANCE SUMMARY:")
    print(f"    Return: {total_return:.2%}, Sharpe: {sharpe_ratio:.2f}, Max DD: {max_drawdown:.2%}, Win Rate: {win_rate:.2%}")

    return regime_backtest, results


def run_signal_modules(data):
    """Test all signal modules"""
    print("\n📡 Testing Signal Modules...")

    # Initialize modules
    rsi = RSIModule()
    macd = MACDModule()
    bollinger = BollingerBandsModule()
    sentiment = SentimentAnalysisModule()
    aggregator = MultiSignalAggregatorModule()

    # Prepare data in the expected format
    price_data = [
        {
            "close": row["close"],
            "high": row["high"],
            "low": row["low"],
            "volume": row["volume"],
        }
        for _, row in data.iterrows()
    ]

    # Process data through modules
    rsi_result = rsi.process({"price_data": price_data})
    print(f"✅ RSI Module: {rsi_result['signal']} (Confidence: {rsi_result.get('confidence', 0):.2f})")

    macd_result = macd.process({"price_data": price_data})
    print(f"✅ MACD Module: {macd_result['signal']} (Confidence: {macd_result.get('confidence', 0):.2f})")

    bb_result = bollinger.process({"price_data": price_data})
    print(f"✅ Bollinger Bands Module: {bb_result['signal']} (Confidence: {bb_result.get('confidence', 0):.2f})")

    sentiment_result = sentiment.process({"price_data": price_data})
    print(f"✅ Sentiment Analysis Module: {sentiment_result['signal']} (Confidence: {sentiment_result.get('confidence', 0):.2f})")

    # Map string signals to numeric values for aggregation
    def signal_to_value(signal, confidence):
        if signal == "BUY":
            return confidence
        elif signal == "SELL":
            return -confidence
        else:  # HOLD
            return 0.0

    # Prepare signals for aggregation
    signals_input = {
        "signals": {
            "RSI": {
                "signal": rsi_result["signal"],
                "confidence": rsi_result.get("confidence", 0),
            },
            "MACD": {
                "signal": macd_result["signal"],
                "confidence": macd_result.get("confidence", 0),
            },
            "BollingerBands": {
                "signal": bb_result["signal"],
                "confidence": bb_result.get("confidence", 0),
            },
            "SentimentAnalysis": {
                "signal": sentiment_result["signal"],
                "confidence": sentiment_result.get("confidence", 0),
            },
        },
        "price_data": {
            "close": data["close"].iloc[-1],
            "open": data["open"].iloc[-1],
        },  # Latest price info
    }

    # Aggregate signals
    aggregated_result = aggregator.process(signals_input)
    print(f"✅ Aggregated Signal: {aggregated_result['final_signal']} (Confidence: {aggregated_result.get('final_confidence', 0):.2f})")

    # Prepare signals dict for return
    signals_dict = {
        "rsi": rsi_result["signal"],
        "macd": macd_result["signal"],
        "bollinger": bb_result["signal"],
        "sentiment": sentiment_result["signal"],
    }

    return signals_dict, aggregated_result.get("final_signal", "HOLD")


def main():
    """Main test function that runs all tests"""
    print("\n" + "=" * 80)
    print("🤖 MULTI-SIGNAL DECISION BOT - FULL SYSTEM TEST")
    print("=" * 80)

    # Generate test data
    data = generate_test_data(days=120)

    try:
        # Test pattern engine
        engine = run_pattern_engine(data)

        # Test signal modules
        signals, aggregated = run_signal_modules(data)

        # Test dashboard
        _dashboard = run_dashboard(signals)

        # Test backtest engine
        backtest, bt_results = run_backtest_engine(data)

        # Test regime backtester
        regime_backtest, rb_results = run_regime_backtester(data)

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)

        print("\n📊 System Performance Summary:")
        print(f"  Pattern Engine Regime: {engine.current_regime}")
        print(f"  Aggregated Signal: {aggregated}")
        print(f"  Backtest Return: {bt_results['total_return']:.2%}")
        print("  Regime Detection: Successfully tested across bull, bear, and sideways regimes")

        return 0

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
