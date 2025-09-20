#!/usr/bin/env python3
"""
Live System Monitor for Multiple-signal-decision-bot

This script provides real-time monitoring of the trading system,
including New Listings Radar and Multi-Signal Bot components.
"""

import argparse
import datetime
import json
import logging
import os
import sys
import threading
import time

import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("system_monitor.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Define the components to monitor
COMPONENTS = {
    "new_listings_radar": {
        "process_pattern": "run_new_listings_radar.py",
        "log_file": "new_listings_radar.log",
        "status": "Unknown",
        "last_check": None,
    },
    "multi_signal_bot": {
        "process_pattern": "multi_signal_bot.py",
        "log_file": "multi_signal_bot.log",
        "status": "Unknown",
        "last_check": None,
    },
}

# Trading metrics
TRADING_METRICS = {
    "active_signals": 0,
    "current_listings": [],
    "open_positions": 0,
    "available_capital": 1000.00,
    "allocated_capital": 0.00,
    "profits": 0.00,
    "last_update": None,
}


def is_process_running(process_pattern):
    """Check if a process matching the pattern is running"""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if any(process_pattern in cmd for cmd in proc.info["cmdline"] if cmd):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def check_log_file(log_file, last_n_lines=10):
    """Check the last N lines of a log file"""
    try:
        if not os.path.exists(log_file):
            return ["Log file does not exist"]

        with open(log_file, "r") as f:
            lines = f.readlines()
            return lines[-last_n_lines:] if lines else ["Log file is empty"]
    except Exception as e:
        return [f"Error reading log file: {e}"]


def update_status():
    """Update the status of all components"""
    logging.info("Updating system status...")

    for component, config in COMPONENTS.items():
        # Check if process is running
        running = is_process_running(config["process_pattern"])
        config["status"] = "Running" if running else "Stopped"
        config["last_check"] = datetime.datetime.now().isoformat()

        # Log the status
        logging.info(f"{component}: {config['status']}")

    # Update trading metrics from budget state file
    try:
        if os.path.exists("budget_state.json"):
            with open("budget_state.json", "r") as f:
                budget_data = json.load(f)
                TRADING_METRICS["available_capital"] = budget_data.get(
                    "available_capital", TRADING_METRICS["available_capital"]
                )
                TRADING_METRICS["allocated_capital"] = budget_data.get(
                    "allocated_capital", TRADING_METRICS["allocated_capital"]
                )
                TRADING_METRICS["open_positions"] = len(
                    budget_data.get("positions", [])
                )
                TRADING_METRICS["last_update"] = datetime.datetime.now().isoformat()
    except Exception as e:
        logging.error(f"Error updating trading metrics: {e}")

    # Check for active listing signals
    try:
        if os.path.exists("diagnostic_listings.json"):
            with open("diagnostic_listings.json", "r") as f:
                listings_data = json.load(f)
                TRADING_METRICS["active_signals"] = len(listings_data)
                TRADING_METRICS["current_listings"] = [
                    {
                        "coin": item.get("coin", "Unknown"),
                        "exchange": item.get("exchange", "Unknown"),
                        "confidence": item.get("confidence", 0) * 100,
                        "expected_return": item.get("expected_return", 0) * 100,
                    }
                    for item in listings_data
                ]
    except Exception as e:
        logging.error(f"Error updating listings data: {e}")


def save_status():
    """Save the current status to a JSON file"""
    status_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "components": COMPONENTS,
        "trading_metrics": TRADING_METRICS,
    }

    with open("system_status.json", "w") as f:
        json.dump(status_data, f, indent=2)

    logging.info("Status saved to system_status.json")


def print_dashboard():
    """Print a simple text-based dashboard"""
    os.system("clear" if os.name == "posix" else "cls")

    print("\n" + "=" * 70)
    print(
        f"🚀 MULTIPLE-SIGNAL-DECISION-BOT MONITOR - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 70)

    # Components Status
    print("\n📊 COMPONENTS STATUS:")
    print("-" * 70)
    for component, config in COMPONENTS.items():
        status_color = "🟢" if config["status"] == "Running" else "🔴"
        print(f"{status_color} {component.upper()}: {config['status']}")

    # Trading Metrics
    print("\n💰 TRADING METRICS:")
    print("-" * 70)
    print(f"Available Capital: ${TRADING_METRICS['available_capital']:.2f}")
    print(f"Allocated Capital: ${TRADING_METRICS['allocated_capital']:.2f}")
    print(f"Open Positions: {TRADING_METRICS['open_positions']}")
    print(f"Active Signals: {TRADING_METRICS['active_signals']}")

    # Current Listings
    if TRADING_METRICS["current_listings"]:
        print("\n🔔 CURRENT LISTINGS:")
        print("-" * 70)
        for i, listing in enumerate(TRADING_METRICS["current_listings"][:5], 1):
            print(
                f"{i}. {listing['coin']} on {listing['exchange']} - "
                + f"Confidence: {listing['confidence']:.1f}% - "
                + f"Expected Return: {listing['expected_return']:.1f}%"
            )

    print("\n" + "=" * 70)
    print(f"Last Update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")


def monitor_loop(interval=60, dashboard=False):
    """Main monitoring loop"""
    try:
        while True:
            update_status()
            save_status()

            if dashboard:
                print_dashboard()

            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user")
    except Exception as e:
        logging.error(f"Error in monitor loop: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Live System Monitor for Multiple-signal-decision-bot"
    )
    parser.add_argument(
        "--interval", type=int, default=60, help="Update interval in seconds"
    )
    parser.add_argument(
        "--dashboard", action="store_true", help="Display live dashboard"
    )
    parser.add_argument(
        "--restart-failed",
        action="store_true",
        help="Automatically restart failed components",
    )

    args = parser.parse_args()

    logging.info("Starting system monitor...")
    logging.info(f"Monitoring interval: {args.interval} seconds")

    try:
        # Create a thread for the monitor loop
        monitor_thread = threading.Thread(
            target=monitor_loop, args=(args.interval, args.dashboard), daemon=True
        )
        monitor_thread.start()

        # Keep the main thread alive
        while True:
            if args.restart_failed:
                # Check for failed components and restart them
                for component, config in COMPONENTS.items():
                    if config["status"] == "Stopped":
                        if component == "new_listings_radar":
                            logging.info("Attempting to restart New Listings Radar...")
                            os.system(
                                "python3 run_new_listings_radar.py --scan > new_listings_radar.log 2>&1 &"
                            )
                        elif component == "multi_signal_bot":
                            logging.info("Attempting to restart Multi Signal Bot...")
                            os.system(
                                "python3 multi_signal_bot.py > multi_signal_bot.log 2>&1 &"
                            )

            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info("System monitor stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
