#!/usr/bin/env python3
"""
Dashboard Summary - Quick view of trading system status
"""

import datetime
import json
import os
import subprocess
import sys
import time

from tabulate import tabulate


def print_header(title):
    """Print a formatted header"""
    width = 70
    print("\n" + "=" * width)
    print(f"{title.center(width)}")
    print("=" * width)


def check_process_running(process_name):
    """Check if a process is running"""
    try:
        output = subprocess.check_output(["ps", "-ef"]).decode()
        return process_name in output and "grep" not in output
    except subprocess.CalledProcessError:
        return False


def read_json_file(filepath):
    """Read a JSON file safely"""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def format_currency(value):
    """Format value as currency"""
    return f"${value:.2f}"


def main():
    """Main function"""
    print("\033c", end="")  # Clear screen

    # System header
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_header(f"📊 TRADING SYSTEM DASHBOARD - {current_time}")

    # Check running components
    components = [
        ("Multi-Signal Bot", "multi_signal_bot.py"),
        ("New Listings Radar", "run_new_listings_radar.py"),
        ("System Monitor", "monitor_live_system.py"),
    ]

    component_status = []
    for name, process in components:
        is_running = check_process_running(process)
        status = "🟢 RUNNING" if is_running else "🔴 STOPPED"
        component_status.append([name, status])

    print("\n📡 SYSTEM COMPONENTS:")
    print(tabulate(component_status, headers=["Component", "Status"], tablefmt="simple"))

    # Read performance data
    trading_metrics = read_json_file("trading_metrics.json")
    if trading_metrics:
        print("\n💰 TRADING PERFORMANCE:")
        performance_data = [
            ["Total PnL", format_currency(trading_metrics.get("total_pnl", 0))],
            ["Realized PnL", format_currency(trading_metrics.get("realized_pnl", 0))],
            [
                "Unrealized PnL",
                format_currency(trading_metrics.get("unrealized_pnl", 0)),
            ],
            ["Win Rate", f"{trading_metrics.get('win_rate', 0) * 100:.1f}%"],
            ["Active Positions", trading_metrics.get("active_positions", 0)],
        ]
        print(tabulate(performance_data, tablefmt="simple"))

    # Read allocation data
    allocation_state = read_json_file("allocation_state.json")
    if allocation_state:
        print("\n🏦 CAPITAL ALLOCATION:")
        allocations = []
        for alloc in allocation_state.get("allocations", []):
            allocations.append(
                [
                    alloc.get("symbol", "Unknown"),
                    alloc.get("exchange", "Unknown"),
                    format_currency(alloc.get("amount", 0)),
                    f"{alloc.get('confidence', 0) * 100:.1f}%",
                    alloc.get("risk_level", "Unknown"),
                ]
            )

        if allocations:
            print(
                tabulate(
                    allocations,
                    headers=["Symbol", "Exchange", "Amount", "Confidence", "Risk"],
                    tablefmt="simple",
                )
            )
        else:
            print("No active allocations")

    # Read signals data
    signals_data = {}
    try:
        with open("benson_signals.csv", "r") as f:
            lines = f.readlines()
            if len(lines) > 1:  # Header + at least one data row
                latest = lines[-1].strip().split(",")
                if len(latest) >= 5:
                    signals_data = {
                        "timestamp": latest[0],
                        "rsi": latest[1],
                        "macd": latest[2],
                        "bollinger": latest[3],
                        "sentiment": latest[4],
                    }
    except (IOError, IndexError):
        pass

    if signals_data:
        print("\n🔍 LATEST SIGNALS:")
        signals = []
        for key, value in signals_data.items():
            if key != "timestamp":
                signals.append([key.upper(), value])
        print(tabulate(signals, headers=["Signal", "Value"], tablefmt="simple"))

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        while True:
            main()
            time.sleep(10)  # Update every 10 seconds
    except KeyboardInterrupt:
        print("\nDashboard stopped by user")
        sys.exit(0)
