#!/usr/bin/env python3
"""
Example script demonstrating the regime performance dashboard.
"""

import os
import sys

import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtesting.dashboard import create_dashboard

# Import the backtester and dashboard
from src.backtesting.regime_backtester import RegimeBacktester


def simple_rsi_strategy(prices, params):
    """
    A simple RSI strategy for demonstration purposes.

    Args:
        prices: Historical price data
        params: Strategy parameters (window, overbought, oversold)

    Returns:
        Array of signals: 1 (buy), -1 (sell), 0 (hold)
    """
    window = params.get("window", 14)
    overbought = params.get("overbought", 70)
    oversold = params.get("oversold", 30)

    # Calculate price changes
    delta = np.zeros_like(prices)
    delta[1:] = prices[1:] - prices[:-1]

    # Create arrays of gains and losses
    gains = np.copy(delta)
    losses = np.copy(delta)
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = abs(losses)

    # Calculate averages using SMA first, then EMA
    avg_gain = np.zeros_like(prices)
    avg_loss = np.zeros_like(prices)

    # Initialize using simple moving average
    if len(prices) >= window:
        avg_gain[window - 1] = np.mean(gains[1:window])
        avg_loss[window - 1] = np.mean(losses[1:window])

    # Calculate for remaining data points using EMA
    for i in range(window, len(prices)):
        avg_gain[i] = (avg_gain[i - 1] * (window - 1) + gains[i]) / window
        avg_loss[i] = (avg_loss[i - 1] * (window - 1) + losses[i]) / window

    # Calculate RSI
    rs = np.zeros_like(prices)
    rsi = np.zeros_like(prices)

    # Avoid division by zero
    for i in range(window, len(prices)):
        if avg_loss[i] == 0:
            rsi[i] = 100
        else:
            rs[i] = avg_gain[i] / avg_loss[i]
            rsi[i] = 100 - (100 / (1 + rs[i]))

    # Generate signals
    signals = np.zeros_like(prices)
    for i in range(window, len(prices)):
        if rsi[i] < oversold:
            signals[i] = 1  # Buy
        elif rsi[i] > overbought:
            signals[i] = -1  # Sell
        else:
            signals[i] = 0  # Hold

    return signals


def generate_demo_data():
    """
    Generate synthetic price data with different market regimes.

    Returns:
        price_data: Synthetic price data
        regime_data: Regime labels for each price point
        regime_labels: Names of the regimes
    """
    # Set random seed for reproducibility
    np.random.seed(42)
    n_points = 1000

    # Base price starts at 100
    price_data = np.zeros(n_points)
    price_data[0] = 100

    # Generate regimes
    regime_data = np.zeros(n_points)

    # Define regime segments
    regime_segments = [
        (0, 200, 0),  # Sideways
        (200, 400, 1),  # Bullish
        (400, 600, 2),  # Bearish
        (600, 800, 3),  # Choppy (volatile sideways)
        (800, 1000, 4),  # Bullish Volatile
    ]

    # Assign regimes
    for start, end, regime in regime_segments:
        regime_data[start:end] = regime

    # Generate price data based on regimes
    for i in range(1, n_points):
        regime = int(regime_data[i])

        if regime == 0:  # Sideways
            drift = 0.0  # No drift
            vol = 0.7  # Low volatility
        elif regime == 1:  # Bullish
            drift = 0.05  # Positive drift
            vol = 0.8  # Normal volatility
        elif regime == 2:  # Bearish
            drift = -0.07  # Negative drift
            vol = 1.0  # Normal volatility
        elif regime == 3:  # Choppy
            drift = 0.0  # No drift
            vol = 1.5  # High volatility
        else:  # Bullish Volatile
            drift = 0.08  # Strong positive drift
            vol = 1.8  # High volatility

        # Random walk with drift
        price_data[i] = price_data[i - 1] * (1 + drift / 100 + vol / 100 * np.random.randn())

    # Create regime labels
    regime_labels = ["Sideways", "Bullish", "Bearish", "Choppy", "Bullish Volatile"]

    return price_data, regime_data, regime_labels


def main():
    """Run the dashboard demonstration."""
    print("Generating demo data...")
    price_data, regime_data, regime_labels = generate_demo_data()

    print(f"Created demo data with {len(price_data)} price points")
    print(f"Regimes: {', '.join(regime_labels)}")

    # Initialize backtester with our data and regime information
    print("Initializing backtester...")
    backtester = RegimeBacktester(price_data, regime_data, regime_labels)

    # Define strategy parameters
    default_params = {"window": 14, "overbought": 70, "oversold": 30}

    # Define regime-specific parameters
    regime_specific_params = {
        "Bullish": {
            "overbought": 75,  # Higher threshold in bull markets
            "oversold": 40,  # Higher oversold threshold too
        },
        "Bearish": {
            "overbought": 60,  # Lower threshold in bear markets
            "oversold": 20,  # Lower oversold threshold too
        },
        "Choppy": {
            "overbought": 65,  # Reduced thresholds in choppy markets
            "oversold": 35,  # to avoid false signals
        },
        "Bullish Volatile": {
            "overbought": 80,  # Much higher threshold in volatile bull markets
            "oversold": 45,  # Higher oversold threshold too
        },
    }

    # Run the backtest
    print("Running backtest...")
    results = backtester.run_backtest(simple_rsi_strategy, default_params, regime_specific_params)

    # Print summary results
    print("\nBacktest Results Summary:")
    print("-" * 50)

    for regime, result in results.items():
        metrics = result["metrics"]
        print(f"\n{regime} Regime:")
        print(f"  Total Return: {metrics['total_return']:.2%}")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"  Win Rate: {metrics['win_rate']:.2%}")

    # Create output directory
    os.makedirs("reports", exist_ok=True)

    # Generate the dashboard
    print("\nGenerating dashboard...")
    create_dashboard(
        results,
        title="RSI Strategy Performance by Market Regime",
        output_dir="reports",
        show_plot=True,
    )

    print("\nDashboard generation completed!")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure all required libraries are installed: numpy, matplotlib")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
