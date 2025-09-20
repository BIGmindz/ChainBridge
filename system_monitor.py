#!/usr/bin/env python3
"""
System Monitor for Multiple-signal-decision-bot
Monitors all system components and ensures they are running correctly
Provides real-time dashboard of trading performance
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import List

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


class SystemMonitor:
    """System monitoring for trading bot components"""

    def __init__(self, interval: int = 60):
        self.interval = interval
        self.components = [
            {
                "name": "Multi-Signal Bot",
                "process_pattern": "multi_signal_bot.py",
                "restart_cmd": "python3 multi_signal_bot.py &",
                "critical": True,
            },
            {
                "name": "New Listings Radar",
                "process_pattern": "new_listings_radar",
                "restart_cmd": "python3 run_new_listings_radar.py --scan &",
                "critical": True,
            },
            {
                "name": "Exchange Alerts",
                "process_pattern": "setup_exchange_alerts.py",
                "restart_cmd": "python3 setup_exchange_alerts.py &",
                "critical": False,
            },
            {
                "name": "Dashboard",
                "process_pattern": "dashboard_summary.py",
                "restart_cmd": "python3 dashboard_summary.py &",
                "critical": False,
            },
        ]
        self.trading_metrics = {}
        self.system_status = {}
        self.log_entries = []

    def check_process_running(self, pattern: str) -> bool:
        """Check if a process matching pattern is running"""
        try:
            cmd = f"ps -ef | grep '{pattern}' | grep -v grep"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip() != ""
        except Exception as e:
            logging.error(f"Error checking process {pattern}: {e}")
            return False

    def restart_process(self, restart_cmd: str) -> bool:
        """Restart a failed process"""
        try:
            subprocess.Popen(restart_cmd, shell=True)
            logging.info(f"Restarted process: {restart_cmd}")
            return True
        except Exception as e:
            logging.error(f"Failed to restart process: {e}")
            return False

    def get_recent_logs(self, log_file: str, lines: int = 10) -> List[str]:
        """Get recent log entries"""
        try:
            with open(log_file, "r") as f:
                return f.readlines()[-lines:]
        except Exception as e:
            return [f"Error reading log file: {e}"]

    def update_trading_metrics(self) -> None:
        """Update trading performance metrics"""
        try:
            metrics_file = "trading_metrics.json"
            if os.path.exists(metrics_file):
                with open(metrics_file, "r") as f:
                    self.trading_metrics = json.load(f)
        except Exception as e:
            logging.error(f"Error updating trading metrics: {e}")

    def update_listings_data(self) -> None:
        """Update new listings data"""
        try:
            listings_file = "new_listings_radar.log"
            if os.path.exists(listings_file):
                self.log_entries = self.get_recent_logs(listings_file, 50)
        except Exception as e:
            logging.error(f"Error updating listings data: {e}")

    def generate_dashboard(self) -> None:
        """Generate system status dashboard"""
        clear_screen()

        # Header
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("╔" + "═" * 60 + "╗")
        print(f"║ 📊 SYSTEM MONITOR - {current_time}" + " " * (60 - 19 - len(current_time)) + "║")
        print("╠" + "═" * 60 + "╣")

        # Component status
        print("║ 🔍 COMPONENT STATUS:                                      ║")
        for component in self.components:
            name = component["name"]
            running = self.check_process_running(component["process_pattern"])
            status = "🟢 RUNNING" if running else "🔴 STOPPED"
            critical = " (CRITICAL)" if component["critical"] else ""
            padding = " " * (60 - 7 - len(name) - len(status) - len(critical))
            print(f"║   {name}: {status}{critical}{padding}║")

        # Trading metrics
        print("╠" + "═" * 60 + "╣")
        print("║ 💰 TRADING PERFORMANCE:                                  ║")
        if self.trading_metrics:
            metrics = [
                ("Total PnL", f"${self.trading_metrics.get('total_pnl', 0):.2f}"),
                ("Win Rate", f"{self.trading_metrics.get('win_rate', 0) * 100:.1f}%"),
                (
                    "Active Positions",
                    str(self.trading_metrics.get("active_positions", 0)),
                ),
            ]
            for label, value in metrics:
                padding = " " * (60 - 4 - len(label) - len(value))
                print(f"║   {label}: {value}{padding}║")
        else:
            print("║   No trading metrics available                           ║")

        # Recent activity
        print("╠" + "═" * 60 + "╣")
        print("║ 🚨 RECENT ACTIVITY:                                      ║")
        if self.log_entries:
            for i, entry in enumerate(self.log_entries[-5:]):
                entry = entry.strip()
                if "NEW LISTING" in entry or "Error" in entry:
                    entry = entry[:53] + "..." if len(entry) > 56 else entry
                    padding = " " * (60 - 4 - len(entry))
                    print(f"║   {entry}{padding}║")
        else:
            print("║   No recent activity                                     ║")

        # System resources
        print("╠" + "═" * 60 + "╣")
        print("║ 🖥️  SYSTEM RESOURCES:                                     ║")
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        print(f"║   CPU: {cpu:.1f}% | Memory: {mem:.1f}%                          ║")

        # Footer
        print("╚" + "═" * 60 + "╝")

    def run(self, show_dashboard: bool = False, restart_failed: bool = False) -> None:
        """Run the system monitor"""
        logging.info("Starting system monitor...")
        logging.info(f"Monitoring interval: {self.interval} seconds")

        while True:
            try:
                logging.info("Updating system status...")

                # Check component status
                self.system_status = {}
                for component in self.components:
                    running = self.check_process_running(component["process_pattern"])
                    self.system_status[component["name"]] = running

                    # Restart if needed
                    if restart_failed and not running and component["critical"]:
                        logging.warning(f"Critical component {component['name']} not running, restarting...")
                        self.restart_process(component["restart_cmd"])

                # Update metrics
                self.update_trading_metrics()
                self.update_listings_data()

                # Show dashboard if requested
                if show_dashboard:
                    self.generate_dashboard()

                # Sleep until next check
                time.sleep(self.interval)

            except Exception as e:
                logging.error(f"Error in monitor loop: {e}")
                time.sleep(self.interval)


def clear_screen():
    """Clear the terminal screen"""
    os.system("cls" if os.name == "nt" else "clear")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Live System Monitor for Multiple-signal-decision-bot")
    parser.add_argument("--interval", type=int, default=60, help="Update interval in seconds")
    parser.add_argument("--dashboard", action="store_true", help="Display live dashboard")
    parser.add_argument(
        "--restart-failed",
        action="store_true",
        help="Automatically restart failed components",
    )
    args = parser.parse_args()

    monitor = SystemMonitor(interval=args.interval)
    try:
        monitor.run(show_dashboard=args.dashboard, restart_failed=args.restart_failed)
    except KeyboardInterrupt:
        logging.info("System monitor stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
