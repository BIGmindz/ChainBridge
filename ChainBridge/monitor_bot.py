#!/usr/bin/env python3
"""
Live Trading Bot Monitor
Simple script to show bot status, signals, and trading activity
"""

import subprocess
import sys
import os
import time
from datetime import datetime


def print_header():
    """Print monitoring header"""
    print("=" * 80)
    print("🤖 BENSON BOT LIVE TRADING MONITOR")
    print("=" * 80)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📊 Monitoring: Real-time signals, balance, and trade execution")
    print("🔄 Press Ctrl+C to stop monitoring")
    print("=" * 80)


def check_bot_status():
    """Check if the bot is running"""
    try:
        # Check if live_trading_bot.py is running
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        if "live_trading_bot.py" in result.stdout:
            return True
        return False
    except Exception:
        return False


def start_bot_if_needed():
    """Start the bot if it's not running"""
    if not check_bot_status():
        print("🚀 Starting live trading bot...")
        try:
            # Change to the bot directory
            bot_dir = os.path.dirname(os.path.abspath(__file__))
            os.chdir(bot_dir)

            # Start the bot in background
            subprocess.Popen(
                [sys.executable, "live_trading_bot.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(3)  # Give it time to start

            if check_bot_status():
                print("✅ Bot started successfully!")
            else:
                print("⚠️  Bot may still be starting...")
        except Exception as e:
            print(f"❌ Error starting bot: {e}")
    else:
        print("✅ Bot is already running!")


def monitor_bot():
    """Monitor the bot output"""
    try:
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(bot_dir)

        print("\n📡 LIVE BOT OUTPUT:")
        print("-" * 80)

        # Follow the bot output in real-time
        process = subprocess.Popen(
            [sys.executable, "live_trading_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Print output line by line as it comes
        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if line:
                    # Filter for important information
                    line = line.strip()
                    if any(
                        keyword in line
                        for keyword in [
                            "📊",
                            "🎯",
                            "💼",
                            "💰",
                            "📈",
                            "🚀",
                            "⚡",
                            "BTC/USD",
                            "ETH/USD",
                            "SOL/USD",
                            "XRP/USD",
                            "Signal:",
                            "PORTFOLIO",
                            "BUY",
                            "SELL",
                            "HOLD",
                            "Capital:",
                            "Balance:",
                            "Positions:",
                            "P&L:",
                        ]
                    ):
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] {line}")
                        sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        return
    except Exception as e:
        print(f"\n❌ Error monitoring bot: {e}")


def main():
    """Main monitoring function"""
    print_header()

    # Check if we're in the right directory
    if not os.path.exists("live_trading_bot.py"):
        print("❌ Error: live_trading_bot.py not found in current directory")
        print("🔧 Please run this script from the bot directory")
        return

    try:
        # Start bot if needed
        start_bot_if_needed()

        # Monitor the bot
        monitor_bot()

    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped. Bot continues running in background.")
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")


if __name__ == "__main__":
    main()
