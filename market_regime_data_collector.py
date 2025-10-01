#!/usr/bin/env python3
"""
Market Regime Data Collector - Collects and processes market data for ML training
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class MarketRegimeDataCollector:
    """
    Collects market data and calculates technical indicators for regime detection
    """

    def __init__(self, data_dir="data/regime_training"):
        self.data_dir = data_dir
        self.symbols = ["BTC/USD", "ETH/USD", "SOL/USD"]
        os.makedirs(data_dir, exist_ok=True)

    def collect_multi_asset_features(self):
        """Collect features from multiple assets"""
        logger.info("📊 Collecting multi-asset market features...")

        all_features = []

        for symbol in self.symbols:
            try:
                features = self._generate_mock_market_data(symbol)
                if features is not None:
                    all_features.extend(features)
            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")

        if all_features:
            df = pd.DataFrame(all_features)
            logger.info(f"✅ Collected {len(df)} data points from {len(self.symbols)} assets")
            return df
        else:
            logger.warning("No data collected")
            return None

    def _generate_mock_market_data(self, symbol):
        """Generate mock market data for demonstration with realistic regime patterns"""
        features = []

        # Generate 1000 data points with regime-specific patterns
        for i in range(1000):
            # Create regime-specific patterns
            regime_type = random.choice(["bull", "bear", "sideways"])

            # Generate realistic price data based on regime
            base_price = self._get_base_price(symbol)

            if regime_type == "bull":
                # Bull market: upward trending with oversold RSI
                trend_factor = 1 + (i * 0.001)  # Gradual upward trend
                volatility = 0.015  # Moderate volatility
                rsi_base = random.uniform(20, 40)  # Oversold
                momentum = random.uniform(0.01, 0.05)  # Positive momentum
            elif regime_type == "bear":
                # Bear market: downward trending with overbought RSI
                trend_factor = 1 - (i * 0.0008)  # Gradual downward trend
                volatility = 0.018  # Higher volatility
                rsi_base = random.uniform(60, 80)  # Overbought
                momentum = random.uniform(-0.05, -0.01)  # Negative momentum
            else:  # sideways
                # Sideways: range-bound with moderate RSI
                trend_factor = 1 + np.sin(i * 0.01) * 0.02  # Oscillating
                volatility = 0.012  # Lower volatility
                rsi_base = random.uniform(40, 60)  # Neutral
                momentum = random.uniform(-0.01, 0.01)  # Minimal momentum

            price = base_price * trend_factor * (1 + np.random.normal(0, volatility))

            # Calculate technical indicators
            feature_row = {
                "timestamp": datetime.now() - timedelta(days=i),
                "symbol": symbol,
                "price": price,
                "volume": random.uniform(100, 10000),
                "rsi_14": rsi_base + random.uniform(-5, 5),  # RSI around regime base
                "macd": random.uniform(-500, 500),
                "macd_signal": random.uniform(-500, 500),
                "macd_hist": random.uniform(-200, 200),
                "bb_upper": price * (1 + random.uniform(0.02, 0.08)),
                "bb_middle": price,
                "bb_lower": price * (1 - random.uniform(0.02, 0.08)),
                "bb_width": random.uniform(0.02, 0.08),
                "bb_position": random.uniform(-0.5, 0.5),
                "volume_ratio": random.uniform(0.5, 2.0),
                "price_change_1h": random.uniform(-0.05, 0.05),
                "price_change_24h": momentum + random.uniform(-0.02, 0.02),  # Momentum-based
                "volatility_24h": volatility + random.uniform(-0.005, 0.005),
                "trend_strength": random.uniform(0.1, 0.9) if regime_type != "sideways" else random.uniform(0.1, 0.3),
            }

            features.append(feature_row)  # type: ignore

        return features

    def _get_base_price(self, symbol):
        """Get base price for symbol"""
        prices = {"BTC/USD": 45000, "ETH/USD": 2800, "SOL/USD": 150}
        return prices.get(symbol, 1000)

    def _calculate_rsi_mock(self):
        """Generate realistic RSI values"""
        # RSI tends to oscillate between 20-80 in normal conditions
        return random.uniform(20, 80)

    def calculate_technical_features(self, df):
        """Calculate technical indicators from price data"""
        logger.info("🔧 Calculating technical indicators...")

        # RSI calculation
        df["rsi_14"] = self._calculate_rsi(df["price"])

        # MACD
        df["macd"], df["macd_signal"], df["macd_hist"] = self._calculate_macd(df["price"])

        # Bollinger Bands
        df["bb_upper"], df["bb_middle"], df["bb_lower"] = self._calculate_bollinger_bands(df["price"])
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        df["bb_position"] = (df["price"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]) - 0.5

        # Volume ratio
        df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # Price changes
        df["price_change_1h"] = df["price"].pct_change(1)
        df["price_change_24h"] = df["price"].pct_change(24)

        # Volatility
        df["volatility_24h"] = df["price"].pct_change(24).rolling(24).std()

        # Trend strength
        df["trend_strength"] = abs(df["price"].pct_change(50).rolling(50).mean())

        logger.info("✅ Technical indicators calculated")
        return df

    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        fast_ema = prices.ewm(span=fast).mean()
        slow_ema = prices.ewm(span=slow).mean()
        macd = fast_ema - slow_ema
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    def label_market_regime(self, df):
        """Label market regimes based on technical indicators"""
        logger.info("🏷️  Labeling market regimes...")

        # Drop rows with NaN values that can't be calculated (due to rolling windows)
        df_clean = df.dropna(subset=["rsi_14", "trend_strength", "price_change_24h", "volatility_24h", "bb_position"])

        # More robust regime detection based on actual data patterns
        conditions = [
            (df_clean["rsi_14"] < 45) & (df_clean["price_change_24h"] > 0.005),  # Bull: oversold + positive momentum (relaxed)
            (df_clean["rsi_14"] > 55) & (df_clean["price_change_24h"] < -0.005),  # Bear: overbought + negative momentum (relaxed)
            (df_clean["volatility_24h"] < 0.5) & (abs(df_clean["bb_position"]) < 0.4),  # Sideways: moderate vol + price not too extreme
        ]

        choices = ["bull", "bear", "sideways"]

        df_clean["regime"] = np.select(conditions, choices, default="sideways")

        # Show regime distribution
        regime_counts = df_clean["regime"].value_counts()
        logger.info(f"📊 Regime distribution: {regime_counts.to_dict()}")  # type: ignore

        return df_clean

    def save_training_data(self, df, filename=None):
        """Save training data to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"regime_training_data_{timestamp}.csv"

        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False)

        logger.info(f"💾 Training data saved: {filepath}")
        return filepath

    def get_current_features(self):
        """Get current market features for real-time detection"""
        try:
            # Generate current market features
            features = {
                "rsi_14": random.uniform(20, 80),
                "macd": random.uniform(-500, 500),
                "macd_signal": random.uniform(-500, 500),
                "macd_hist": random.uniform(-200, 200),
                "bb_upper": random.uniform(40000, 60000),
                "bb_middle": random.uniform(35000, 55000),
                "bb_lower": random.uniform(30000, 50000),
                "bb_width": random.uniform(0.02, 0.08),
                "bb_position": random.uniform(-0.5, 0.5),
                "volume_ratio": random.uniform(0.5, 2.0),
                "price_change_1h": random.uniform(-0.05, 0.05),
                "price_change_24h": random.uniform(-0.1, 0.1),
                "volatility_24h": random.uniform(0.01, 0.08),
                "trend_strength": random.uniform(0.1, 0.9),
            }

            logger.info("📊 Current market features generated")
            return features

        except Exception as e:
            logger.error(f"Error getting current features: {e}")
            return None


if __name__ == "__main__":
    # Demo the data collector
    print("🔬 Market Regime Data Collector Demo")
    print("=" * 40)

    collector = MarketRegimeDataCollector()

    # Collect data
    df = collector.collect_multi_asset_features()

    if df is not None:
        print(f"📊 Collected {len(df)} data points")
        print(f"📈 Features: {list(df.columns)}")  # type: ignore

        # Calculate technical indicators
        df = collector.calculate_technical_features(df)

        # Label regimes
        df = collector.label_market_regime(df)

        # Show sample
        print("\n📋 Sample Data:")
        print(df.head())

        # Save data
        filepath = collector.save_training_data(df)
        print(f"\n💾 Data saved to: {filepath}")

    print("\n✅ Demo Complete")
