#!/usr/bin/env python3

"""
Test script for the New York Fed Global Supply Chain Pressure Index integration
"""

import os

import matplotlib.pyplot as plt
import pandas as pd


def test_gscpi_data() -> None:
    """Validate the GSCPI data format and plot it"""
    cache_file = "cache/gscpi_data.csv"

    if not os.path.exists(cache_file):
        print(f"ERROR: Cache file {cache_file} not found!")
        return

    # Load the data
    print(f"Reading GSCPI data from {cache_file}...")
    try:
        df = pd.read_csv(cache_file)  # type: ignore
        print(f"Successfully loaded data with {len(df)} rows")

        # Display column names
        print(f"Columns: {', '.join(df.columns)}")

        # Convert dates
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])  # type: ignore
            df = df.sort_values("Date")  # type: ignore

            # Display date range
            print(
                f"Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}"
            )

            # Show recent values
            print("\nMost recent GSCPI values:")
            recent = df.tail(5)
            for _, row in recent.iterrows():
                print(f"{row['Date'].strftime('%Y-%m')}: {row['GSCPI']:.2f}")

            # Get latest value
            latest = df.iloc[-1]
            print(
                f"\nLatest GSCPI value: {latest['GSCPI']:.2f} (from {latest['Date'].strftime('%Y-%m')})"
            )

            # Interpretation
            if latest["GSCPI"] > 2.0:
                print(
                    "INTERPRETATION: Severe supply chain stress - Strong inflation hedge signal"
                )
            elif latest["GSCPI"] > 1.0:
                print(
                    "INTERPRETATION: High supply chain stress - Inflation hedge signal"
                )
            elif latest["GSCPI"] > 0.5:
                print(
                    "INTERPRETATION: Moderate supply chain stress - Mild inflation hedge signal"
                )
            elif latest["GSCPI"] > -0.5:
                print("INTERPRETATION: Normal supply chain conditions - Neutral signal")
            elif latest["GSCPI"] > -1.0:
                print("INTERPRETATION: Supply chain ease - Mild deflationary signal")
            else:
                print(
                    "INTERPRETATION: Significant supply chain ease - Deflationary signal"
                )

            # Try to create a simple plot
            try:
                plt.figure(figsize=(10, 6))
                plt.plot(df["Date"], df["GSCPI"], "b-", linewidth=2)
                plt.axhline(y=0, color="k", linestyle="-", alpha=0.3)
                plt.axhline(y=1, color="r", linestyle="--", alpha=0.5)
                plt.axhline(y=-1, color="g", linestyle="--", alpha=0.5)
                plt.fill_between(
                    df["Date"],
                    df["GSCPI"],
                    0,
                    where=(df["GSCPI"] > 0),
                    color="r",
                    alpha=0.2,
                )
                plt.fill_between(
                    df["Date"],
                    df["GSCPI"],
                    0,
                    where=(df["GSCPI"] < 0),
                    color="g",
                    alpha=0.2,
                )
                plt.title("NY Fed Global Supply Chain Pressure Index (GSCPI)")
                plt.ylabel("Standard Deviations from Average")
                plt.xlabel("Date")
                plt.grid(True, alpha=0.3)
                plt.tight_layout()

                # Save the plot
                plt.savefig("cache/gscpi_plot.png")
                print("\nPlot saved to cache/gscpi_plot.png")

            except Exception as plot_error:
                print(f"Could not create plot: {plot_error}")
        else:
            print("ERROR: 'Date' column not found in data!")

    except Exception as e:
        print(f"ERROR reading GSCPI data: {e}")


if __name__ == "__main__":
    test_gscpi_data()
