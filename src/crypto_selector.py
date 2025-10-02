"""
VOLATILE CRYPTO SELECTOR
Find the most volatile cryptos for maximum trading opportunity
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

import ccxt
import numpy as np
import pandas as pd


class VolatileCryptoSelector:
    """
    Select cryptos with highest volatility for enhanced trading opportunities
    """

    def __init__(self, exchange_id: str = "kraken", lookback_days: int = 7):
        """
        Initialize with exchange and lookback period

        Args:
            exchange_id: Which exchange to use for data
            lookback_days: How many days of historical data to analyze
        """
        self.exchange_id = exchange_id
        self.lookback_days = lookback_days

        # Initialize exchange connection
        try:
            self.exchange = getattr(ccxt, exchange_id)()
        except Exception as e:
            print(f"⚠️ Failed to initialize exchange: {e}")
            self.exchange = None

    def _fetch_market_data(self) -> Dict[str, Any]:
        """Get market data from exchange"""
        try:
            if self.exchange:
                return self.exchange.load_markets()
            else:
                return {}
        except Exception as e:
            print(f"⚠️ Failed to fetch market data: {e}")
            return {}

    def _fetch_ohlcv(self, symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """Fetch historical OHLCV data for volatility calculation"""
        try:
            if self.exchange:
                since = int((datetime.now() - timedelta(days=self.lookback_days)).timestamp() * 1000)
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)

                # Convert to DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")  # type: ignore
                return df
            else:
                # Generate mock data for testing
                return self._generate_mock_data(symbol)
        except Exception as e:
            print(f"⚠️ Failed to fetch OHLCV data for {symbol}: {e}")
            return self._generate_mock_data(symbol)

    def _generate_mock_data(self, symbol: str) -> pd.DataFrame:
        """Generate mock OHLCV data for testing or when exchange API fails"""
        print(f"🧪 Generating mock volatility data for {symbol}")

        # Create realistic mock data based on symbol
        # Different cryptos have different volatility profiles
        data = []
        base_price = 0

        # Set base price and volatility based on symbol
        if "BTC" in symbol:
            base_price = 43000 + random.randint(-2000, 2000)
            volatility = 0.02
        elif "ETH" in symbol:
            base_price = 2400 + random.randint(-100, 100)
            volatility = 0.03
        elif "SOL" in symbol:
            base_price = 130 + random.randint(-10, 10)
            volatility = 0.05
        elif "DOGE" in symbol:
            base_price = 0.14 + random.random() * 0.02
            volatility = 0.08
        elif "SHIB" in symbol:
            base_price = 0.00002 + random.random() * 0.000002
            volatility = 0.10
        elif "AVAX" in symbol:
            base_price = 35 + random.randint(-2, 2)
            volatility = 0.04
        elif "MATIC" in symbol:
            base_price = 0.8 + random.random() * 0.1
            volatility = 0.06
        else:
            base_price = 50 + random.randint(-20, 20)
            volatility = 0.07

        # Generate daily candles
        for i in range(self.lookback_days):
            date = datetime.now() - timedelta(days=self.lookback_days - i)
            price_change = base_price * volatility * (random.random() * 2 - 1)
            base_price += price_change

            # Ensure price doesn't go negative
            base_price = max(base_price, base_price * 0.1)

            # Create daily candle
            high = base_price * (1 + random.random() * volatility)
            low = base_price * (1 - random.random() * volatility)
            open_price = low + random.random() * (high - low)
            close = low + random.random() * (high - low)
            volume = base_price * 1000 * (0.5 + random.random())

            data.append([date, open_price, high, low, close, volume])  # type: ignore

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df

    def calculate_volatility(self, symbol: str) -> float:
        """Calculate volatility for a specific symbol"""
        df = self._fetch_ohlcv(symbol)

        if df.empty:
            return 0.0

        # Calculate daily returns
        df["return"] = df["close"].pct_change()

        # Calculate standard deviation of returns (volatility)
        volatility = df["return"].std()

        # Annualize volatility
        annualized_volatility = volatility * np.sqrt(365)

        return annualized_volatility

    def get_top_volatile_cryptos(self, top_n: int = 5) -> List[str]:
        """
        Get top N volatile cryptocurrencies

        Args:
            top_n: Number of cryptocurrencies to return

        Returns:
            List of cryptocurrency symbols with highest volatility
        """
        print(f"🔍 Searching for top {top_n} volatile cryptos...")

        # Get available markets
        markets = self._fetch_market_data()

        if not markets and not self.exchange:
            # If we couldn't get real market data, use a predefined list
            print("ℹ️ Using predefined list of common volatile cryptos")
            common_volatiles = [
                "WIF/USD",
                "PEPE/USD",
                "BONK/USD",
                "SHIB/USD",
                "DOGE/USD",
                "SOL/USD",
                "AVAX/USD",
                "NEAR/USD",
                "MATIC/USD",
                "SUI/USD",
            ]
            return common_volatiles[:top_n]

        # Filter USD pairs (or USDT if no USD pairs available)
        usd_pairs = [symbol for symbol in markets.keys() if symbol.endswith("/USD") or symbol.endswith("/USDT")]

        # If we don't have enough pairs, use predefined list
        if len(usd_pairs) < top_n:
            print(f"⚠️ Not enough USD pairs ({len(usd_pairs)}), using predefined list")
            common_volatiles = [
                "WIF/USD",
                "PEPE/USD",
                "BONK/USD",
                "SHIB/USD",
                "DOGE/USD",
                "SOL/USD",
                "AVAX/USD",
                "NEAR/USD",
                "MATIC/USD",
                "SUI/USD",
            ]
            return common_volatiles[:top_n]

        # Sample a subset of pairs to avoid long processing times
        sample_size = min(20, len(usd_pairs))
        sampled_pairs = random.sample(usd_pairs, sample_size)

        # Calculate volatility for each pair
        volatilities = {}
        for symbol in sampled_pairs:
            print(f"Calculating volatility for {symbol}...")
            vol = self.calculate_volatility(symbol)
            volatilities[symbol] = vol
            print(f"{symbol}: {vol:.2%}")

        # Sort by volatility (descending)
        sorted_pairs = sorted(volatilities.items(), key=lambda x: x[1], reverse=True)

        # Get top N volatile pairs
        top_volatile = [pair[0] for pair in sorted_pairs[:top_n]]

        # Print results
        print(f"\n🏆 Top {top_n} volatile cryptocurrencies:")
        for i, symbol in enumerate(top_volatile):
            vol_pct = volatilities.get(symbol, 0) * 100
            print(f"{i + 1}. {symbol}: {vol_pct:.2f}% volatility")

        return top_volatile


if __name__ == "__main__":
    # Test the crypto selector
    selector = VolatileCryptoSelector()
    top_cryptos = selector.get_top_volatile_cryptos(top_n=5)
    print(f"\nFinal selection: {', '.join(top_cryptos)}")
