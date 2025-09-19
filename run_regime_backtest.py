#!/usr/bin/env python3
"""
Run the regime-specific backtesting tool to evaluate trading performance
across different market regimes (bull, bear, sideways).
"""

import os
import sys
import asyncio
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the backtester
from src.backtesting.regime_backtester import RegimeBacktester, demo_regime_backtester

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Regime-Specific Backtesting Tool"
    )
    
    parser.add_argument(
        "--demo", 
        action="store_true",
        help="Run the backtester demo with synthetic data"
    )
    
    parser.add_argument(
        "--data", 
        type=str,
        help="Path to CSV file with price data (requires columns: date, price, volume)"
    )
    
    parser.add_argument(
        "--output", 
        type=str,
        default="regime_backtest_results.json",
        help="Path to save results JSON file"
    )
    
    return parser.parse_args()

async def run_with_data_file(file_path, output_path):
    """Run the backtester with data from a CSV file"""
    import pandas as pd
    
    # Load the data
    try:
        print(f"Loading data from {file_path}...")
        df = pd.read_csv(file_path)
        
        # Check for required columns
        required_cols = ['price']
        if not all(col in df.columns for col in required_cols):
            print("Error: CSV must contain at least a 'price' column")
            return
            
        # Extract data
        price_data = df['price'].tolist()
        
        # Optional columns
        volume_data = None
        if 'volume' in df.columns:
            volume_data = df['volume'].tolist()
            
        dates = None
        date_col = next((col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()), None)
        if date_col:
            dates = df[date_col].tolist()
        
        print(f"Loaded {len(price_data)} data points from {file_path}")
        
        # Create and run backtester
        backtester = RegimeBacktester(price_data, volume_data, dates)
        
        # Run full backtest
        print("\nRunning full backtest...")
        full_results = await backtester.run_full_backtest()
        
        # Save and visualize results
        backtester.save_results(full_results, output_path)
        backtester.visualize_regime_performance(full_results)
        
        # Generate and print report
        report = backtester.generate_regime_report(full_results)
        print("\n" + report)
        
        # Run regime-specific backtests
        print("\nRunning regime comparison backtests...")
        regime_results = await backtester.compare_all_regimes()
        
        # Save regime-specific results
        regime_output = output_path.replace('.json', '_comparison.json')
        backtester.save_results(regime_results, regime_output)
        
        print(f"\nResults saved to {output_path} and {regime_output}")
        
    except Exception as e:
        print(f"Error processing CSV file: {e}")

async def main():
    """Main function to run the regime backtester"""
    args = parse_arguments()
    
    if args.demo:
        print("Running regime backtester demo with synthetic data...")
        await demo_regime_backtester()
        
    elif args.data:
        print(f"Running regime backtester with data from {args.data}...")
        await run_with_data_file(args.data, args.output)
        
    else:
        # Default to demo
        print("No options specified. Running demo with synthetic data...")
        await demo_regime_backtester()

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   REGIME-SPECIFIC BACKTESTING TOOL                    ║
    ║   Analyze Trading Performance Across Market Regimes    ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())