#!/usr/bin/env python3
"""
Run Rapid Fire ML Training System

This script launches the 30-minute intensive paper trading simulation
with real-time learning and pattern recognition for the Multiple-signal-decision-bot.
"""

import argparse
import os
from datetime import datetime

# Import the RapidFireMLTrainer
from rapid_fire_ml_trainer import RapidFireMLTrainer


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run Rapid Fire ML Training System")
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
    ║ 🚀 RAPID FIRE ML TRAINING SYSTEM
    ║══════════════════════════════════════════════════════════════
    ║ Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ║ System: Multiple-signal-decision-bot
    ║ Mode: 30-minute intensive paper trading
    ║ Learning: Real-time pattern recognition and decision tracking
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
        # Create the RapidFireMLTrainer
        trainer = RapidFireMLTrainer(config_path=args.config, initial_capital=args.capital)

        # Run the training session
        trainer.run_training(duration_minutes=args.duration, cycle_seconds=args.cycle)

    except KeyboardInterrupt:
        print("\nRapid Fire ML Training interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
