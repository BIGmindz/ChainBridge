#!/usr/bin/env python3
"""
New Listings Integration Verification Dashboard

This script verifies that the New Listings Radar module is properly integrated
with the Multiple-signal-decision-bot system and displays key statistics.
"""

import importlib
import json
import os
import sys

# Optional visualization dependencies
plt = None
sns = None
pd = None
np = None

if importlib.util.find_spec("matplotlib"):
    import matplotlib.pyplot as plt
if importlib.util.find_spec("seaborn"):
    import seaborn as sns
if importlib.util.find_spec("pandas"):
    import pandas as pd
if importlib.util.find_spec("numpy"):
    pass

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set styling
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = [14, 8]
plt.rcParams["font.size"] = 12


def check_module_integration():
    """Check if the New Listings Radar module is properly integrated"""
    integration_status = {
        "module_exists": False,
        "imported_in_bot": False,
        "initialized_in_bot": False,
        "signal_processing": False,
        "backtest_available": False,
        "run_script_available": False,
        "dashboard_available": False,
        "dependencies_installed": False,
    }

    # Check if the module exists
    if os.path.exists("modules/new_listings_radar_module.py"):
        integration_status["module_exists"] = True

    # Check if the module is imported in the main bot
    with open("multi_signal_bot.py", "r") as f:
        bot_code = f.read()
        if "from modules.new_listings_radar_module import NewListingsRadar" in bot_code:
            integration_status["imported_in_bot"] = True
        if "new_listings_radar = NewListingsRadar" in bot_code:
            integration_status["initialized_in_bot"] = True
        if 'module_signals["NewListingsRadar"]' in bot_code:
            integration_status["signal_processing"] = True

    # Check if the backtest functionality is available
    try:
        from modules.new_listings_radar_module import NewListingsRadar

        radar = NewListingsRadar()
        if hasattr(radar, "backtest_listing_strategy"):
            integration_status["backtest_available"] = True
    except Exception:
        pass

    # Check if run script is available
    if os.path.exists("run_new_listings_radar.py"):
        integration_status["run_script_available"] = True

    # Check if dashboard is available
    if os.path.exists("new_listings_dashboard.py"):
        integration_status["dashboard_available"] = True

    # Check if dependencies are installed
    try:
        if importlib.util.find_spec("bs4"):
            integration_status["dependencies_installed"] = True
    except Exception:
        pass

    return integration_status


def load_backtest_results():
    """Load backtest results if available"""
    if os.path.exists("test_listings_backtest.json"):
        with open("test_listings_backtest.json", "r") as f:
            return json.load(f)
    return None


def load_diagnostic_results():
    """Load diagnostic results if available"""
    if os.path.exists("diagnostic_listings.json"):
        with open("diagnostic_listings.json", "r") as f:
            return json.load(f)
    return None


def visualize_integration_status(status):
    """Visualize the integration status"""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Prepare data
    categories = list(status.keys())  # type: ignore
    values = [1 if status[cat] else 0 for cat in categories]

    # Format categories for display
    display_categories = [cat.replace("_", " ").title() for cat in categories]

    # Set colors
    colors = ["green" if v else "red" for v in values]

    # Create bar chart
    bars = ax.bar(display_categories, values, color=colors)

    # Add counts
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.1,
            "✅" if val else "❌",
            ha="center",
            va="bottom",
            fontsize=14,
        )

    # Set labels
    ax.set_title("New Listings Radar Integration Status", fontsize=16)
    ax.set_ylim(0, 1.2)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Not Integrated", "Integrated"])

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()

    # Save the figure
    plt.savefig("new_listings_integration_status.png")

    return fig


def visualize_backtest_performance(backtest_results):
    """Visualize backtest performance"""
    if not backtest_results:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create data for visualization
    performance_data = {
        "Metric": [
            "Total Return",
            "Average per Listing",
            "Win Rate",
            "Best Trade",
            "Worst Trade",
        ],
        "Value": [
            backtest_results.get("total_return", 0) * 100,
            backtest_results.get("avg_return", 0) * 100,
            backtest_results.get("win_rate", 0) * 100,
            backtest_results.get("max_return", 0) * 100,
            backtest_results.get("min_return", 0) * 100,
        ],
    }

    df = pd.DataFrame(performance_data)

    # Set colors
    colors = ["#2ecc71", "#3498db", "#9b59b6", "#f1c40f", "#e74c3c"]

    # Create bar chart
    bars = ax.bar(df["Metric"], df["Value"], color=colors)

    # Add labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1,
            f"{height:.1f}%",
            ha="center",
            va="bottom",
        )

    # Set labels
    ax.set_title("New Listings Radar Backtest Performance", fontsize=16)
    ax.set_ylabel("Percentage (%)")

    plt.tight_layout()

    # Save the figure
    plt.savefig("new_listings_backtest_performance.png")

    return fig


def visualize_signals(signals_data):
    """Visualize signal data"""
    if not signals_data:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    # Extract data
    coins = [signal.get("coin", "Unknown") for signal in signals_data]
    confidence = [signal.get("confidence", 0) * 100 for signal in signals_data]
    returns = [signal.get("expected_return", 0) * 100 for signal in signals_data]

    # Create DataFrame
    df = pd.DataFrame(
        {"Coin": coins, "Confidence": confidence, "Expected Return": returns}
    )

    # Create grouped bar chart
    df.plot(x="Coin", kind="bar", ax=ax)

    # Set labels
    ax.set_title("New Listings Signals", fontsize=16)
    ax.set_ylabel("Percentage (%)")

    plt.tight_layout()

    # Save the figure
    plt.savefig("new_listings_signals.png")

    return fig


def main():
    """Main execution function"""
    # Check integration status
    print("🔍 Checking New Listings Radar integration status...")
    status = check_module_integration()

    # Print status
    print("\n📊 Integration Status:")
    for key, value in status.items():
        icon = "✅" if value else "❌"
        print(f"{icon} {key.replace('_', ' ').title()}")

    # Calculate overall integration percentage
    integration_percent = (sum(1 for v in status.values() if v) / len(status)) * 100  # type: ignore
    print(f"\nOverall Integration: {integration_percent:.1f}%")

    # Load backtest results
    backtest_results = load_backtest_results()

    if backtest_results:
        print("\n📈 Backtest Results Available")
    else:
        print("\n⚠️ No backtest results found")

    # Load diagnostic results
    diagnostic_results = load_diagnostic_results()

    if diagnostic_results:
        print(f"\n🧪 Diagnostic Results: {len(diagnostic_results)} signals found")
    else:
        print("\n⚠️ No diagnostic results found")

    # Create visualizations
    print("\n🎨 Creating visualizations...")
    visualize_integration_status(status)
    if backtest_results:
        visualize_backtest_performance(backtest_results)
    if diagnostic_results:
        visualize_signals(diagnostic_results)

    print("\n✅ Integration verification complete")
    print("Check the generated images for visualization:")
    print("  • new_listings_integration_status.png")
    print("  • new_listings_backtest_performance.png")
    print("  • new_listings_signals.png")


if __name__ == "__main__":
    main()
