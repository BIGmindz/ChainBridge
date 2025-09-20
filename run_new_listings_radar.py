#!/usr/bin/env python3
"""
Run New Listings Radar

This script allows you to run the New Listings Radar independently to monitor
new coin listings across major exchanges and generate trading signals.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.new_listings_radar import ListingsMonitor

# Import the New Listings Radar module
from modules.new_listings_radar_module import NewListingsRadar


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="New Listings Radar")
    parser.add_argument("--scan", action="store_true", help="Scan for new listings")
    parser.add_argument("--backtest", action="store_true", help="Run backtest")
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days for backtest"
    )
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument(
        "--output",
        type=str,
        default="new_listings_signals.json",
        help="Output file for results",
    )

    args = parser.parse_args()

    # Create New Listings Radar
    radar = NewListingsRadar()

    # Scan for new listings
    if args.scan:
        print("📡 Scanning exchanges for new listings...")
        signals = await radar.execute_listing_strategy()

        if args.save and signals:
            # Convert datetime objects to ISO strings for JSON serialization
            for signal in signals:
                if "timestamp" in signal and isinstance(signal["timestamp"], datetime):
                    signal["timestamp"] = signal["timestamp"].isoformat()

            # Save signals to file
            with open(args.output, "w") as f:
                json.dump(signals, f, indent=4)
            print(f"💾 Signals saved to {args.output}")

    # Run backtest
    if args.backtest:
        print(f"📊 Running backtest over {args.days} days...")
        results = radar.backtest_listing_strategy(args.days)

        if args.save and results:
            # Add a timestamp
            results["timestamp"] = datetime.now().isoformat()

            # Save results to file
            backtest_file = "new_listings_backtest.json"
            with open(backtest_file, "w") as f:
                json.dump(results, f, indent=4)
            print(f"💾 Backtest results saved to {backtest_file}")

    # If no arguments provided, run full radar
    if not (args.scan or args.backtest):
        # Use the new ListingsMonitor class
        monitor = ListingsMonitor()
        monitor.scan_exchanges()


if __name__ == "__main__":
    asyncio.run(main())
