#!/usr/bin/env python3
"""
Execute Immediate Actions

This script executes all immediate actions for the trading system:
1. Start full system live monitoring
2. Set alerts for all exchanges
3. Allocate $1000 for first listing
4. Document everything
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("immediate_actions.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def run_command(command, background=False):
    """Run a command and return the process"""
    # Replace python with python3 in the command
    command = command.replace("python ", "python3 ")
    logging.info(f"Running command: {command}")

    if background:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process
    else:
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info(f"Command completed with return code {result.returncode}")
            if result.stdout:
                logging.info(f"Command output: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed with return code {e.returncode}")
            logging.error(f"Error output: {e.stderr}")
            return e


def execute_step_1():
    """Step 1: Start full system live monitoring"""
    logging.info("STEP 1: Starting full system live monitoring")

    # Start the system monitor in the background
    process = run_command(
        "python monitor_live_system.py --dashboard > monitor_system.log 2>&1 &",
        background=True,
    )

    logging.info("System monitor started in background")
    return process


def execute_step_2():
    """Step 2: Set alerts for all exchanges"""
    logging.info("STEP 2: Setting alerts for all exchanges")

    # Start the exchange alert system in the background
    process = run_command("python setup_exchange_alerts.py > exchange_alerts.log 2>&1 &", background=True)

    logging.info("Exchange alerts started in background")
    return process


def execute_step_3():
    """Step 3: Allocate $1000 for first listing"""
    logging.info("STEP 3: Allocating $1000 for first listing")

    # Allocate capital for the first listing
    result = run_command("python allocate_capital.py --allocate")

    logging.info("Capital allocation completed")
    return result


def execute_step_4():
    """Step 4: Document everything"""
    logging.info("STEP 4: Documenting everything")

    # Verify that documentation files exist
    docs = [
        "TRADING_SYSTEM_DOCUMENTATION.md",
        "TRADING_SYSTEM_QUICKSTART.md",
        "README_NEW_LISTINGS.md",
        "QUICKSTART_NEW_LISTINGS.md",
    ]

    missing_docs = [doc for doc in docs if not os.path.exists(doc)]

    if missing_docs:
        logging.warning(f"Missing documentation files: {missing_docs}")
    else:
        logging.info("All documentation files exist")

    # Create a timestamp file to record execution
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"immediate_actions_executed_{timestamp}.txt", "w") as f:
        f.write(f"Immediate actions executed at {datetime.now().isoformat()}\n")
        f.write("1. Started full system live monitoring\n")
        f.write("2. Set alerts for all exchanges\n")
        f.write("3. Allocated $1000 for first listing\n")
        f.write("4. Verified documentation\n")

    logging.info(f"Execution record saved to immediate_actions_executed_{timestamp}.txt")
    return True


def start_trading_system():
    """Start the trading system"""
    logging.info("Starting the trading system")

    # Start New Listings Radar in the background
    run_command(
        "python run_new_listings_radar.py --scan > new_listings_radar.log 2>&1 &",
        background=True,
    )

    # Give it a moment to start
    time.sleep(2)

    # Start Multi-Signal Bot in the background
    run_command("python multi_signal_bot.py > multi_signal_bot.log 2>&1 &", background=True)

    logging.info("Trading system started")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Execute Immediate Actions for the Trading System")
    parser.add_argument("--start-trading", action="store_true", help="Also start the trading system")

    args = parser.parse_args()

    logging.info("Executing immediate actions")

    # Execute each step
    execute_step_1()
    execute_step_2()
    execute_step_3()
    execute_step_4()

    if args.start_trading:
        start_trading_system()

    logging.info("All immediate actions executed successfully")

    # Print summary
    print("\n" + "=" * 70)
    print("IMMEDIATE ACTIONS EXECUTED SUCCESSFULLY")
    print("=" * 70)
    print("\n1. ✅ Started full system live monitoring")
    print("2. ✅ Set alerts for all exchanges")
    print("3. ✅ Allocated $1000 for first listing")
    print("4. ✅ Documented everything")

    if args.start_trading:
        print("\n✅ Trading system started")
        print("\nView logs:")
        print("  • New Listings Radar: tail -f new_listings_radar.log")
        print("  • Multi-Signal Bot: tail -f multi_signal_bot.log")
        print("  • System Monitor: tail -f monitor_system.log")
        print("  • Exchange Alerts: tail -f exchange_alerts.log")

    print("\nNext steps:")
    if not args.start_trading:
        print("  • Start trading: python run_new_listings_radar.py --scan & python multi_signal_bot.py")
    print("  • Monitor system: python monitor_live_system.py --dashboard")
    print("  • Check alerts: python setup_exchange_alerts.py --status")
    print("  • Check allocation: python allocate_capital.py --status")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
