#!/usr/bin/env python3
"""
Capital Allocation for New Listings

This script manages capital allocation for new cryptocurrency listings,
starting with $1000 for the first listing.
"""

import argparse
import datetime
import json
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("capital_allocation.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Initial capital allocation
INITIAL_CAPITAL = 1000.0

# Allocation settings
ALLOCATION_SETTINGS = {
    "first_listing_amount": 1000.0,
    "max_allocation_per_listing": 1000.0,
    "min_allocation_per_listing": 100.0,
    "max_risk_per_trade": 0.025,
    "confidence_tiers": {
        "0.95": 1.0,  # 95% confidence -> 100% of max allocation
        "0.90": 0.8,  # 90% confidence -> 80% of max allocation
        "0.85": 0.6,  # 85% confidence -> 60% of max allocation
        "0.80": 0.4,  # 80% confidence -> 40% of max allocation
        "0.75": 0.2,  # 75% confidence -> 20% of max allocation
    },
    "risk_level_multipliers": {"LOW": 1.0, "MEDIUM": 0.8, "HIGH": 0.5},
}

# Allocation state
ALLOCATION_STATE = {
    "total_capital": 1000.0,
    "allocated_capital": 0.0,
    "available_capital": 1000.0,
    "allocations": [],
    "last_update": datetime.datetime.now().isoformat(),
}


def load_allocation_settings():
    """Load allocation settings from file if available"""
    settings_file = "config/allocation_settings.json"

    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)

                # Update the global settings with loaded values
                ALLOCATION_SETTINGS.update(settings)

            logging.info(f"Loaded allocation settings from {settings_file}")
        except Exception as e:
            logging.error(f"Error loading allocation settings: {e}")
    else:
        # Save the default settings
        save_allocation_settings()


def save_allocation_settings():
    """Save the current allocation settings to file"""
    settings_file = "config/allocation_settings.json"

    # Ensure the config directory exists
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)

    try:
        with open(settings_file, "w") as f:
            json.dump(ALLOCATION_SETTINGS, f, indent=2)

        logging.info(f"Saved allocation settings to {settings_file}")
    except Exception as e:
        logging.error(f"Error saving allocation settings: {e}")


def load_allocation_state():
    """Load allocation state from file if available"""
    state_file = "allocation_state.json"

    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)

                # Update the global state with loaded values
                ALLOCATION_STATE.update(state)

            logging.info(f"Loaded allocation state from {state_file}")
        except Exception as e:
            logging.error(f"Error loading allocation state: {e}")
    else:
        # Save the default state
        save_allocation_state()


def save_allocation_state():
    """Save the current allocation state to file"""
    state_file = "allocation_state.json"

    try:
        # Update the timestamp
        ALLOCATION_STATE["last_update"] = datetime.datetime.now().isoformat()

        with open(state_file, "w") as f:
            json.dump(ALLOCATION_STATE, f, indent=2)

        logging.info(f"Saved allocation state to {state_file}")
    except Exception as e:
        logging.error(f"Error saving allocation state: {e}")


def calculate_allocation(listing):
    """Calculate the allocation amount for a listing"""
    # Get listing properties
    confidence = listing.get("confidence", 0)
    risk_level = listing.get("risk_level", "MEDIUM")
    _expected_return = listing.get("expected_return", 0)

    # Determine the base allocation based on confidence
    base_allocation = 0

    # Find the appropriate confidence tier
    confidence_tiers = sorted(
        [float(tier) for tier in ALLOCATION_SETTINGS["confidence_tiers"]], reverse=True
    )

    for tier in confidence_tiers:
        if confidence >= tier:
            base_allocation = ALLOCATION_SETTINGS["confidence_tiers"][str(tier)]
            break

    # Apply risk level multiplier
    risk_multiplier = ALLOCATION_SETTINGS["risk_level_multipliers"].get(risk_level, 0.5)

    # Calculate the allocation
    if len(ALLOCATION_STATE["allocations"]) == 0:
        # First listing gets special allocation
        allocation = ALLOCATION_SETTINGS["first_listing_amount"]
    else:
        # Subsequent listings use the standard calculation
        max_allocation = ALLOCATION_SETTINGS["max_allocation_per_listing"]
        allocation = max_allocation * base_allocation * risk_multiplier

    # Ensure allocation is within limits
    allocation = min(allocation, ALLOCATION_STATE["available_capital"])
    allocation = max(allocation, ALLOCATION_SETTINGS["min_allocation_per_listing"])
    allocation = min(allocation, ALLOCATION_SETTINGS["max_allocation_per_listing"])

    return allocation


def allocate_capital(listing):
    """Allocate capital for a listing"""
    if (
        ALLOCATION_STATE["available_capital"]
        < ALLOCATION_SETTINGS["min_allocation_per_listing"]
    ):
        logging.warning("Insufficient capital for allocation")
        return None

    # Calculate allocation
    amount = calculate_allocation(listing)

    if amount <= 0:
        logging.warning("Calculated allocation amount is zero")
        return None

    # Create allocation record
    allocation = {
        "id": len(ALLOCATION_STATE["allocations"]) + 1,
        "timestamp": datetime.datetime.now().isoformat(),
        "exchange": listing.get("exchange", "Unknown"),
        "coin": listing.get("coin", "Unknown"),
        "amount": amount,
        "confidence": listing.get("confidence", 0),
        "expected_return": listing.get("expected_return", 0),
        "risk_level": listing.get("risk_level", "MEDIUM"),
        "status": "allocated",
    }

    # Update allocation state
    ALLOCATION_STATE["allocated_capital"] += amount
    ALLOCATION_STATE["available_capital"] -= amount
    ALLOCATION_STATE["allocations"].append(allocation)

    # Save the updated state
    save_allocation_state()

    logging.info(
        f"Allocated ${amount:.2f} for {listing.get('coin', 'Unknown')} on {listing.get('exchange', 'Unknown')}"
    )

    return allocation


def get_active_listings():
    """Get active listings from the diagnostic data"""
    listings_file = "diagnostic_listings.json"

    if not os.path.exists(listings_file):
        logging.warning(f"Listings file {listings_file} not found")
        return []

    try:
        with open(listings_file, "r") as f:
            listings_data = json.load(f)

        return listings_data
    except Exception as e:
        logging.error(f"Error getting active listings: {e}")
        return []


def print_allocation_status():
    """Print the current allocation status"""
    print("\n" + "=" * 70)
    print(
        f"💰 CAPITAL ALLOCATION STATUS - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 70)

    print(f"\nTotal Capital: ${ALLOCATION_STATE['total_capital']:.2f}")
    print(f"Allocated: ${ALLOCATION_STATE['allocated_capital']:.2f}")
    print(f"Available: ${ALLOCATION_STATE['available_capital']:.2f}")

    if ALLOCATION_STATE["allocations"]:
        print("\n📊 ACTIVE ALLOCATIONS:")
        print("-" * 70)

        for allocation in ALLOCATION_STATE["allocations"]:
            print(
                f"[{allocation.get('id', 0)}] {allocation.get('coin', 'Unknown')} on {allocation.get('exchange', 'Unknown')}"
            )
            print(f"  Amount: ${allocation.get('amount', 0):.2f}")
            print(f"  Confidence: {allocation.get('confidence', 0) * 100:.1f}%")
            print(
                f"  Expected Return: {allocation.get('expected_return', 0) * 100:.1f}%"
            )
            print(f"  Risk Level: {allocation.get('risk_level', 'MEDIUM')}")
            print(f"  Status: {allocation.get('status', 'unknown').upper()}")
            print()
    else:
        print("\n📭 No active allocations")

    print("=" * 70 + "\n")


def allocate_first_listing():
    """Allocate capital for the first listing"""
    # Load the latest state and settings
    load_allocation_settings()
    load_allocation_state()

    # Get active listings
    listings = get_active_listings()

    if not listings:
        logging.warning("No active listings found")
        return

    # Sort listings by confidence and expected return
    sorted_listings = sorted(
        listings,
        key=lambda x: (x.get("confidence", 0), x.get("expected_return", 0)),
        reverse=True,
    )

    # Check if we already have allocations
    if ALLOCATION_STATE["allocations"]:
        # Check if we already allocated for this listing
        existing_coins = [a.get("coin") for a in ALLOCATION_STATE["allocations"]]

        for listing in sorted_listings:
            if listing.get("coin") not in existing_coins:
                # Allocate for this new listing
                allocation = allocate_capital(listing)
                if allocation:
                    break
    else:
        # Allocate for the first listing
        allocation = allocate_capital(sorted_listings[0])

    # Show the current allocation status
    print_allocation_status()


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Capital Allocation for New Listings")
    parser.add_argument(
        "--allocate", action="store_true", help="Allocate capital for the first listing"
    )
    parser.add_argument("--status", action="store_true", help="Show allocation status")
    parser.add_argument(
        "--settings", action="store_true", help="Configure allocation settings"
    )

    args = parser.parse_args()

    # Load the current state and settings
    load_allocation_settings()
    load_allocation_state()

    if args.settings:
        # Interactive configuration
        print("\n📝 Capital Allocation Settings")
        print("-" * 70)

        try:
            first_amount = input(
                f"First listing amount [{ALLOCATION_SETTINGS['first_listing_amount']}]: "
            )
            if first_amount:
                ALLOCATION_SETTINGS["first_listing_amount"] = float(first_amount)

            max_amount = input(
                f"Maximum allocation per listing [{ALLOCATION_SETTINGS['max_allocation_per_listing']}]: "
            )
            if max_amount:
                ALLOCATION_SETTINGS["max_allocation_per_listing"] = float(max_amount)

            min_amount = input(
                f"Minimum allocation per listing [{ALLOCATION_SETTINGS['min_allocation_per_listing']}]: "
            )
            if min_amount:
                ALLOCATION_SETTINGS["min_allocation_per_listing"] = float(min_amount)

            max_risk = input(
                f"Maximum risk per trade [{ALLOCATION_SETTINGS['max_risk_per_trade']}]: "
            )
            if max_risk:
                ALLOCATION_SETTINGS["max_risk_per_trade"] = float(max_risk)
        except ValueError:
            print("Invalid input, using previous value")

        # Save the updated settings
        save_allocation_settings()

        print("\n✅ Settings saved")
    elif args.status:
        # Show the current status
        print_allocation_status()
    elif args.allocate:
        # Allocate capital for the first listing
        allocate_first_listing()
    else:
        # Show help
        parser.print_help()


if __name__ == "__main__":
    main()
