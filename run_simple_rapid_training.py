#!/usr/bin/env python3
"""
Run Simple Rapid Fire Training System (No TensorFlow)

This script launches the 30-minute intensive paper trading simulation
with signal weight optimization for the Multiple-signal-decision-bot.
This version doesn't require TensorFlow.
"""

import argparse
import os
from datetime import datetime

# Import the SimpleRapidFireTrainer
from simple_rapid_fire_trainer import SimpleRapidFireTrainer


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run Simple Rapid Fire Training (No TensorFlow)")
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration of training in minutes (default: 30)",
    )
    parser.add_argument(
        "--cycle",
        type=int,
        default=30,
        help="Seconds between training cycles (default: 30)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial paper trading capital (default: $1000)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "--dashboard",
        type=int,
        default=15,
        help="Minutes between dashboard updates (default: 15)",
    )

    return parser.parse_args()


def setup_environment():
    """Setup the training environment"""
    # Create data directories if they don't exist
    os.makedirs("data/rapid_fire_sessions", exist_ok=True)

    # Print system information
    print(
        f"""
    ╔══════════════════════════════════════════════════════════════
    ║ 🚀 SIMPLE RAPID FIRE TRAINING SYSTEM (NO TENSORFLOW)
    ║══════════════════════════════════════════════════════════════
    ║ Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ║ System: Multiple-signal-decision-bot
    ║ Mode: 30-minute intensive paper trading
    ║ Focus: Signal weight optimization and performance tracking
    ║ Dashboard: Updates every 15 minutes
    ╚══════════════════════════════════════════════════════════════
    """
    )


def main():
    """Main function to run the training system"""
    # Parse command line arguments
    args = parse_args()

    # Setup environment
    setup_environment()

    try:
        # Create the SimpleRapidFireTrainer
        trainer = SimpleRapidFireTrainer(config_path=args.config, initial_capital=args.capital)

        # Run the training session
        trainer.run_training(duration_minutes=args.duration, cycle_seconds=args.cycle)

    except KeyboardInterrupt:
        print("\nSimple Rapid Fire Training interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

# Replace references to undefined 'api_config' with environment variable lookups
#     api_key = api_config.get("key", "").strip()
#     api_secret = api_config.get("secret", "").strip()
api_key = str(os.getenv("API_KEY", "")).strip()
api_secret = str(os.getenv("API_SECRET", "")).strip()
