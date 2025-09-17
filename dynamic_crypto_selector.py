#!/usr/bin/env python3
"""
DYNAMIC CRYPTO SELECTOR
Automatically finds and trades the most volatile/volume cryptos
This ensures you always have 'trade bait' with movement
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

class VolatileCryptoSelector:
    """
    Finds the best cryptos to trade based on volatility and volume
    Your edge: Always trading where the action is
    """
    
    def __init__(self, exchange='kraken'):
        """Initialize with exchange"""
        self.exchange = getattr(ccxt, exchange)()
        self.top_cryptos = []
        self.volatility_scores = {}
        
    def get_top_volatile_cryptos(self, base_currency='USD', top_n=5):
        """
        Get the top N most volatile cryptos
        These are your 'trade bait' - high movement = high opportunity
        """
        
        # Default list of highly volatile cryptos (fallback)
        volatile_candidates = [
            'BTC/USD',   # The king - always liquid
            'ETH/USD',   # #2 - smart contract leader  
            'SOL/USD',   # Fast & volatile
            'DOGE/USD',  # Meme king - huge swings
            'SHIB/USD',  # Micro movements = big %
            'PEPE/USD',  # New meme volatility
            'WIF/USD',   # Solana meme coin
            'AVAX/USD',  # DeFi volatility
            'MATIC/USD', # Polygon - news driven
            'ATOM/USD',  # Cosmos ecosystem
            'NEAR/USD',  # AI narrative coin
            'APT/USD',   # Aptos - new & volatile
            'ARB/USD',   # Arbitrum - L2 leader
            'INJ/USD',   # Injective - DeFi
            'SEI/USD'    # New & volatile
        ]
        
        volatility_data = {}
        
        print("\n🔍 Analyzing crypto volatility...")
        
        for symbol in volatile_candidates:
            try:
                # Get recent price data
                ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=24)
                
                if ohlcv and len(ohlcv) > 0:
                    # Calculate volatility metrics
                    closes = [x[4] for x in ohlcv]  # Close prices
                    volumes = [x[5] for x in ohlcv]  # Volumes
                    
                    # Calculate volatility (standard deviation of returns)
                    returns = pd.Series(closes).pct_change().dropna()
                    volatility = returns.std() * np.sqrt(24)  # Daily volatility
                    
                    # Calculate average volume (in USD)
                    avg_price = np.mean(closes)
                    avg_volume_usd = np.mean(volumes) * avg_price
                    
                    # Combined score (volatility * volume for liquidity)
                    score = volatility * np.log10(avg_volume_usd + 1)
                    
                    volatility_data[symbol] = {
                        'volatility': volatility,
                        'volume_usd': avg_volume_usd,
                        'score': score,
                        'last_price': closes[-1]
                    }
                    
            except Exception as e:
                print(f"  ⚠️ Couldn't analyze {symbol}: {str(e)[:50]}")
                continue
        
        # Sort by score and get top N
        sorted_cryptos = sorted(volatility_data.items(), 
                               key=lambda x: x[1]['score'], 
                               reverse=True)[:top_n]
        
        self.top_cryptos = [crypto for crypto, _ in sorted_cryptos]
        self.volatility_scores = dict(sorted_cryptos)
        
        print(f"\n🎯 Top {top_n} Most Volatile Cryptos Selected:")
        for i, (symbol, data) in enumerate(sorted_cryptos, 1):
            print(f"  {i}. {symbol}")
            print(f"     Volatility: {data['volatility']*100:.1f}%")
            print(f"     Volume: ${data['volume_usd']:,.0f}")
            print(f"     Score: {data['score']:.2f}")
        
        return self.top_cryptos
    
    def get_trading_parameters(self, symbol):
        """
        Get optimized trading parameters for each crypto
        Based on its volatility characteristics
        """
        if symbol in self.volatility_scores:
            volatility = self.volatility_scores[symbol]['volatility']
            
            # Adjust parameters based on volatility
            if volatility > 0.10:  # High volatility (>10% daily)
                return {
                    'position_size_pct': 0.02,  # Smaller positions
                    'stop_loss': 0.03,  # Tighter stops
                    'take_profit': 0.05,  # Quick profits
                    'signal_threshold': 0.7  # Higher confidence required
                }
            elif volatility > 0.05:  # Medium volatility
                return {
                    'position_size_pct': 0.03,
                    'stop_loss': 0.05,
                    'take_profit': 0.08,
                    'signal_threshold': 0.6
                }
            else:  # Lower volatility
                return {
                    'position_size_pct': 0.05,
                    'stop_loss': 0.07,
                    'take_profit': 0.10,
                    'signal_threshold': 0.5
                }
        
        # Default parameters
        return {
            'position_size_pct': 0.03,
            'stop_loss': 0.05,
            'take_profit': 0.08,
            'signal_threshold': 0.6
        }
    
    def update_config_file(self, config_path='config.yaml'):
        """Update the main config file with the selected cryptos"""
        
        if not self.top_cryptos:
            print("⚠️ No cryptos selected yet. Run get_top_volatile_cryptos() first.")
            return False
            
        try:
            # Get the original config
            import yaml
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as file:
                    config = yaml.safe_load(file)
            else:
                config = {}
            
            # Update symbols
            config['symbols'] = self.top_cryptos
            
            # Write back to file
            with open(config_path, 'w') as file:
                yaml.dump(config, file, default_flow_style=False)
                
            print(f"✅ Updated {config_path} with top {len(self.top_cryptos)} volatile cryptocurrencies")
            return True
            
        except Exception as e:
            print(f"❌ Error updating config file: {e}")
            return False

# Test the selector
if __name__ == "__main__":
    selector = VolatileCryptoSelector()
    top_cryptos = selector.get_top_volatile_cryptos()
    
    print("\n✅ Ready to trade the most volatile cryptos!")
    
    # Save configuration
    config = {
        'selected_cryptos': top_cryptos,
        'volatility_scores': selector.volatility_scores,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('volatile_cryptos_config.json', 'w') as f:
        json.dump(config, f, indent=2, default=str)
    
    print(f"📁 Configuration saved to volatile_cryptos_config.json")
    
    # Update main config file
    selector.update_config_file()