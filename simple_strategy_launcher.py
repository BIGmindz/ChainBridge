#!/usr/bin/env python3
"""
Simple Strategy Launcher - Command Line Version
Usage: python simple_strategy_launcher.py [strategy_name]
"""

import subprocess
import sys
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def discover_strategies(base_path="strategies"):
    """Scans the strategy directory to find all available trading strategies."""
    if not os.path.exists(base_path):
        return {}

    strategies = {}
    for strategy_name in os.listdir(base_path):
        strategy_path = os.path.join(base_path, strategy_name)
        if os.path.isdir(strategy_path):
            config_path = os.path.join(strategy_path, "config.yaml")
            model_path = os.path.join(strategy_path, "model.pkl")

            # A valid strategy must have both a config and a model file.
            if os.path.exists(config_path) and os.path.exists(model_path):
                strategies[strategy_name] = {"config_path": config_path, "model_path": model_path}
    return strategies


def main():
    """
    Simple command-line strategy launcher.
    """
    logging.info("🔍 Discovering available trading strategies...")
    available_strategies = discover_strategies()

    if not available_strategies:
        logging.error("FATAL: No valid strategies found in the 'strategies/' directory.")
        logging.error("A valid strategy requires a 'config.yaml' and a 'model.pkl' file in its folder.")
        sys.exit(1)

    # Get strategy from command line argument or show available options
    if len(sys.argv) > 1:
        selected_strategy_name = sys.argv[1]
    else:
        print("\nAvailable strategies:")
        for i, name in enumerate(available_strategies.keys(), 1):
            print(f"  {i}. {name}")
        print("\nUsage: python simple_strategy_launcher.py <strategy_name>")
        print("Example: python simple_strategy_launcher.py bull_trend")
        return

    if selected_strategy_name not in available_strategies:
        logging.error(f"Strategy '{selected_strategy_name}' not found.")
        logging.info(f"Available strategies: {list(available_strategies.keys())}")
        sys.exit(1)

    selected_strategy = available_strategies[selected_strategy_name]

    logging.info("======================================================")
    logging.info(f"🚀 LAUNCHING STRATEGY: {selected_strategy_name.upper()} 🚀")
    logging.info("======================================================")

    try:
        # Pass the selected strategy's paths to the engine via environment variables
        env = os.environ.copy()
        env["BENSON_STRATEGY_CONFIG"] = selected_strategy["config_path"]
        env["BENSON_STRATEGY_MODEL"] = selected_strategy["model_path"]

        strategy_engine_script = "strategy_engine.py"
        if not os.path.exists(strategy_engine_script):
            logging.error(f"FATAL: Strategy Engine not found at '{strategy_engine_script}'.")
            sys.exit(1)

        logging.info(f"   Config: {selected_strategy['config_path']}")
        logging.info(f"   Model: {selected_strategy['model_path']}")

        subprocess.run([sys.executable, strategy_engine_script], check=True, env=env)

    except KeyboardInterrupt:
        logging.info("\nMaster launcher detected user shutdown (Ctrl+C). Session terminated.")
    except subprocess.CalledProcessError as e:
        logging.error(f"The trading session exited with an error (code {e.returncode}).")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
