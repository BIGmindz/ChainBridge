import os
import sys
import json
import time
import datetime
import threading
import logging
import psutil
import argparse
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("system_monitor.log"), logging.StreamHandler(sys.stdout)],
)


class SystemMonitor:
    """Class-based system monitor for the trading bot"""

    def __init__(self, config_path="config/config.yaml"):
        """Initialize the system monitor"""
        self.config_path = config_path
        self.components = {
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
        self.trading_metrics = {
            "active_signals": 0,
            "current_listings": [],
            "open_positions": 0,
            "available_capital": 1000.00,
            "allocated_capital": 0.00,
            "profits": 0.00,
            "last_update": None,
            "symbol": "N/A",
        }

        # Load configuration
        self.load_config()

    def load_config(self):
        """Load configuration from YAML file"""
        try:
            config = load_config(self.config_path)
            if config:
                self.trading_metrics["symbol"] = config.get("trading", {}).get("symbol", "BTC/USD")
                logging.info(f"Loaded configuration: symbol={self.trading_metrics['symbol']}")
            else:
                logging.warning("Could not load configuration, using defaults")
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    def is_process_running(self, process_pattern):
        """Check if a process matching the pattern is running"""
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if cmdline and any(process_pattern in cmd for cmd in cmdline if cmd):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def check_log_file(self, log_file, last_n_lines=10):
        """Check the last N lines of a log file"""
        try:
            if not os.path.exists(log_file):
                return ["Log file does not exist"]

            with open(log_file, "r") as f:
                lines = f.readlines()
                return lines[-last_n_lines:] if lines else ["Log file is empty"]
        except Exception as e:
            return [f"Error reading log file: {e}"]

    def update_status(self):
        """Update the status of all components"""
        logging.info("Updating system status...")

        if self.components is None or not isinstance(self.components, dict):
            logging.error(f"Components is not a valid dict: {type(self.components)}")
            return

        for component, config in self.components.items():
            if config is None:
                logging.warning(f"Configuration for component '{component}' is None. Skipping.")
                continue
            # Check if process is running
            running = self.is_process_running(config.get("process_pattern", ""))
            config["status"] = "Running" if running else "Stopped"
            config["last_check"] = datetime.datetime.now().isoformat()

            # Log the status
            logging.info(f"{component}: {config['status']}")

        # Update trading metrics from budget state file
        try:
            if os.path.exists("budget_state.json"):
                with open("budget_state.json", "r") as f:
                    budget_data = json.load(f)
                    self.trading_metrics["available_capital"] = budget_data.get(
                        "available_capital", self.trading_metrics["available_capital"]
                    )
                    self.trading_metrics["allocated_capital"] = budget_data.get(
                        "allocated_capital", self.trading_metrics["allocated_capital"]
                    )
                    self.trading_metrics["open_positions"] = len(budget_data.get("positions", []))
                    self.trading_metrics["last_update"] = datetime.datetime.now().isoformat()
        except Exception as e:
            logging.error(f"Error updating trading metrics: {e}")

        # Check for active listing signals
        try:
            if os.path.exists("diagnostic_listings.json"):
                with open("diagnostic_listings.json", "r") as f:
                    listings_data = json.load(f)
                    self.trading_metrics["active_signals"] = len(listings_data) if listings_data else 0
                    self.trading_metrics["current_listings"] = (
                        [
                            {
                                "coin": item.get("coin", "Unknown"),
                                "exchange": item.get("exchange", "Unknown"),
                                "confidence": item.get("confidence", 0) * 100,
                                "expected_return": item.get("expected_return", 0) * 100,
                            }
                            for item in listings_data
                        ]
                        if listings_data
                        else []
                    )
        except Exception as e:
            logging.error(f"Error updating listings data: {e}")

    def save_status(self):
        """Save the current status to a JSON file"""
        status_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "components": self.components,
            "trading_metrics": self.trading_metrics,
        }

        with open("system_status.json", "w") as f:
            json.dump(status_data, f, indent=2)

        logging.info("Status saved to system_status.json")

    def print_dashboard(self):
        """Print a simple text-based dashboard"""
        os.system("clear" if os.name == "posix" else "cls")

        print("\n" + "=" * 70)
        print(f"🚀 MULTIPLE-SIGNAL-DECISION-BOT MONITOR - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Components Status
        print("\n📊 COMPONENTS STATUS:")
        print("-" * 70)
        for component, config in self.components.items():
            status_color = "🟢" if config.get("status") == "Running" else "🔴"
            print(f"{status_color} {component.upper()}: {config.get('status', 'Unknown')}")

        # Trading Metrics
        print("\n💰 TRADING METRICS:")
        print("-" * 70)
        print(f"Trading Symbol: {self.trading_metrics.get('symbol', 'N/A')}")
        print(f"Available Capital: ${self.trading_metrics.get('available_capital', 0):.2f}")
        print(f"Allocated Capital: ${self.trading_metrics.get('allocated_capital', 0):.2f}")
        print(f"Open Positions: {self.trading_metrics.get('open_positions', 0)}")
        print(f"Active Signals: {self.trading_metrics.get('active_signals', 0)}")

        # Current Listings
        current_listings = self.trading_metrics.get("current_listings", [])
        if current_listings:
            print("\n🔔 CURRENT LISTINGS:")
            print("-" * 70)
            for i, listing in enumerate(current_listings[:5], 1):
                print(
                    f"{i}. {listing.get('coin', 'N/A')} on {listing.get('exchange', 'N/A')} - "
                    + f"Confidence: {listing.get('confidence', 0):.1f}% - "
                    + f"Expected Return: {listing.get('expected_return', 0):.1f}%"
                )

        print("\n" + "=" * 70)
        print(f"Last Update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")

    def monitor_loop(self, interval=10, dashboard=False):
        """Main monitoring loop"""
        logging.info(f"Monitor loop started with interval={interval}, dashboard={dashboard}")
        logging.info(f"Self components: {self.components}")
        try:
            while True:
                self.update_status()
                self.save_status()

                if dashboard:
                    self.print_dashboard()

                time.sleep(interval)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
        except Exception as e:
            logging.error(f"Error in monitor loop: {e}", exc_info=True)


def load_config(path="config/config.yaml"):
    """Load YAML configuration file"""
    if not os.path.exists(path):
        logging.error(f"Configuration file not found at {path}")
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return None


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Live System Monitor for Multiple-signal-decision-bot")
    parser.add_argument("--interval", type=int, default=10, help="Update interval in seconds")
    parser.add_argument("--dashboard", action="store_true", help="Display live dashboard")
    parser.add_argument("--restart-failed", action="store_true", help="Automatically restart failed components")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Path to configuration file")

    args = parser.parse_args()

    # Create monitor instance
    monitor = SystemMonitor(args.config)
    logging.info(f"Created monitor instance: {monitor}")
    logging.info(f"Monitor components: {monitor.components}")

    logging.info("Starting system monitor...")
    logging.info(f"Monitoring interval: {args.interval} seconds")

    try:
        # Create a thread for the monitor loop
        monitor_thread = threading.Thread(target=monitor.monitor_loop, args=(args.interval, args.dashboard), daemon=True)
        monitor_thread.start()

        # Keep the main thread alive
        while True:
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info("System monitor stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
