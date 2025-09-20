import ccxt
import os
import pandas as pd

def test_market_data():
    try:
        # Initialize exchange
        print("Initializing Kraken exchange...")
        exchange = ccxt.kraken({
            'apiKey': '1234',
            'secret': 'dummy',
            'enableRateLimit': True
        })
        
        # Fetch OHLCV data
        print("Fetching BTC/USD data...")
        ohlcv = exchange.fetch_ohlcv('BTC/USD', '1m', limit=100)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Print sample
        print("\nSample of fetched data:")
        print(df.head())
        print("\nShape:", df.shape)
        
        return True
        
    except Exception as e:
        print(f"\nError fetching market data: {str(e)}")
        return False

if __name__ == '__main__':
    test_market_data()