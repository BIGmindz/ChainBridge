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
import sys
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Dict, List

# Configure logging
LOG_FILE = Path("exchange_alerts.log")
CONFIG_FILE = Path("config/exchange_alerts.json")
ALERTS_FILE = Path("exchange_alerts_active.json")
LISTINGS_FILE = Path("diagnostic_listings.json")


for directory in {LOG_FILE.parent, CONFIG_FILE.parent, ALERTS_FILE.parent, LISTINGS_FILE.parent}:
    directory.mkdir(parents=True, exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)


ALLOWED_NOTIFICATIONS = {"log", "file"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}


@dataclass
class ExchangeAlertConfig:
    """Represents alert criteria and delivery preferences for an exchange."""

    enabled: bool = True
    min_confidence: float = 0.75
    min_expected_return: float = 0.20
    max_risk_level: str = "HIGH"
    notification_method: List[str] = field(default_factory=lambda: ["log", "file"])

    def validate(self) -> None:
        """Validate the configuration values."""

        if not isinstance(self.enabled, bool):
            raise ValueError("'enabled' must be a boolean")

        if not (0 <= self.min_confidence <= 1):
            raise ValueError("'min_confidence' must be between 0 and 1")

        if not (0 <= self.min_expected_return <= 1):
            raise ValueError("'min_expected_return' must be between 0 and 1")

        max_risk = self.max_risk_level.upper()
        if max_risk not in RISK_LEVELS:
            raise ValueError(f"'max_risk_level' must be one of {sorted(RISK_LEVELS)}")
        self.max_risk_level = max_risk

        if isinstance(self.notification_method, str) or not isinstance(self.notification_method, Iterable):
            raise ValueError("'notification_method' must be an iterable of strings")

        notifications = []
        for method in self.notification_method:
            if not isinstance(method, str):
                raise ValueError("notification methods must be strings")
            method_normalized = method.lower()
            if method_normalized not in ALLOWED_NOTIFICATIONS:
                error_message = f"Unsupported notification method '{method}'. Allowed methods: {sorted(ALLOWED_NOTIFICATIONS)}"
                raise ValueError(error_message)
            notifications.append(method_normalized)

        # Store normalized versions to keep configuration consistent
        self.notification_method = notifications

    def to_dict(self) -> Dict[str, object]:
        """Serialize configuration into a JSON-compatible dictionary."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ExchangeAlertConfig":
        """Create a configuration instance from an arbitrary mapping."""

        allowed_keys = {field_def.name for field_def in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed_keys}

        candidate = cls(**filtered)
        candidate.validate()
        return candidate


DEFAULT_EXCHANGE_CONFIGS: Dict[str, ExchangeAlertConfig] = {
    "KRAKEN": ExchangeAlertConfig(),
}

EXCHANGE_ALERTS: Dict[str, ExchangeAlertConfig] = {}


def clone_config(config: ExchangeAlertConfig) -> ExchangeAlertConfig:
    """Create a defensive copy of an exchange configuration."""

    return ExchangeAlertConfig.from_dict(config.to_dict())


def load_exchange_alerts():
    """Load exchange alert configurations from file if available."""

    EXCHANGE_ALERTS.clear()

    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                loaded_config = json.load(f)

            for exchange, config in loaded_config.items():
                exchange_key = exchange.upper()
                try:
                    EXCHANGE_ALERTS[exchange_key] = ExchangeAlertConfig.from_dict(config)
                except Exception as e:
                    logging.error("Invalid configuration for %s skipped: %s", exchange_key, e)

            logging.info("Loaded exchange alert configurations from %s", CONFIG_FILE)
        except Exception as e:
            logging.error("Error loading exchange alert configurations: %s", e)

    # Ensure that required default exchanges always exist
    for exchange, config in DEFAULT_EXCHANGE_CONFIGS.items():
        EXCHANGE_ALERTS.setdefault(exchange, clone_config(config))

    if not CONFIG_FILE.exists():
        # Persist defaults so users can edit or extend easily
        save_exchange_alerts()


def save_exchange_alerts():
    """Save the current exchange alert configurations to file."""

    # Ensure the config directory exists
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            serialized = {exchange: config.to_dict() for exchange, config in EXCHANGE_ALERTS.items()}
            json.dump(serialized, f, indent=2)

        logging.info("Saved exchange alert configurations to %s", CONFIG_FILE)
    except Exception as e:
        logging.error("Error saving exchange alert configurations: %s", e)


def check_exchange_listings():
    """Check for new listings from the diagnostic data"""
    if not LISTINGS_FILE.exists():
        logging.warning("Listings file %s not found", LISTINGS_FILE)
        return []

    try:
        with LISTINGS_FILE.open("r", encoding="utf-8") as f:
            listings_data = json.load(f)

        # Filter listings based on alert configurations
        filtered_listings = []

        for listing in listings_data:
            exchange = listing.get("exchange", "").upper()

            config = EXCHANGE_ALERTS.get(exchange)
            if config and config.enabled:
                confidence = listing.get("confidence", 0)
                expected_return = listing.get("expected_return", 0)
                risk_level = listing.get("risk_level", "HIGH")

                # Check if the listing meets the alert criteria
                if (
                    confidence >= config.min_confidence
                    and expected_return >= config.min_expected_return
                    and risk_level_to_numeric(risk_level) <= risk_level_to_numeric(config.max_risk_level)
                ):
                    filtered_listings.append(listing)

        return filtered_listings
    except Exception as e:
        logging.error("Error checking exchange listings: %s", e)
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

        message = (
            f"🔔 ALERT: New {coin} listing on {exchange} - "
            f"{confidence:.1f}% confidence, {expected_return:.1f}% expected return, "
            f"{risk_level} risk"
        )

        alert = {
            "timestamp": datetime.datetime.now().isoformat(),
            "exchange": exchange,
            "coin": coin,
            "confidence": confidence,
            "expected_return": expected_return,
            "risk_level": risk_level,
            "message": message,
        }

        alerts.append(alert)

        # Log the alert
        logging.info(message)

    # Save alerts to file
    save_alerts(alerts)


def save_alerts(alerts):
    """Save alerts to file"""

    try:
        # Load existing alerts if available
        existing_alerts = []
        if ALERTS_FILE.exists():
            with ALERTS_FILE.open("r", encoding="utf-8") as f:
                existing_alerts = json.load(f)

        # Add new alerts
        updated_alerts = existing_alerts + alerts

        # Keep only the 100 most recent alerts
        updated_alerts = updated_alerts[-100:]

        ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with ALERTS_FILE.open("w", encoding="utf-8") as f:
            json.dump(updated_alerts, f, indent=2)

        logging.info("Saved %s alerts to %s", len(alerts), ALERTS_FILE)
    except Exception as e:
        logging.error("Error saving alerts: %s", e)


def print_alert_status():
    """Print the current alert status"""
    print("\n" + "=" * 70)
    print(f"🔔 EXCHANGE ALERT SYSTEM - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print("\n📊 EXCHANGE ALERT CONFIGURATIONS:")
    print("-" * 70)
    for exchange in sorted(EXCHANGE_ALERTS):
        config = EXCHANGE_ALERTS[exchange]
        status = "🟢 ENABLED" if config.enabled else "🔴 DISABLED"
        print(f"{exchange}: {status}")
        print(f"  Min Confidence: {config.min_confidence * 100:.1f}%")
        print(f"  Min Expected Return: {config.min_expected_return * 100:.1f}%")
        print(f"  Max Risk Level: {config.max_risk_level}")

    print("\n" + "=" * 70)

    # Check for active alerts
    if ALERTS_FILE.exists():
        try:
            with ALERTS_FILE.open("r", encoding="utf-8") as f:
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
        logging.error("Error in alert loop: %s", e)


def prompt_for_config(exchange: str, existing: ExchangeAlertConfig) -> ExchangeAlertConfig:
    """Interactively prompt the user to update or create a configuration."""

    print(f"\nConfiguring {exchange}:")
    enabled_input = input(f"Enable alerts for {exchange}? (y/n) [{'y' if existing.enabled else 'n'}]: ").strip().lower()
    enabled = existing.enabled if enabled_input not in {"y", "n"} else enabled_input == "y"

    def prompt_float(prompt_text: str, current: float) -> float:
        raw = input(prompt_text).strip()
        if not raw:
            return current
        try:
            value_raw = float(raw)
            value = value_raw / 100 if value_raw >= 1 else value_raw
        except ValueError as exc:
            print(f"Invalid number '{raw}', keeping previous value.")
            logging.warning("Invalid numeric input for %s: %s", exchange, exc)
            return current
        if not 0 <= value <= 1:
            print("Value must be between 0 and 100.")
            return current
        return value

    min_conf = prompt_float(
        f"Minimum confidence (0-100) [{existing.min_confidence * 100:.0f}]: ",
        existing.min_confidence,
    )
    min_ret = prompt_float(
        f"Minimum expected return (0-100) [{existing.min_expected_return * 100:.0f}]: ",
        existing.min_expected_return,
    )

    risk = input(f"Maximum risk level (LOW/MEDIUM/HIGH) [{existing.max_risk_level}]: ").strip().upper()
    max_risk = existing.max_risk_level if risk not in RISK_LEVELS else risk

    methods = input(
        f"Notification methods (comma separated: {', '.join(sorted(ALLOWED_NOTIFICATIONS))}) [{', '.join(existing.notification_method)}]: "
    ).strip()
    if methods:
        notification_method = [m.strip().lower() for m in methods.split(",") if m.strip()]
    else:
        notification_method = existing.notification_method

    updated = ExchangeAlertConfig(
        enabled=enabled,
        min_confidence=min_conf,
        min_expected_return=min_ret,
        max_risk_level=max_risk,
        notification_method=notification_method,
    )
    try:
        updated.validate()
    except ValueError as exc:
        print(f"Invalid configuration: {exc}. Keeping previous settings.")
        logging.error("Invalid configuration for %s: %s", exchange, exc)
        return existing

    return updated


def add_exchange(exchange: str) -> None:
    """Add a new exchange to the configuration interactively."""

    exchange_key = exchange.upper()
    if exchange_key in EXCHANGE_ALERTS:
        print(f"{exchange_key} already exists. Use --configure to update it.")
        return

    print(f"\n➕ Adding exchange {exchange_key}")
    base_config = clone_config(DEFAULT_EXCHANGE_CONFIGS["KRAKEN"])
    EXCHANGE_ALERTS[exchange_key] = prompt_for_config(exchange_key, base_config)
    save_exchange_alerts()
    print(f"✅ Added {exchange_key} to the alert configuration.")


def remove_exchange(exchange: str) -> None:
    """Remove an exchange from the configuration if it is not mandatory."""

    exchange_key = exchange.upper()
    if exchange_key in DEFAULT_EXCHANGE_CONFIGS:
        print(f"Cannot remove mandatory exchange {exchange_key}.")
        return

    if EXCHANGE_ALERTS.pop(exchange_key, None):
        save_exchange_alerts()
        print(f"🗑️ Removed {exchange_key} from the alert configuration.")
    else:
        print(f"Exchange {exchange_key} was not configured.")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Exchange Alert System for New Listings Radar")
    parser.add_argument("--interval", type=int, default=300, help="Alert check interval in seconds")
    parser.add_argument("--configure", action="store_true", help="Configure alert settings")
    parser.add_argument("--status", action="store_true", help="Show alert status")
    parser.add_argument("--add-exchange", metavar="EXCHANGE", help="Add a new exchange configuration")
    parser.add_argument("--remove-exchange", metavar="EXCHANGE", help="Remove an exchange configuration")

    args = parser.parse_args()

    # Load the current configuration
    load_exchange_alerts()

    if args.add_exchange:
        add_exchange(args.add_exchange)
    elif args.remove_exchange:
        remove_exchange(args.remove_exchange)
    elif args.configure:
        # Interactive configuration
        print("\n📝 Exchange Alert Configuration")
        print("-" * 70)

        for exchange in sorted(EXCHANGE_ALERTS):
            EXCHANGE_ALERTS[exchange] = prompt_for_config(exchange, EXCHANGE_ALERTS[exchange])

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
