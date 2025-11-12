#!/usr/bin/env python3
"""
Trading Mode Switcher

Safely switches between paper and live trading modes by:
1. Stopping all running trading processes
2. Updating the .env file
3. Providing restart instructions
"""

import sys
import time
import subprocess
from pathlib import Path


def stop_all_trading_processes():
    """Stop all running trading-related processes."""
    print("🛑 Stopping all trading processes...")

    processes_to_kill = [
        "multi_signal_bot.py",
        "benson_rsi_bot.py",
        "rapid_fire_ml_trainer.py",
        "dashboard.py",
        "animated_dashboard",
        "streamlit",
    ]

    killed_count = 0
    for proc_name in processes_to_kill:
        try:
            # Use pkill to kill processes matching the pattern
            result = subprocess.run(["pkill", "-f", proc_name], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ Stopped processes matching: {proc_name}")
                killed_count += 1
            else:
                print(f"   ℹ️  No processes found for: {proc_name}")
        except Exception as e:
            print(f"   ⚠️  Error stopping {proc_name}: {e}")

    if killed_count > 0:
        print(f"🛑 Successfully stopped {killed_count} process groups")
        # Give processes time to shut down cleanly
        time.sleep(2)
    else:
        print("ℹ️  No running trading processes found")


def update_env_file(new_paper_value):
    """Update the PAPER setting in .env file."""
    env_path = Path(".env")

    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False

    try:
        # Read current content
        content = env_path.read_text()

        # Update or add PAPER setting
        if "PAPER=" in content:
            # Replace existing
            import re

            content = re.sub(r"PAPER=.*", f"PAPER={new_paper_value}", content)
        else:
            # Add new
            content += f"\nPAPER={new_paper_value}\n"

        # Write back
        env_path.write_text(content)
        print(f"✅ Updated .env: PAPER={new_paper_value}")
        return True

    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False


def confirm_live_mode():
    """Get confirmation before switching to live mode."""
    print()
    print("⚠️  DANGER: You are about to enable LIVE TRADING!")
    print("   This will execute REAL TRADES with REAL MONEY!")
    print()
    print("   Make sure you have:")
    print("   - Valid API credentials in .env")
    print("   - Sufficient funds in your account")
    print("   - Understanding of the risks")
    print()

    response = input("Type 'YES' to confirm live trading: ").strip()
    return response.upper() == "YES"


def show_restart_instructions(target_mode):
    """Show instructions for restarting in the new mode."""
    mode_name = "LIVE TRADING" if target_mode == "false" else "PAPER TRADING"

    print(f"\n🎯 Successfully switched to {mode_name} mode!")
    print("\n📋 To start trading in the new mode:")
    print()
    print("1. Activate your virtual environment:")
    print("   source .venv/bin/activate")
    print()
    print("2. Run the preflight check:")
    print("   python multi_signal_bot.py --dry-preflight")
    print()
    print("3. Start the bot:")
    print("   python multi_signal_bot.py")
    print()
    print("4. Or start with custom config:")
    print("   python multi_signal_bot.py --config config/config.yaml --capital 10000")
    print()


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python switch_trading_mode.py [paper|live]")
        print()
        print("Examples:")
        print("  python switch_trading_mode.py paper  # Switch to paper trading")
        print("  python switch_trading_mode.py live   # Switch to live trading")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command not in ["paper", "live"]:
        print("❌ Invalid command. Use 'paper' or 'live'")
        sys.exit(1)

    target_paper_value = "true" if command == "paper" else "false"
    target_mode_name = "paper trading" if command == "paper" else "LIVE TRADING"

    print(f"🔄 Switching to {target_mode_name} mode...")
    print("=" * 50)

    # Step 1: Stop all processes
    stop_all_trading_processes()

    # Step 2: Confirm live mode if switching to live
    if command == "live":
        if not confirm_live_mode():
            print("❌ Live mode switch cancelled.")
            sys.exit(1)

    # Step 3: Update .env file
    if not update_env_file(target_paper_value):
        print("❌ Failed to update configuration. Mode not changed.")
        sys.exit(1)

    # Step 4: Show restart instructions
    show_restart_instructions(target_paper_value)

    print("✅ Mode switch complete! Ready to restart with new settings.")


if __name__ == "__main__":
    main()
