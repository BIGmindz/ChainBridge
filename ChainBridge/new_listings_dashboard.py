#!/usr/bin/env python3
"""
New Listings Radar Dashboard

This script provides a visual dashboard for tracking new cryptocurrency listings
across major exchanges and monitoring trading opportunities.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the New Listings Radar module
from modules.new_listings_radar_module import NewListingsRadar

# Configure prettier plots
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (14, 8)
plt.rcParams["font.size"] = 12


class NewListingsDashboard:
    """
    Dashboard for monitoring new cryptocurrency listings and trading opportunities
    """

    def __init__(self):
        self.radar = NewListingsRadar()
        self.listing_data_file = "listing_opportunities.json"
        self.backtest_results_file = "listing_backtest_results.json"
        self.listing_data = self.load_listing_data()
        self.listings_by_exchange = {}
        self.profit_projections = self.radar.get_profit_projections()

    def load_listing_data(self):
        """Load listing data from the JSON file"""
        if os.path.exists(self.listing_data_file):
            try:
                with open(self.listing_data_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {"listings": [], "backtest_results": {}}

    def save_listing_data(self):
        """Save listing data to the JSON file"""
        with open(self.listing_data_file, "w") as f:
            json.dump(self.listing_data, f, indent=4)

    async def update_listings(self):
        """Update the listings by running the radar"""
        print("📡 Scanning for new coin listings...")
        signals = await self.radar.generate_trading_signals()

        # Add the signals to our data with timestamp
        for signal in signals:
            if "timestamp" in signal:
                if isinstance(signal["timestamp"], datetime):
                    signal["timestamp"] = signal["timestamp"].isoformat()
            else:
                signal["timestamp"] = datetime.now().isoformat()

            self.listing_data["listings"].append(signal)  # type: ignore

        # Update the listings by exchange
        self.listings_by_exchange = {}
        for listing in self.listing_data["listings"]:
            exchange = listing.get("exchange", "UNKNOWN")
            if exchange not in self.listings_by_exchange:
                self.listings_by_exchange[exchange] = []
            self.listings_by_exchange[exchange].append(listing)  # type: ignore

        # Save updated data
        self.save_listing_data()

        return signals

    def run_backtest(self, days=30):
        """Run a backtest and save the results"""
        print(f"📊 Running backtest over {days} days...")
        results = self.radar.backtest_listing_strategy(days)

        if results:
            # Add a timestamp
            results["timestamp"] = datetime.now().isoformat()

            # Save to the listing data
            self.listing_data["backtest_results"] = results
            self.save_listing_data()

        return results

    def plot_opportunities(self):
        """Plot the current listing opportunities"""
        if not self.listing_data["listings"]:
            print("No listing opportunities available. Run update first.")
            return

        # Convert listings to DataFrame for easier plotting
        listings_df = pd.DataFrame(self.listing_data["listings"])

        # Only include the most recent 20 listings
        if len(listings_df) > 20:
            listings_df = listings_df.sort_values("timestamp", ascending=False).head(20)  # type: ignore

        # Create a figure with subplots
        fig, axes = plt.subplots(2, 1, figsize=(14, 12))

        # Plot 1: Expected return by exchange
        sns.barplot(x="coin", y="expected_return", hue="exchange", data=listings_df, ax=axes[0])
        axes[0].set_title("Expected Return by Coin and Exchange")
        axes[0].set_ylabel("Expected Return")
        axes[0].set_xlabel("Coin")

        # Format as percentage
        axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))

        # Plot 2: Confidence levels
        sns.scatterplot(
            x="expected_return",
            y="confidence",
            hue="exchange",
            size="position_size",
            sizes=(50, 200),
            data=listings_df,
            ax=axes[1],
        )

        axes[1].set_title("Risk-Reward Matrix")
        axes[1].set_xlabel("Expected Return")
        axes[1].set_ylabel("Confidence")
        axes[1].grid(True)

        # Format as percentage
        axes[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

        plt.tight_layout()
        plt.savefig("new_listings_opportunities.png")
        print("📈 Opportunities chart saved to 'new_listings_opportunities.png'")

        return fig

    def plot_backtest_results(self):
        """Plot the backtest results"""
        if not self.listing_data.get("backtest_results"):
            print("No backtest results available. Run backtest first.")
            return

        results = self.listing_data["backtest_results"]

        # Create a figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: Monthly Profit Projections
        projections = []
        labels = []
        for scenario, data in self.profit_projections.items():
            projections.append(data["monthly_return"])  # type: ignore
            labels.append(scenario.replace("_", " ").title())  # type: ignore

        # Add the backtest result
        projections.append(results.get("monthly_return", 0))  # type: ignore
        labels.append("BACKTEST RESULT")  # type: ignore

        # Create bar chart
        sns.barplot(x=labels, y=projections, ax=axes[0])
        axes[0].set_title("Monthly Return Projections")
        axes[0].set_ylabel("Monthly Return")

        # Format as percentage
        axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))

        # Rotate x labels for better readability
        plt.setp(axes[0].get_xticklabels(), rotation=30, ha="right")

        # Plot 2: Return Distribution (simulated)
        # Generate simulated returns based on the backtest mean and std
        avg_return = results.get("avg_return_per_listing", 0.3)
        # Assume std is ~50% of the mean
        std_return = avg_return * 0.5

        simulated_returns = np.random.normal(avg_return, std_return, 1000)

        # Plot the distribution
        sns.histplot(simulated_returns, kde=True, ax=axes[1])
        axes[1].axvline(
            x=avg_return,
            color="r",
            linestyle="--",
            label=f"Avg Return: {avg_return:.1%}",
        )

        axes[1].set_title("Return Distribution")
        axes[1].set_xlabel("Return per Listing")
        axes[1].legend()

        # Format as percentage
        axes[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0%}"))

        plt.tight_layout()
        plt.savefig("new_listings_backtest.png")
        print("📊 Backtest results saved to 'new_listings_backtest.png'")

        return fig

    def print_listing_summary(self):
        """Print a summary of the listing opportunities"""
        listings = self.listing_data["listings"]

        if not listings:
            print("No listing opportunities found.")
            return

        # Find the most recent listings
        recent_listings = sorted(
            listings,
            key=lambda x: (datetime.fromisoformat(x["timestamp"]) if isinstance(x["timestamp"], str) else x["timestamp"]),
            reverse=True,
        )[:5]

        print("\n")
        print("=" * 80)
        print("🚀 NEW LISTING OPPORTUNITIES SUMMARY")
        print("=" * 80)

        for listing in recent_listings:
            print(f"\n💎 {listing['coin']} on {listing['exchange']}")
            print(f"   Confidence: {listing['confidence'] * 100:.0f}%")
            print(f"   Expected Return: {listing['expected_return'] * 100:.0f}%")
            print(f"   Position Size: {listing['position_size'] * 100:.1f}%")
            if "entry_strategy" in listing:
                print(
                    f"   Entry: {listing['entry_strategy']['type'] if isinstance(listing['entry_strategy'], dict) else listing['entry_strategy']}"
                )
            print(f"   Risk Level: {listing.get('risk_level', 'MEDIUM')}")
            print(f"   Timestamp: {listing['timestamp']}")

        # Print statistics by exchange
        print("\n")
        print("=" * 80)
        print("📊 EXCHANGE STATISTICS")
        print("=" * 80)

        for exchange, exchange_listings in self.listings_by_exchange.items():
            avg_return = sum(item["expected_return"] for item in exchange_listings) / len(exchange_listings)  # type: ignore
            avg_confidence = sum(item["confidence"] for item in exchange_listings) / len(exchange_listings)  # type: ignore

            print(f"\n{exchange}:")
            print(f"  Listings: {len(exchange_listings)}")
            print(f"  Avg Expected Return: {avg_return * 100:.1f}%")
            print(f"  Avg Confidence: {avg_confidence * 100:.1f}%")

    def print_backtest_summary(self):
        """Print a summary of the backtest results"""
        results = self.listing_data.get("backtest_results")

        if not results:
            print("No backtest results available.")
            return

        print("\n")
        print("=" * 80)
        print("📈 BACKTEST RESULTS")
        print("=" * 80)

        print(f"Listings per Month: {results.get('listings_per_month', 0):.1f}")
        print(f"Average Return per Listing: {results.get('avg_return_per_listing', 0) * 100:.1f}%")
        print(f"Win Rate: {results.get('win_rate', 0) * 100:.1f}%")
        print(f"Best Trade: {results.get('best_trade', 0) * 100:.1f}%")
        print(f"Worst Trade: {results.get('worst_trade', 0) * 100:.1f}%")
        print(f"Monthly Return: {results.get('monthly_return', 0) * 100:.1f}%")
        print(f"Monthly Return on $10,000: ${10000 * results.get('monthly_return', 0):.2f}")

        # Compare to projections
        print("\n")
        print("=" * 80)
        print("💰 COMPARED TO PROJECTIONS")
        print("=" * 80)

        for scenario, data in self.profit_projections.items():
            print(f"\n{scenario.replace('_', ' ').title()}:")
            print(f"  Projected Monthly Return: {data['monthly_return'] * 100:.1f}%")
            print(f"  Backtest Monthly Return: {results.get('monthly_return', 0) * 100:.1f}%")
            diff = results.get("monthly_return", 0) - data["monthly_return"]
            print(f"  Difference: {diff * 100:+.1f}%")


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="New Listings Radar Dashboard")
    parser.add_argument("--update", action="store_true", help="Update listing opportunities")
    parser.add_argument("--backtest", action="store_true", help="Run backtest")
    parser.add_argument("--days", type=int, default=30, help="Number of days for backtest")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    parser.add_argument("--summary", action="store_true", help="Print summary")

    args = parser.parse_args()

    # Create dashboard
    dashboard = NewListingsDashboard()

    # If no arguments, print help
    if not (args.update or args.backtest or args.plot or args.summary):
        parser.print_help()
        # Default to summary
        args.summary = True

    # Update listings
    if args.update:
        await dashboard.update_listings()

    # Run backtest
    if args.backtest:
        dashboard.run_backtest(args.days)

    # Generate plots
    if args.plot:
        dashboard.plot_opportunities()
        dashboard.plot_backtest_results()

    # Print summary
    if args.summary:
        dashboard.print_listing_summary()
        dashboard.print_backtest_summary()


if __name__ == "__main__":
    asyncio.run(main())
