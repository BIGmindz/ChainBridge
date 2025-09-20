#!/usr/bin/env python3
"""
Detailed Kraken Balance Analysis
"""

import os

import ccxt
from dotenv import load_dotenv


def main():
    load_dotenv()

    exchange = ccxt.kraken(
        {
            "apiKey": os.getenv("API_KEY"),
            "secret": os.getenv("API_SECRET"),
            "enableRateLimit": True,
        }
    )

    # Load markets
    markets = exchange.load_markets()
    print(f"Loaded {len(markets)} markets from Kraken")

    # Get balance
    balance = exchange.fetch_balance()
    print("\n=== DETAILED KRAKEN BALANCE ANALYSIS ===")
    print(f"USD: ${balance.get('USD', {}).get('free', 0):.2f}")

    total_value = 0
    assets_to_check = []

    for asset, data in balance.items():
        if isinstance(data, dict) and data.get("free", 0) > 0:
            amount = data["free"]

            # Try multiple ways to get USD value
            usd_value = 0

            # Method 1: Direct USD pair
            usd_symbol = f"{asset}/USD"
            if usd_symbol in markets:
                try:
                    ticker = exchange.fetch_ticker(usd_symbol)
                    usd_value = amount * ticker["last"]
                    print(
                        f"{asset}: {amount} @ ${ticker['last']:.4f} = ${usd_value:.2f}"
                    )
                except Exception as e:
                    print(f"{asset}: {amount} - Error getting {usd_symbol}: {e}")
            else:
                # Method 2: Try USDT pair and convert
                usdt_symbol = f"{asset}/USDT"
                if usdt_symbol in markets:
                    try:
                        ticker = exchange.fetch_ticker(usdt_symbol)
                        usdt_value = amount * ticker["last"]
                        # Convert USDT to USD (assume 1:1 for simplicity)
                        usd_value = usdt_value * 0.999
                        print(
                            f"{asset}: {amount} @ ${ticker['last']:.4f} USDT = ${usd_value:.2f}"
                        )
                    except Exception as e:
                        print(f"{asset}: {amount} - Error getting {usdt_symbol}: {e}")
                else:
                    print(f"{asset}: {amount} - No direct USD/USDT pair found")

            if usd_value > 0:
                total_value += usd_value
                if usd_value >= 1.0:  # Only include meaningful amounts
                    assets_to_check.append((asset, amount, usd_value))

    print("\n=== SUMMARY ===")
    print(f"Total USD value: ${total_value:.2f}")
    print(f"Assets with >$1 value: {len(assets_to_check)}")
    for asset, amount, value in assets_to_check:
        print(f"  {asset}: ${value:.2f}")


if __name__ == "__main__":
    main()
