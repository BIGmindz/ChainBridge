#!/usr/bin/env python3
"""
Diagnostic script for the New Listings Radar module

This script tests the execute_listing_strategy method to ensure it's functioning correctly.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.new_listings_radar_module import NewListingsRadar
except ImportError:
    print("❌ Error: Could not import NewListingsRadar module.")
    print("Make sure the module exists at 'modules/new_listings_radar_module.py'")
    sys.exit(1)


async def diagnose_listing_strategy():
    """Test the execute_listing_strategy method"""
    print("🔍 Testing execute_listing_strategy method...")

    try:
        # Create module instance
        radar = NewListingsRadar()
        print("✅ Module initialized successfully")

        # Test the execute_listing_strategy method
        print("\n⏳ Executing listing strategy (this may take a moment)...")

        # Check if the method exists and is callable
        if not hasattr(radar, "execute_listing_strategy"):
            print("❌ Method 'execute_listing_strategy' does not exist")
            return

        try:
            # Call the method
            results = await radar.execute_listing_strategy()

            if results:
                print(
                    f"✅ Strategy executed successfully with {len(results)} result(s)"
                )

                # Print the results
                print("\n📊 Results:")
                for i, result in enumerate(results):
                    print(f"\nResult {i + 1}:")
                    for key, value in result.items():
                        print(f"  {key}: {value}")

                # Save results for inspection
                with open("diagnostic_listings.json", "w") as f:
                    # Convert datetime objects to strings for JSON serialization
                    results_json = []
                    for result in results:
                        result_copy = result.copy()
                        for key, value in result_copy.items():
                            if isinstance(value, datetime):
                                result_copy[key] = value.isoformat()
                        results_json.append(result_copy)  # type: ignore

                    json.dump(results_json, f, indent=4)

                print("\n💾 Results saved to diagnostic_listings.json")
            else:
                print("ℹ️ Strategy executed successfully, but no results were returned")
                print("This is normal if no new listings were detected")
        except Exception as e:
            print(f"❌ Strategy execution failed: {e}")
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")


async def main():
    """Main execution function"""
    await diagnose_listing_strategy()


if __name__ == "__main__":
    asyncio.run(main())
