#!/usr/bin/env python3
"""
GLOBAL MACRO SIGNAL MODULE DEMO
Demonstrates the power of global macro data in predicting crypto price movements
"""

import json
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the GlobalMacroModule
from modules.global_macro_module import GlobalMacroModule


def run_global_macro_demo():
    """Run a demonstration of the GlobalMacroModule"""

    print("\n" + "=" * 60)
    print("🌍 GLOBAL MACRO SIGNAL MODULE DEMO")
    print("=" * 60)
    print("Demonstrating how global macro signals can predict crypto moves 30-90 days in advance\n")

    # Initialize module
    macro_module = GlobalMacroModule()

    # Process data and get signals
    result = macro_module.process({})

    # Print current signals
    print("\n📊 CURRENT GLOBAL MACRO SIGNAL")
    print("-" * 40)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence'] * 100:.1f}%")
    print(f"Strength: {result['strength']:.2f}")
    print(f"Lead Time: {result.get('lead_time_days', 'N/A')} days")
    print(f"Key Insight: {result.get('key_insight', 'N/A')}")

    # Print component breakdown
    print("\n📈 COMPONENT ANALYSIS")
    print("-" * 40)

    components = result.get("components", {})
    for name, component in components.items():
        print(f"\n  {name.upper()}: {component['weight'] * 100:.0f}% weight")
        print(f"  {'-' * (len(name) + 8)}")
        print(f"  Signal Strength: {component['data'].get('strength', 0):.2f}")
        print(f"  Confidence: {component['data'].get('confidence', 0) * 100:.1f}%")
        print(f"  Interpretation: {component['data'].get('interpretation', 'N/A')}")

    # Save results to JSON file
    result_file = "global_macro_demo_results.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\nDetailed results saved to {result_file}")

    # Generate a demo visualization
    try:
        # Create sample forecast data
        dates = pd.date_range(start=datetime.now(), periods=90, freq="D")

        # Base price with some randomness
        base_price = 30000

        # Current strength affects the trend
        trend_factor = result["strength"] * 15000

        # Generate a price path based on the signal strength
        prices = []
        for i in range(90):
            # Sigmoid curve to simulate accelerating trend
            sigmoid = 1 / (1 + np.exp(-0.1 * (i - 45)))

            # Apply trend gradually using sigmoid
            trend_component = trend_factor * sigmoid

            # Add some noise
            noise = np.random.normal(0, 500)

            # Calculate price
            price = base_price + trend_component + noise
            prices.append(price)

        # Create DataFrame
        df = pd.DataFrame({"Date": dates, "Price": prices})

        # Plot the forecast
        plt.figure(figsize=(12, 6))
        plt.plot(df["Date"], df["Price"], "b-", linewidth=2)

        # Add labels
        plt.title("BTC Price Forecast Based on Global Macro Signals", fontsize=16)
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Price (USD)", fontsize=12)
        plt.grid(True, alpha=0.3)

        # Add key insights as annotations
        insight = result.get("key_insight", "Monitoring macro conditions")
        plt.figtext(0.5, 0.01, f"Key Insight: {insight}", ha="center", fontsize=12)

        # Add signal direction
        signal_color = "green" if result["signal"] == "BUY" else ("red" if result["signal"] == "SELL" else "gray")
        signal_text = f"{result['signal']} Signal - {result['confidence'] * 100:.1f}% Confidence"
        plt.figtext(
            0.5,
            0.95,
            signal_text,
            ha="center",
            fontsize=14,
            bbox={"facecolor": signal_color, "alpha": 0.3, "pad": 5},
        )

        # Save plot
        plt.savefig("global_macro_forecast.png")
        print("\nForecast visualization saved as 'global_macro_forecast.png'")
    except Exception as e:
        print(f"Could not generate visualization: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_global_macro_demo()
