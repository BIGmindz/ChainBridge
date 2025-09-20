#!/usr/bin/env python3
"""
Exchange Alert System for New Listings Radar

This script sets up alerts for monitoring all supported exchanges
for new cryptocurrency listings.
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("exchange_alerts.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Exchange alert configurations
EXCHANGE_ALERTS = {
    "KRAKEN": {
        "enabled": True,
        "min_confidence": 0.75,
        "min_expected_return": 0.20,
        "max_risk_level": "HIGH",
        "notification_method": ["log", "file"],
    },
    "COINBASE": {
        "enabled": True,
        "min_confidence": 0.80,
        "min_expected_return": 0.25,
        "max_risk_level": "MEDIUM",
        "notification_method": ["log", "file"],
    },
    "BINANCE": {
        "enabled": True,
        "min_confidence": 0.75,
        "min_expected_return": 0.20,
        "max_risk_level": "HIGH",
        "notification_method": ["log", "file"],
    },
    "OKX": {
        "enabled": True,
        "min_confidence": 0.85,
        "min_expected_return": 0.30,
        "max_risk_level": "MEDIUM",
        "notification_method": ["log", "file"],
    },
    "KUCOIN": {
        "enabled": True,
        "min_confidence": 0.85,
        "min_expected_return": 0.25,
        "max_risk_level": "MEDIUM",
        "notification_method": ["log", "file"],
    },
}


def load_exchange_alerts():
    """Load exchange alert configurations from file if available"""
    config_file = "config/exchange_alerts.json"

    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                loaded_config = json.load(f)

                # Update the global configuration with loaded values
                for exchange, config in loaded_config.items():
                    if exchange in EXCHANGE_ALERTS:
                        EXCHANGE_ALERTS[exchange].update(config)

            logging.info(f"Loaded exchange alert configurations from {config_file}")
        except Exception as e:
            logging.error(f"Error loading exchange alert configurations: {e}")
    else:
        # Save the default configuration
        save_exchange_alerts()


def save_exchange_alerts():
    """Save the current exchange alert configurations to file"""
    config_file = "config/exchange_alerts.json"

    # Ensure the config directory exists
    os.makedirs(os.path.dirname(config_file), exist_ok=True)

    try:
        with open(config_file, "w") as f:
            json.dump(EXCHANGE_ALERTS, f, indent=2)

        logging.info(f"Saved exchange alert configurations to {config_file}")
    except Exception as e:
        logging.error(f"Error saving exchange alert configurations: {e}")


def check_exchange_listings():
    """Check for new listings from the diagnostic data"""
    listings_file = "diagnostic_listings.json"

    if not os.path.exists(listings_file):
        logging.warning(f"Listings file {listings_file} not found")
        return []

    try:
        with open(listings_file, "r") as f:
            listings_data = json.load(f)

        # Filter listings based on alert configurations
        filtered_listings = []

        for listing in listings_data:
            exchange = listing.get("exchange", "").upper()

            if exchange in EXCHANGE_ALERTS and EXCHANGE_ALERTS[exchange]["enabled"]:
                config = EXCHANGE_ALERTS[exchange]
                confidence = listing.get("confidence", 0)
                expected_return = listing.get("expected_return", 0)
                risk_level = listing.get("risk_level", "HIGH")

                # Check if the listing meets the alert criteria
                if (
                    confidence >= config["min_confidence"]
                    and expected_return >= config["min_expected_return"]
                    and risk_level_to_numeric(risk_level) <= risk_level_to_numeric(config["max_risk_level"])
                ):
                    filtered_listings.append(listing)

        return filtered_listings
    except Exception as e:
        logging.error(f"Error checking exchange listings: {e}")
        return []


def risk_level_to_numeric(risk_level):
    """Convert risk level to numeric value for comparison"""
    risk_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    return risk_map.get(risk_level.upper(), 3)


def generate_alerts(listings):
    """Generate alerts for the given listings"""
    if not listings:
        logging.info("No listings match the alert criteria")
        return

    alerts = []

    for listing in listings:
        exchange = listing.get("exchange", "").upper()
        coin = listing.get("coin", "Unknown")
        confidence = listing.get("confidence", 0) * 100
        expected_return = listing.get("expected_return", 0) * 100
        risk_level = listing.get("risk_level", "MEDIUM")

        alert = {
            "timestamp": datetime.datetime.now().isoformat(),
            "exchange": exchange,
            "coin": coin,
            "confidence": confidence,
            "expected_return": expected_return,
            "risk_level": risk_level,
            "message": f"🔔 ALERT: New {coin} listing on {exchange} - {confidence:.1f}% confidence, {expected_return:.1f}% expected return, {risk_level} risk",
        }

        alerts.append(alert)

        # Log the alert
        logging.info(alert["message"])

    # Save alerts to file
    save_alerts(alerts)


def save_alerts(alerts):
    """Save alerts to file"""
    alerts_file = "exchange_alerts_active.json"

    try:
        # Load existing alerts if available
        existing_alerts = []
        if os.path.exists(alerts_file):
            with open(alerts_file, "r") as f:
                existing_alerts = json.load(f)

        # Add new alerts
        updated_alerts = existing_alerts + alerts

        # Keep only the 100 most recent alerts
        updated_alerts = updated_alerts[-100:]

        with open(alerts_file, "w") as f:
            json.dump(updated_alerts, f, indent=2)

        logging.info(f"Saved {len(alerts)} alerts to {alerts_file}")
    except Exception as e:
        logging.error(f"Error saving alerts: {e}")


def print_alert_status():
    """Print the current alert status"""
    print("\n" + "=" * 70)
    print(f"🔔 EXCHANGE ALERT SYSTEM - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print("\n📊 EXCHANGE ALERT CONFIGURATIONS:")
    print("-" * 70)
    for exchange, config in EXCHANGE_ALERTS.items():
        status = "🟢 ENABLED" if config["enabled"] else "🔴 DISABLED"
        print(f"{exchange}: {status}")
        print(f"  Min Confidence: {config['min_confidence'] * 100:.1f}%")
        print(f"  Min Expected Return: {config['min_expected_return'] * 100:.1f}%")
        print(f"  Max Risk Level: {config['max_risk_level']}")

    print("\n" + "=" * 70)

    # Check for active alerts
    alerts_file = "exchange_alerts_active.json"
    if os.path.exists(alerts_file):
        try:
            with open(alerts_file, "r") as f:
                alerts = json.load(f)

            print(f"\n🚨 ACTIVE ALERTS: {len(alerts)}")
            print("-" * 70)

            # Show the 5 most recent alerts
            for alert in alerts[-5:]:
                print(f"[{alert.get('timestamp', '')}] {alert.get('message', '')}")
        except Exception as e:
            print(f"\n⚠️ Error reading alerts: {e}")
    else:
        print("\n📭 No active alerts")

    print("\n" + "=" * 70 + "\n")


def alert_loop(interval=300):
    """Main alert loop"""
    try:
        while True:
            # Load the latest configuration
            load_exchange_alerts()

            # Check for new listings
            listings = check_exchange_listings()

            # Generate alerts
            generate_alerts(listings)

            # Sleep until next check
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Alert system stopped by user")
    except Exception as e:
        logging.error(f"Error in alert loop: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Exchange Alert System for New Listings Radar")
    parser.add_argument("--interval", type=int, default=300, help="Alert check interval in seconds")
    parser.add_argument("--configure", action="store_true", help="Configure alert settings")
    parser.add_argument("--status", action="store_true", help="Show alert status")

    args = parser.parse_args()

    # Load the current configuration
    load_exchange_alerts()

    if args.configure:
        # Interactive configuration
        print("\n📝 Exchange Alert Configuration")
        print("-" * 70)

        for exchange in EXCHANGE_ALERTS:
            print(f"\nConfiguring {exchange}:")

            EXCHANGE_ALERTS[exchange]["enabled"] = input(f"Enable alerts for {exchange}? (y/n) [y]: ").lower() != "n"

            try:
                min_conf = input(f"Minimum confidence (0-100) [{EXCHANGE_ALERTS[exchange]['min_confidence'] * 100:.0f}]: ")
                if min_conf:
                    EXCHANGE_ALERTS[exchange]["min_confidence"] = float(min_conf) / 100

                min_ret = input(f"Minimum expected return (0-100) [{EXCHANGE_ALERTS[exchange]['min_expected_return'] * 100:.0f}]: ")
                if min_ret:
                    EXCHANGE_ALERTS[exchange]["min_expected_return"] = float(min_ret) / 100

                risk = input(f"Maximum risk level (LOW/MEDIUM/HIGH) [{EXCHANGE_ALERTS[exchange]['max_risk_level']}]: ").upper()
                if risk in ["LOW", "MEDIUM", "HIGH"]:
                    EXCHANGE_ALERTS[exchange]["max_risk_level"] = risk
            except ValueError:
                print("Invalid input, using previous value")

        # Save the updated configuration
        save_exchange_alerts()

        print("\n✅ Configuration saved")
    elif args.status:
        # Show the current status
        print_alert_status()
    else:
        # Start the alert loop
        logging.info("Starting exchange alert system...")
        logging.info(f"Alert check interval: {args.interval} seconds")

        alert_loop(args.interval)


if __name__ == "__main__":
    main()
