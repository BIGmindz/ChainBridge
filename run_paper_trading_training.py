#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Paper Trading Data Collection Script (Simplified)

This script runs a 30-minute paper trading simulation to collect data
for later training of the adaptive weight model.
This version focuses only on data collection without TensorFlow dependencies.
"""

import argparse
import datetime
import json
import os
import time

import pandas as pd

from modules.adaptive_weight_module.signal_data_collector import SignalDataCollector

# Import bot components
from MultiSignalBot import MultiSignalBot

# Constants
DATA_COLLECTION_INTERVAL = 30  # seconds
TRAINING_DURATION = 30 * 60  # 30 minutes in seconds
RESULTS_DIR = "data/paper_trading_results"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run paper trading simulation for ML model training")
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration of paper trading simulation in minutes (default: 30)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Data collection interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTC/USD",
        help="Trading symbol (default: BTC/USD)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualizations after training",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to main configuration file",
    )
    parser.add_argument(
        "--adaptive-config",
        type=str,
        default="config/adaptive_weight_config.yaml",
        help="Path to adaptive weight model configuration file",
    )
    return parser.parse_args()


def setup_directories():
    """Set up necessary directories for data collection."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(RESULTS_DIR, f"training_session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)

    # Create subdirectories
    os.makedirs(os.path.join(session_dir, "signal_data"), exist_ok=True)
    os.makedirs(os.path.join(session_dir, "market_data"), exist_ok=True)
    os.makedirs(os.path.join(session_dir, "performance"), exist_ok=True)
    os.makedirs(os.path.join(session_dir, "model"), exist_ok=True)
    os.makedirs(os.path.join(session_dir, "visualizations"), exist_ok=True)

    return session_dir


def run_paper_trading_simulation(args, session_dir):
    """Run paper trading simulation and collect data."""
    print(f"Starting paper trading simulation for {args.duration} minutes...")
    print(f"Data will be collected every {args.interval} seconds")
    print(f"Results will be saved to {session_dir}")

    # Initialize components
    _bot = MultiSignalBot(config_path=args.config, paper_mode=True)
    _signal_collector = SignalDataCollector()

    # Prepare data collection
    start_time = time.time()
    end_time = start_time + (args.duration * 60)
    collection_times = []
    signal_data_snapshots = []
    market_condition_snapshots = []
    performance_snapshots = []

    # Run simulation
    print("\nPaper trading simulation in progress...")
    print("Press Ctrl+C to stop early\n")

    try:
        while time.time() < end_time:
            current_time = time.time()
            timestamp = datetime.datetime.now().isoformat()

            # Run one cycle of the trading bot
            print(f"[{timestamp}] Running trading cycle...")
            _bot_result = _bot.run_once(timestamp=timestamp)

            # Collect signal data
            print("Collecting signal data...")
            # Get signal data from bot's last signals
            raw_signals = _bot.last_signals
            signal_data = _signal_collector.collect_signals(raw_signals)
            signal_data_snapshots.append({"timestamp": timestamp, "data": signal_data})

            # Collect market data without using the classifier
            print("Collecting market data...")
            market_data = _bot.get_latest_market_data()

            # Simple market condition assessment without ML clustering
            simple_condition = "UNKNOWN"
            if market_data and "price_change_24h_pct" in market_data:
                pct_change = market_data["price_change_24h_pct"]
                volatility = market_data.get("volatility_24h", 0)

                if pct_change > 5:
                    simple_condition = "BULL"
                elif pct_change < -5:
                    simple_condition = "BEAR"
                elif volatility > 3:
                    simple_condition = "VOLATILE"
                else:
                    simple_condition = "SIDEWAYS"

            market_condition_snapshots.append(
                {
                    "timestamp": timestamp,
                    "condition": simple_condition,
                    "raw_data": market_data,
                }
            )

            # Record performance metrics
            print("Recording performance metrics...")
            # Use get_portfolio_status instead of get_performance_metrics
            performance = _bot.budget_manager.get_portfolio_status()
            performance_snapshots.append({"timestamp": timestamp, "metrics": performance})

            # Save interim data
            if len(signal_data_snapshots) % 10 == 0:
                save_collected_data(
                    session_dir,
                    signal_data_snapshots,
                    market_condition_snapshots,
                    performance_snapshots,
                )

            # Wait for next collection interval
            collection_times.append(current_time)
            elapsed = time.time() - current_time
            wait_time = max(0, args.interval - elapsed)

            remaining = int(end_time - time.time())
            mins = remaining // 60
            secs = remaining % 60
            print(f"Waiting {wait_time:.1f}s before next collection. Remaining time: {mins}m {secs}s")

            if wait_time > 0:
                time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\nPaper trading simulation stopped manually")

    # Save final collected data
    save_collected_data(
        session_dir,
        signal_data_snapshots,
        market_condition_snapshots,
        performance_snapshots,
    )

    print(f"\nPaper trading simulation completed. Data saved to {session_dir}")
    return signal_data_snapshots, market_condition_snapshots, performance_snapshots


def save_collected_data(session_dir, signal_data, market_condition, performance):
    """Save collected data to files."""
    # Save signal data
    with open(os.path.join(session_dir, "signal_data", "signal_snapshots.json"), "w") as f:
        json.dump(signal_data, f, indent=2)

    # Save market condition data
    with open(os.path.join(session_dir, "market_data", "market_conditions.json"), "w") as f:
        json.dump(market_condition, f, indent=2)

    # Save performance data
    with open(os.path.join(session_dir, "performance", "performance_metrics.json"), "w") as f:
        json.dump(performance, f, indent=2)


def prepare_data_for_later_training(session_dir):
    """Prepare data for later training (without TensorFlow dependency)."""
    print("\nPreparing data for later model training...")

    # Load collected data
    with open(os.path.join(session_dir, "signal_data", "signal_snapshots.json"), "r") as f:
        signal_data = json.load(f)

    with open(os.path.join(session_dir, "market_data", "market_conditions.json"), "r") as f:
        market_condition = json.load(f)

    with open(os.path.join(session_dir, "performance", "performance_metrics.json"), "r") as f:
        performance = json.load(f)

    # Generate a summary of the data
    summary = {
        "collection_timestamp": datetime.datetime.now().isoformat(),
        "signal_data_count": len(signal_data),
        "market_conditions_count": len(market_condition),
        "performance_metrics_count": len(performance),
        "symbols_covered": list(set(snapshot.get("data", {}).get("symbol", "unknown") for snapshot in signal_data if "data" in snapshot)),
        "market_regimes_detected": list(
            set(snapshot.get("condition", "unknown") for snapshot in market_condition if "condition" in snapshot)
        ),
    }

    # Save summary
    with open(os.path.join(session_dir, "data_collection_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Data prepared for later training. Summary saved to {session_dir}/data_collection_summary.json")
    return summary


def generate_basic_visualizations(session_dir):
    """Generate basic visualizations of the collected data."""
    print("\nGenerating basic visualizations...")

    # Load data for visualization
    with open(os.path.join(session_dir, "market_data", "market_conditions.json"), "r") as f:
        market_condition = json.load(f)

    with open(os.path.join(session_dir, "performance", "performance_metrics.json"), "r") as f:
        performance = json.load(f)

    # Create visualizations directory
    viz_dir = os.path.join(session_dir, "visualizations")
    os.makedirs(viz_dir, exist_ok=True)

    # Simple market regime count visualization using pandas
    try:
        # Extract market regimes
        regimes = [entry.get("condition", "unknown") for entry in market_condition if "condition" in entry]

        # Count regimes
        regime_counts = pd.Series(regimes).value_counts()

        # Save as CSV
        regime_counts.to_csv(os.path.join(viz_dir, "market_regime_counts.csv"))

        print(f"Basic visualizations (CSV data) saved to {viz_dir}")
    except Exception as e:
        print(f"Warning: Could not generate visualizations: {e}")

    # Save raw data in a more analysis-friendly format
    with open(os.path.join(viz_dir, "data_collection_results.json"), "w") as f:
        json.dump(
            {
                "collection_time": datetime.datetime.now().isoformat(),
                "market_regimes_detected": list(
                    set(snapshot.get("condition", "unknown") for snapshot in market_condition if "condition" in snapshot)
                ),
                "market_regime_counts": ({regime: regimes.count(regime) for regime in set(regimes)} if "regimes" in locals() else {}),
                "data_points_collected": len(market_condition),
            },
            f,
            indent=2,
        )


def main():
    """Main function."""
    args = parse_args()

    # Set up directories
    session_dir = setup_directories()

    # Run paper trading simulation
    signal_data, market_condition, performance = run_paper_trading_simulation(args, session_dir)

    # Prepare data for later training
    summary = prepare_data_for_later_training(session_dir)

    # Generate basic visualizations if requested
    if args.visualize:
        generate_basic_visualizations(session_dir)

    print("\nPaper trading and data collection completed successfully!")
    print(f"Collected {summary.get('signal_data_count', 0)} signal data points")
    print(f"Detected market regimes: {', '.join(summary.get('market_regimes_detected', ['unknown']))}")
    print(f"All data saved to: {session_dir}")
    print("\nTo train the adaptive weight model with this data, run:")
    print(f"python modules/adaptive_weight_module/weight_trainer.py --data-dir {session_dir}")


if __name__ == "__main__":
    main()
