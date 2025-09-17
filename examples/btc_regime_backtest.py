#!/usr/bin/env python3
"""
Example script to run the regime backtester with our sample BTC price data.
This demonstrates how to use the regime-specific backtester with real market data.
"""

import os
import sys
import asyncio
import pandas as pd
from datetime import datetime
import numpy as np

# Conditionally import matplotlib
has_matplotlib = False
try:
    import matplotlib.pyplot as plt
    has_matplotlib = True
except ImportError:
    pass

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the backtester
from src.backtesting.regime_backtester import RegimeBacktester

async def run_btc_backtest():
    """Run backtesting on the BTC sample data"""
    # Load the BTC price data
    csv_path = 'sample_data/btc_price_data.csv'
    
    try:
        print(f"Loading BTC price data from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # Verify we have the necessary columns
        required_cols = ['date', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            print(f"Error: CSV must contain columns: {', '.join(required_cols)}")
            return
        
        # Extract price data
        price_data = df['close'].tolist()
        volume_data = df['volume'].tolist()
        dates = df['date'].tolist()
        
        # Create a more interesting dataset by synthesizing different market regimes
        # based on the sample data (which is very limited)
        print("Enhancing dataset with synthetic market regimes...")
        
        # Create a longer dataset with bull, bear, and sideways regimes
        enhanced_prices = []
        enhanced_volumes = []
        enhanced_dates = []
        
        # Use the data we have as a base
        base_price = price_data[0]
        price_range = max(price_data) - min(price_data)
        avg_volume = sum(volume_data) / len(volume_data)
        
        # Generate 180 days of data (6 months) with clear market regimes
        start_date = datetime.strptime(dates[0], "%Y-%m-%d")
        
        # Bull market for 60 days
        for i in range(60):
            # Bull market with upward trend
            if i == 0:
                new_price = base_price
            else:
                daily_return = np.random.normal(0.005, 0.012)  # 0.5% average daily gain
                new_price = enhanced_prices[-1] * (1 + daily_return)
            
            enhanced_prices.append(new_price)
            enhanced_volumes.append(avg_volume * np.random.uniform(0.8, 1.3))
            new_date = (start_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            enhanced_dates.append(new_date)
        
        # Sideways market for 30 days
        sideways_start_price = enhanced_prices[-1]
        for i in range(60, 90):
            # Sideways market with mean reversion
            deviation = (enhanced_prices[-1] / sideways_start_price) - 1
            daily_return = np.random.normal(-deviation * 0.2, 0.007)  # Mean reversion
            new_price = enhanced_prices[-1] * (1 + daily_return)
            
            enhanced_prices.append(new_price)
            enhanced_volumes.append(avg_volume * np.random.uniform(0.6, 0.9))  # Lower volume
            new_date = (start_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            enhanced_dates.append(new_date)
        
        # Bear market for 60 days
        for i in range(90, 150):
            # Bear market with downward trend
            daily_return = np.random.normal(-0.004, 0.015)  # 0.4% average daily loss
            new_price = enhanced_prices[-1] * (1 + daily_return)
            
            enhanced_prices.append(new_price)
            enhanced_volumes.append(avg_volume * np.random.uniform(1.1, 1.6))  # Higher volume
            new_date = (start_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            enhanced_dates.append(new_date)
        
        # Sideways market for 30 days
        sideways_start_price = enhanced_prices[-1]
        for i in range(150, 180):
            # Sideways market with mean reversion
            deviation = (enhanced_prices[-1] / sideways_start_price) - 1
            daily_return = np.random.normal(-deviation * 0.2, 0.008)  # Mean reversion
            new_price = enhanced_prices[-1] * (1 + daily_return)
            
            enhanced_prices.append(new_price)
            enhanced_volumes.append(avg_volume * np.random.uniform(0.6, 0.9))  # Lower volume
            new_date = (start_date + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            enhanced_dates.append(new_date)
        
        print(f"Enhanced dataset created with {len(enhanced_prices)} days of price data")
        
        # Visualize the enhanced dataset
        try:
            plt.figure(figsize=(12, 6))
            plt.plot(enhanced_prices)
            
            # Mark the different regime periods
            plt.axvspan(0, 60, alpha=0.2, color='green', label='Bull Market')
            plt.axvspan(60, 90, alpha=0.2, color='yellow', label='Sideways Market')
            plt.axvspan(90, 150, alpha=0.2, color='red', label='Bear Market')
            plt.axvspan(150, 180, alpha=0.2, color='yellow', label='Sideways Market')
            
            plt.title('Enhanced BTC Price Dataset with Market Regimes')
            plt.xlabel('Days')
            plt.ylabel('Price (USD)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig('enhanced_btc_dataset.png')
            plt.close()
            
            print("Dataset visualization saved as 'enhanced_btc_dataset.png'")
            
        except Exception as e:
            print(f"Warning: Could not create visualization: {e}")
        
        # Create and run the backtester
        backtester = RegimeBacktester(enhanced_prices, enhanced_volumes, enhanced_dates)
        
        # Run full backtest
        print("\nRunning full backtest...")
        full_results = await backtester.run_full_backtest()
        
        # Save and visualize results
        backtester.save_results(full_results, 'btc_regime_backtest.json')
        backtester.visualize_regime_performance(full_results)
        
        # Generate and print report
        report = backtester.generate_regime_report(full_results)
        print("\n" + report)
        
        # Run regime-specific backtests
        print("\nRunning regime comparison backtests...")
        regime_results = await backtester.compare_all_regimes()
        
        # Save regime-specific results
        backtester.save_results(regime_results, 'btc_regime_comparison.json')
        
        return {
            'full_results': full_results,
            'regime_results': regime_results
        }
        
    except Exception as e:
        print(f"Error during BTC backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   BTC REGIME-SPECIFIC BACKTEST                        ║
    ║   Testing Trading Performance Across Market Regimes    ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(run_btc_backtest())