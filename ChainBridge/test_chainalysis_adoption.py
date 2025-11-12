#!/usr/bin/env python3
"""
Test script for the Chainalysis Adoption Tracker Module

Demonstrates tracking of the Chainalysis Global Crypto Adoption Index
and generating BUY signals when adoption growth exceeds 40% YoY in any region
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # type: ignore

# Import the AdoptionTrackerModule
from modules.adoption_tracker_module import AdoptionTrackerModule


def test_adoption_tracker():
    """Test the Chainalysis Adoption Tracker Module"""

    print("\n" + "=" * 70)
    print("🌐 CHAINALYSIS ADOPTION TRACKER MODULE TEST")
    print("=" * 70)

    # Initialize the module
    tracker = AdoptionTrackerModule()

    # Process data and get signals
    result = tracker.process()

    # Print the results
    print("\n📊 ADOPTION-BASED SIGNAL")
    print("-" * 50)
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence'] * 100:.1f}%")
    print(f"Strength: {result['strength']:.2f}")
    print(f"Reasoning: {result['reasoning']}")

    # Get the raw adoption data
    adoption_data = tracker.get_adoption_data()

    # Display high growth regions (>40% YoY)
    print("\n🌐 HIGH GROWTH REGIONS (>40% YoY)")
    print("-" * 50)
    high_growth_regions = result.get("high_growth_regions", {})
    if high_growth_regions:
        for region, growth in high_growth_regions.items():
            print(f"  • {region.replace('_', ' ')}: {growth * 100:.1f}% growth")

            # List countries in this high-growth region
            if region in adoption_data.get("current_year_data", {}):
                region_data = adoption_data["current_year_data"][region]
                print("    Countries:")
                countries = []
                for country, country_data in region_data.get("countries", {}).items():
                    growth = country_data.get("yoy_change", 0)
                    countries.append((country, growth))  # type: ignore

                # Sort by growth
                countries.sort(key=lambda x: x[1], reverse=True)
                for country, growth in countries:
                    growth_indicator = "🔥" if growth > 0.4 else ""
                    print(f"      - {country}: {growth * 100:.1f}% {growth_indicator}")
    else:
        print("  • No regions with >40% growth detected")

    # Save results to file
    output_file = "chainalysis_adoption_test_results.json"
    with open(output_file, "w") as f:
        # Convert some values to JSON-serializable format
        serializable_result = result.copy()
        serializable_result["timestamp"] = str(serializable_result["timestamp"])
        json.dump(serializable_result, f, indent=2)

    print(f"\nDetailed results saved to {output_file}")

    # Generate visualization
    try:
        plt.figure(figsize=(12, 8))

        # Extract regional data for visualization
        regions = []
        growth_rates = []
        above_threshold = []

        for region, data in adoption_data.get("current_year_data", {}).items():
            regions.append(region.replace("_", " "))  # type: ignore
            growth = data.get("yoy_change", 0)
            growth_rates.append(growth * 100)  # Convert to percentage  # type: ignore
            above_threshold.append(growth > tracker.buy_threshold)  # type: ignore

        # Sort by growth rate
        sorted_indices = np.argsort(growth_rates)[::-1]
        regions = [regions[i] for i in sorted_indices]
        growth_rates = [growth_rates[i] for i in sorted_indices]
        above_threshold = [above_threshold[i] for i in sorted_indices]

        # Create bar colors based on threshold
        colors = ["#5cb85c" if above else "#6c757d" for above in above_threshold]

        # Create the bar chart
        _bars = plt.barh(regions, growth_rates, color=colors)

        # Add threshold line
        plt.axvline(
            x=tracker.buy_threshold * 100,
            color="red",
            linestyle="--",
            label=f"Buy Threshold ({tracker.buy_threshold * 100}%)",
        )

        # Add labels and title
        plt.xlabel("YoY Growth (%)")
        plt.title(
            "Chainalysis Global Crypto Adoption Index - Regional Growth Rates",
            fontsize=14,
        )
        plt.grid(axis="x", linestyle="--", alpha=0.7)

        # Add legend
        green_patch = plt.Rectangle((0, 0), 1, 1, fc="#5cb85c")
        gray_patch = plt.Rectangle((0, 0), 1, 1, fc="#6c757d")
        plt.legend(
            [
                green_patch,
                gray_patch,
                plt.Line2D([0], [0], color="red", linestyle="--"),
            ],
            ["> 40% Growth (Buy Signal)", "< 40% Growth", "Buy Threshold"],
        )

        # Add value labels to the bars
        for i, v in enumerate(growth_rates):
            plt.text(v + 1, i, f"{v:.1f}%", va="center")

        # Add signal annotation
        signal_color = "green" if result["signal"] == "BUY" else "gray"
        signal_box = dict(boxstyle="round,pad=0.5", facecolor=signal_color, alpha=0.3)
        plt.annotate(
            f"{result['signal']} Signal ({result['confidence'] * 100:.0f}% Confidence)",
            xy=(0.5, 0.97),
            xycoords="figure fraction",
            bbox=signal_box,
            ha="center",
            fontsize=12,
        )

        # Show the date range
        current_year = adoption_data.get("current_year", "2024")
        base_year = adoption_data.get("base_year", "2023")
        date_text = f"Period: {base_year} to {current_year}"
        plt.figtext(0.5, 0.01, date_text, ha="center", fontsize=10)

        plt.tight_layout()

        # Save the chart
        plt.savefig("chainalysis_adoption_growth.png")
        print("\nVisualization saved as 'chainalysis_adoption_growth.png'")

    except Exception as e:
        print(f"Error generating visualization: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_adoption_tracker()
