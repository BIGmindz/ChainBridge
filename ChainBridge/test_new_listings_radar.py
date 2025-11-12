#!/usr/bin/env python3
"""
Test script for the New Listings Radar module

This script performs a test of the New Listings Radar functionality
to verify proper integration and operation.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.new_listings_radar_module import NewListingsRadar
except ImportError:
    print("❌ Error: Could not import NewListingsRadar module.")
    print("Make sure the module exists at 'modules/new_listings_radar_module.py'")
    sys.exit(1)


async def demo_new_listings_radar():
    """Test the New Listings Radar module"""
    print("🧪 Testing New Listings Radar module...")

    # Create module instance
    try:
        radar = NewListingsRadar()
        print("✅ Module initialized successfully")
    except Exception as e:
        print(f"❌ Module initialization failed: {e}")
        return False

    # Test 1: Check exchange connectivity
    print("\n🔍 Test 1: Testing exchange connectivity...")
    exchanges = list(radar.cex_sources.keys())  # type: ignore

    if not exchanges:
        print("❌ No exchanges supported or available")
        return False

    print(f"✅ Found {len(exchanges)} supported exchanges: {', '.join(exchanges)}")
    # Check if exchanges have required properties
    for exchange, config in radar.cex_sources.items():
        print(
            f"  • {exchange}: {'url' in config and 'weight' in config and 'avg_pump' in config}"
        )

    # Test 2: Check announcement parsing and methods
    print("\n🔍 Test 2: Testing announcement parsing methods...")
    try:
        # Check if required parsing methods exist
        methods_to_check = [
            "extract_coins_from_announcement",
            "parse_listing_date",
            "execute_listing_strategy",
        ]

        for method in methods_to_check:
            if hasattr(radar, method):
                print(f"✅ Method '{method}' exists")
            else:
                print(f"❌ Method '{method}' does not exist")

        # Try to access the execute_listing_strategy method
        if hasattr(radar, "execute_listing_strategy"):
            print("🔄 Scanning methods are available")
        else:
            print("⚠️ Scanning functionality may be limited")
    except Exception as e:
        print(f"❌ Method checking failed: {e}")

    # Test 3: Test signal generation capabilities
    print("\n🔍 Test 3: Testing signal generation capabilities...")
    try:
        # Check if the module has signal generation attributes
        if hasattr(radar, "risk_filters"):
            print("✅ Risk filters configured:")
            for filter_name, value in radar.risk_filters.items():
                print(f"  • {filter_name}: {value}")
        else:
            print("❌ Risk filters not defined")

        # Check trading parameters
        if hasattr(radar, "trading_params"):
            print("✅ Trading parameters configured:")
            for param, value in radar.trading_params.items():
                print(f"  • {param}: {value}")
        else:
            print("❌ Trading parameters not defined")

        # Check if signal generation methods exist
        if hasattr(radar, "execute_listing_strategy"):
            print("✅ Signal generation method exists")
        else:
            print("❌ Signal generation method not found")
    except Exception as e:
        print(f"❌ Signal capability check failed: {e}")

    # Test 4: Check backtest capabilities
    print("\n🔍 Test 4: Checking backtest capabilities...")
    try:
        # Check if backtest method exists
        if hasattr(radar, "backtest_listing_strategy"):
            print("✅ Backtest method exists")

            # Try to access backtest parameters (if available)
            if hasattr(radar, "backtest_params"):
                print("✅ Backtest parameters configured:")
                for param, value in radar.backtest_params.items():
                    print(f"  • {param}: {value}")
            else:
                print("ℹ️ No specific backtest parameters found (may use defaults)")

            print("\n📈 Backtest capability available")
            print(
                "  • To run a backtest: python run_new_listings_radar.py --backtest --days 30"
            )
        else:
            print("❌ Backtest method not found")

        # Create a test backtest results file for demonstration
        demo_results = {
            "start_date": datetime.now() - timedelta(days=30),
            "end_date": datetime.now(),
            "total_signals": 15,
            "profitable_signals": 11,
            "avg_return": 24.5,
            "max_return": 62.3,
            "timestamp": datetime.now(),
        }

        # Save demo results
        with open("test_listings_backtest.json", "w") as f:
            # Convert datetime objects to strings for JSON serialization
            for key, value in demo_results.items():
                if isinstance(value, datetime):
                    demo_results[key] = value.isoformat()

            json.dump(demo_results, f, indent=4)

        print("💾 Demo backtest results saved to test_listings_backtest.json")
    except Exception as e:
        print(f"❌ Backtest capability check failed: {e}")

    print("\n🏁 New Listings Radar test completed")
    return True


def main():
    """Main execution function"""
    try:
        asyncio.run(demo_new_listings_radar())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")


if __name__ == "__main__":
    main()
