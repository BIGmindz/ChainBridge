#!/usr/bin/env python3
"""
Automated Multi-Signal Trader with Dynamic Crypto Selection

This script combines the dynamic crypto selector with the multi-signal trading bot
to create a fully automated trading system that:
1. Finds the most volatile cryptocurrencies
2. Updates the trading configuration
3. Runs the multi-signal bot with the selected cryptocurrencies
"""

import os
import time
import argparse
import logging
from datetime import datetime, timedelta

# Import our components
from dynamic_crypto_selector import VolatileCryptoSelector
from multi_signal_bot import run_multi_signal_bot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/automated_trader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutomatedTrader")

def run_automated_trader(refresh_hours=12, run_once=False):
    """
    Main function to run the automated trading system
    
    Args:
        refresh_hours: How often to refresh the crypto selection (in hours)
        run_once: Whether to run just once or continuously
    """
    
    logger.info("🚀 Starting Automated Multi-Signal Trader")
    
    last_selection_time = datetime.min
    
    while True:
        current_time = datetime.now()
        
        # Check if it's time to refresh the crypto selection
        if (current_time - last_selection_time) > timedelta(hours=refresh_hours):
            logger.info(f"Time to refresh crypto selection (every {refresh_hours} hours)")
            
            try:
                # Run the crypto selector
                logger.info("Starting dynamic crypto selection...")
                selector = VolatileCryptoSelector()
                
                # Get top volatile cryptos
                top_cryptos = selector.get_top_volatile_cryptos(top_n=5)
                
                # Update the configuration
                selector.update_config_file()
                
                logger.info(f"Selected cryptos: {', '.join(top_cryptos)}")
                
                # Update the last selection time
                last_selection_time = current_time
                
                # Save trading parameters for each selected crypto
                trading_params = {}
                for symbol in top_cryptos:
                    params = selector.get_trading_parameters(symbol)
                    trading_params[symbol] = params
                    
                logger.info("Trading parameters optimized for each crypto")
                
                # Save parameters to file for reference
                import json
                with open('trading_parameters.json', 'w') as f:
                    json.dump(trading_params, f, indent=2)
                
            except Exception as e:
                logger.error(f"Error in crypto selection: {e}")
        
        # Run the trading bot (one cycle if run_once=True)
        try:
            logger.info("Starting multi-signal trading bot...")
            run_multi_signal_bot(once=True)  # Always run once per cycle
        except Exception as e:
            logger.error(f"Error in trading bot: {e}")
        
        # If we're only supposed to run once, exit now
        if run_once:
            logger.info("Run-once mode enabled, exiting...")
            break
            
        # Sleep for a bit before the next cycle
        # We'll run the bot every 5 minutes, but only refresh the crypto selection
        # according to the refresh_hours parameter
        logger.info("Sleeping for 5 minutes before next cycle")
        time.sleep(300)  # 5 minutes

def main():
    """CLI entrypoint with command-line arguments"""
    parser = argparse.ArgumentParser(description="Automated Multi-Signal Trader")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--refresh", type=int, default=12, help="Hours between crypto selection refresh (default: 12)")
    args = parser.parse_args()

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Run the automated trader
    run_automated_trader(refresh_hours=args.refresh, run_once=args.once)

if __name__ == "__main__":
    main()