"""
Example script demonstrating the use of the RegimeBacktester class.
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # type: ignore

# Import the backtester
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


def main():
    """Run a simple backtest demonstration."""
    # Generate synthetic price data (bull, bear, and sideways regimes)
    np.random.seed(42)
    n_points = 500

    # Base price starts at 100
    price_data = np.zeros(n_points)
    price_data[0] = 100

    # Generate regimes
    regimes = np.zeros(n_points)

    # First 150 points: bullish
    regimes[:150] = 1

    # Next 200 points: bearish
    regimes[150:350] = 2

    # Last 150 points: range-bound
    regimes[350:] = 0

    # Generate price data based on regimes
    for i in range(1, n_points):
        if regimes[i] == 1:  # Bull
            drift = 0.05  # Positive drift
            vol = 1.0  # Normal volatility
        elif regimes[i] == 2:  # Bear
            drift = -0.07  # Negative drift
            vol = 1.5  # Higher volatility
        else:  # Sideways
            drift = 0.0  # No drift
            vol = 0.8  # Lower volatility

        # Random walk with drift
        price_data[i] = price_data[i - 1] * (1 + drift / 100 + vol / 100 * np.random.randn())

    # Create regime labels
    regime_labels = ["Sideways", "Bullish", "Bearish"]

    # Initialize backtester with our data and regime information
    backtester = RegimeBacktester(price_data, regimes, regime_labels)

    # Define our strategy parameters
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
    }

    # Run the backtest
    results = backtester.run_backtest(simple_rsi_strategy, default_params, regime_specific_params)

    # Print results
    print("\nBacktest Results:")
    print("-" * 50)

    for regime, result in results.items():
        metrics = result["metrics"]
        print(f"\n{regime} Regime:")
        print(f"  Total Return: {metrics['total_return']:.2%}")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"  Win Rate: {metrics['win_rate']:.2%}")

    # Plot the results
    backtester.plot_results()

    # Find best parameters for each regime
    param_grid = {
        "window": [7, 14, 21],
        "overbought": [65, 70, 75, 80],
        "oversold": [20, 25, 30, 35],
    }

    best_params = backtester.get_best_parameters_by_regime(simple_rsi_strategy, param_grid, "sharpe_ratio")

    print("\nBest Parameters by Regime:")
    print("-" * 50)
    for regime, params in best_params.items():
        print(f"\n{regime}:")
        for param, value in params.items():
            print(f"  {param}: {value}")


if __name__ == "__main__":
    # Check if matplotlib is available
    try:
        import matplotlib.pyplot as plt  # noqa: F401

        has_matplotlib = True
    except ImportError:
        has_matplotlib = False
        print("Matplotlib is not available. Install it to see the plots.")

    main()
