"""
Market Regime Detection Demo

This script demonstrates the market regime detection capability
of the enhanced MultiSignalTradingEngine.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np

# Conditionally import matplotlib
has_matplotlib = False
try:
    import matplotlib.pyplot as plt

    has_matplotlib = True
except ImportError:
    pass

# Add the project root to path to import the trading engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # type: ignore
from src.core.unified_trading_engine import MultiSignalTradingEngine  # noqa: E402


class MarketRegimeSimulation:
    """
    Simulates different market regimes to test the trading engine's
    regime detection and adaptation capabilities.
    """

    def __init__(self, engine, days: int = 30):
        self.engine = engine
        self.start_price = 10000.0  # Starting price
        self.days = days  # Simulation length in days
        self.hourly_intervals = 24 * days  # Hourly price points
        self.prices = []
        self.volumes = []
        self.detected_regimes = []
        self.regime_confidences = []
        self.trade_results = []

        # Placeholder for regime visualization data
        self.regime_viz_data = {}

    def generate_price_data(self):
        """Generate synthetic price data with different market regimes"""
        prices = [self.start_price]
        volumes = []

        # Create regime segments
        regimes = [
            # Start with bull market
            {"regime": "bull", "days": 10, "trend": 0.005, "volatility": 0.02},
            # Then sideways market
            {"regime": "sideways", "days": 8, "trend": 0.0001, "volatility": 0.01},
            # Then bear market
            {"regime": "bear", "days": 6, "trend": -0.006, "volatility": 0.025},
            # End with sideways market
            {"regime": "sideways", "days": 6, "trend": 0.0002, "volatility": 0.015},
        ]

        # Generate hourly prices following the regime pattern
        hour = 0

        for regime in regimes:
            hours_in_regime = regime["days"] * 24
            trend = regime["trend"]  # Hourly trend
            volatility = regime["volatility"]  # Hourly volatility

            for i in range(hours_in_regime):
                if hour >= self.hourly_intervals:
                    break

                # Apply trend and random noise
                last_price = prices[-1]

                # Add trend component
                next_price = last_price * (1 + trend)

                # Add random volatility component
                next_price = next_price * (1 + np.random.normal(0, volatility))

                # Apply regime-specific patterns
                if regime["regime"] == "bull":
                    # Bull markets have occasional larger jumps up
                    if np.random.random() < 0.05:  # 5% chance
                        next_price = next_price * (1 + np.random.uniform(0.01, 0.03))

                    # More volume in bull markets
                    volume = np.random.uniform(1.0, 2.5) * last_price / 1000

                elif regime["regime"] == "bear":
                    # Bear markets have occasional larger drops
                    if np.random.random() < 0.05:  # 5% chance
                        next_price = next_price * (1 - np.random.uniform(0.01, 0.04))

                    # Higher volume on dumps in bear markets
                    volume = np.random.uniform(1.2, 3.0) * last_price / 1000

                else:  # sideways
                    # Sideways markets sometimes hit resistance/support
                    if np.random.random() < 0.1:  # 10% chance
                        # Mean reversion
                        distance_from_mean = (next_price / prices[0]) - 1
                        next_price = next_price * (1 - 0.1 * distance_from_mean)

                    # Lower volume in sideways markets
                    volume = np.random.uniform(0.5, 1.5) * last_price / 1000

                prices.append(next_price)  # type: ignore
                volumes.append(volume)  # type: ignore
                hour += 1

        # Trim to exact length needed
        self.prices = prices[: self.hourly_intervals + 1]
        self.volumes = volumes[: self.hourly_intervals]

        print(
            f"Generated {len(self.prices) - 1} hourly price points across {len(regimes)} market regimes"
        )

    async def run_simulation(self):
        """Run the market regime simulation"""
        if not self.prices:
            self.generate_price_data()

        print("\n🚀 Starting market regime simulation...")
        print(f"Initial price: ${self.prices[0]:,.2f}")
        print(f"Duration: {self.days} days ({self.hourly_intervals} hourly intervals)")

        # Process each hour
        for hour in range(self.hourly_intervals):
            # Get current price and volume
            current_price = self.prices[hour + 1]
            current_volume = self.volumes[hour]

            # Collect signals with price data for regime detection
            signals = await self.engine.collect_all_signals(
                current_price, current_volume
            )

            # Make trading decision
            decision = self.engine.make_ml_decision(signals)

            # Simulate trade result based on price movement
            next_hour = min(hour + 1, self.hourly_intervals - 1)
            price_change = (self.prices[next_hour + 1] / current_price) - 1

            # Calculate PnL based on decision and price change
            if decision["action"] == "BUY":
                pnl = price_change * 100  # Simplified PnL calculation
            elif decision["action"] == "SELL":
                pnl = -price_change * 100  # Profit from price drop
            else:  # HOLD
                pnl = 0

            # Apply position sizing
            pnl *= decision["position_size"] * 10  # Scale for better visualization

            trade_result = {
                "action": decision["action"],
                "pnl": pnl,
                "confidence": decision["confidence"],
                "timestamp": (datetime.now() + timedelta(hours=hour)).isoformat(),
                "price": current_price,
                "signals": list(signals.keys()),  # type: ignore
                "signal_values": signals,
                "regime": decision.get("regime", "unknown"),
            }

            # Update ML weights based on trade result
            self.engine.update_ml_weights(trade_result)

            # Store trade result
            self.trade_results.append(trade_result)  # type: ignore

            # Store detected regime info
            self.detected_regimes.append(decision.get("regime", "unknown"))  # type: ignore
            self.regime_confidences.append(decision.get("regime_confidence", 0))  # type: ignore

            # Show progress
            if hour % 24 == 0:
                print(
                    f"Day {hour // 24 + 1}: Price ${current_price:,.2f}, "
                    f"Regime: {decision.get('regime', 'unknown')}, "
                    f"Action: {decision['action']}"
                )

        # Get regime visualization data
        self.regime_viz_data = self.engine.get_regime_visualization_data()

        # Print simulation results
        print("\n✅ Simulation complete!")
        print(f"Final price: ${self.prices[-1]:,.2f}")
        print(f"Price change: {((self.prices[-1] / self.prices[0]) - 1) * 100:.2f}%")

        # Get performance stats
        stats = self.engine.get_performance_stats()

        print("\n📊 Trading Performance:")
        print(f"Trades executed: {stats['trades']}")
        print(f"Win rate: {stats['win_rate']:.2f}%")
        print(f"Total PnL: {stats['total_pnl']:.2f}")
        print(f"ML adaptation score: {stats['ml_adaptation']:.2f}")

        print("\n🔮 Market Regime Performance:")
        for regime, perf in stats.get("regime_performance", {}).items():
            if perf["trades"] > 0:
                print(
                    f"{regime.upper()}: {perf['trades']} trades, Win rate: {perf['win_rate']:.2f}%, PnL: {perf['pnl']:.2f}"
                )

        return stats

    def visualize_results(self):
        """Visualize the market regime detection and trading results"""
        if not self.prices or not self.detected_regimes:
            print("No simulation data to visualize")
            return

        # Create figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(
            3, 1, figsize=(14, 14), gridspec_kw={"height_ratios": [2, 1, 1]}
        )

        # Plot 1: Price and Regimes
        hours = range(len(self.prices))

        # Plot price
        ax1.plot(hours, self.prices, "b-", label="Price", alpha=0.7)
        ax1.set_title("Price and Detected Market Regimes")
        ax1.set_ylabel("Price")
        ax1.grid(True, alpha=0.3)

        # Add regime background colors
        regime_colors = {
            "bull": "lightgreen",
            "bear": "lightcoral",
            "sideways": "lightyellow",
            "unknown": "lightgray",
        }

        # Plot vertical spans for each regime
        current_regime = None
        start_hour = 0

        for hour, regime in enumerate(self.detected_regimes):
            if regime != current_regime or hour == len(self.detected_regimes) - 1:
                if current_regime is not None:
                    ax1.axvspan(
                        start_hour,
                        hour,
                        alpha=0.2,
                        color=regime_colors.get(current_regime, "lightgray"),
                    )
                current_regime = regime
                start_hour = hour

        # Plot 2: Regime Confidence
        ax2.plot(range(len(self.regime_confidences)), self.regime_confidences, "r-")
        ax2.set_title("Regime Detection Confidence")
        ax2.set_ylabel("Confidence")
        ax2.set_ylim([0, 1])
        ax2.grid(True, alpha=0.3)

        # Plot 3: Cumulative PnL
        cumulative_pnl = [0]
        for trade in self.trade_results:
            cumulative_pnl.append(cumulative_pnl[-1] + trade["pnl"])  # type: ignore

        ax3.plot(range(len(cumulative_pnl)), cumulative_pnl, "g-")
        ax3.set_title("Cumulative PnL")
        ax3.set_xlabel("Hours")
        ax3.set_ylabel("PnL")
        ax3.grid(True, alpha=0.3)

        # Add legend for regimes
        if has_matplotlib:
            try:
                from matplotlib.patches import Patch

                legend_elements = [
                    Patch(facecolor=color, alpha=0.2, label=regime)
                    for regime, color in regime_colors.items()
                ]
            except ImportError:
                legend_elements = []
        ax1.legend(handles=legend_elements, loc="upper left")

        plt.tight_layout()
        plt.savefig("market_regime_simulation.png")
        plt.close()

        print("✅ Visualization saved to 'market_regime_simulation.png'")

        # Create signal performance by regime visualization
        self._visualize_signal_regime_performance()

    def _visualize_signal_regime_performance(self):
        """Visualize signal performance by market regime"""
        if not self.regime_viz_data:
            return

        signal_perf = self.regime_viz_data.get("signal_regime_performance", {})
        if not signal_perf:
            return

        regimes = list(signal_perf.keys())  # type: ignore

        # Collect all unique signals across regimes
        all_signals = set()
        for regime in signal_perf:
            all_signals.update(signal_perf[regime].keys())

        all_signals = sorted(all_signals)

        # Prepare data for bar chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Plot 1: Win rates by signal and regime
        width = 0.8 / len(regimes)
        for i, regime in enumerate(regimes):
            win_rates = []
            for signal in all_signals:
                if signal in signal_perf.get(regime, {}):
                    win_rates.append(signal_perf[regime][signal].get("win_rate", 0))  # type: ignore
                else:
                    win_rates.append(0)  # type: ignore

            x = np.arange(len(all_signals))
            ax1.bar(
                x + i * width - width * (len(regimes) - 1) / 2,
                win_rates,
                width,
                label=regime,
            )

        ax1.set_title("Signal Win Rates by Market Regime")
        ax1.set_xlabel("Signal")
        ax1.set_ylabel("Win Rate %")
        ax1.set_xticks(range(len(all_signals)))
        ax1.set_xticklabels(all_signals, rotation=45)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: PnL by signal and regime
        for i, regime in enumerate(regimes):
            pnl_values = []
            for signal in all_signals:
                if signal in signal_perf.get(regime, {}):
                    pnl_values.append(signal_perf[regime][signal].get("total_pnl", 0))  # type: ignore
                else:
                    pnl_values.append(0)  # type: ignore

            ax2.bar(
                x + i * width - width * (len(regimes) - 1) / 2,
                pnl_values,
                width,
                label=regime,
            )

        ax2.set_title("Signal PnL by Market Regime")
        ax2.set_xlabel("Signal")
        ax2.set_ylabel("Total PnL")
        ax2.set_xticks(range(len(all_signals)))
        ax2.set_xticklabels(all_signals, rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig("signal_regime_performance.png")
        plt.close()

        print(
            "✅ Signal performance visualization saved to 'signal_regime_performance.png'"
        )


async def main():
    # Create trading engine with enhanced ML and regime detection
    engine = MultiSignalTradingEngine(enhanced_ml=True, regime_aware=True)

    # Create and run the simulation
    simulation = MarketRegimeSimulation(engine, days=30)
    await simulation.run_simulation()

    # Visualize the results
    simulation.visualize_results()

    # Save statistics to file
    stats = engine.get_performance_stats()
    with open("market_regime_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("✅ Statistics saved to 'market_regime_stats.json'")


if __name__ == "__main__":
    asyncio.run(main())
