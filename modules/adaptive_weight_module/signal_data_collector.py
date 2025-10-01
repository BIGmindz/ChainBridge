#!/usr/bin/env python3
"""
Signal Data Collector

This module collects and preprocesses signal data from all 15 signals
across the 4 different layers for training the adaptive weight model.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np


class SignalDataCollector:
    """
    Collects, processes, and stores signal data for the adaptive weight model
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the signal data collector"""
        self.config = config or {}

        # Set up data paths
        self.data_dir = self.config.get("data_dir", os.path.join("data", "adaptive_weight_data"))
        os.makedirs(self.data_dir, exist_ok=True)

        # Signal configuration (allow overrides from config)
        default_signal_layers = {
            "LAYER_1_TECHNICAL": ["RSI", "MACD", "Bollinger", "Volume", "Sentiment"],
            "LAYER_2_LOGISTICS": [
                "Port_Congestion",
                "Diesel",
                "Supply_Chain",
                "Container",
            ],
            "LAYER_3_GLOBAL_MACRO": [
                "Inflation",
                "Regulatory",
                "Remittance",
                "CBDC",
                "FATF",
            ],
            "LAYER_4_ADOPTION": ["Chainalysis_Global"],
        }
        config_signal_layers = self.config.get("signal_layers")
        if isinstance(config_signal_layers, dict) and config_signal_layers:
            self.signal_layers = {layer: list(signals) for layer, signals in config_signal_layers.items()}  # type: ignore
        else:
            self.signal_layers = default_signal_layers

        # Data collection settings
        self.lookback_days = self.config.get("lookback_days", 7)
        self.performance_metrics = self.config.get("performance_metrics", ["return", "sharpe", "max_drawdown"])

        # Signal mapping to standardize signal formats
        self.signal_mapping = self._create_signal_mapping()

    def collect_signals(self, signal_data: Dict[str, Any], timestamp: str = None) -> Dict[str, Any]:
        """
        Collect and standardize signals from all layers

        Args:
            signal_data: Raw signal data from various modules
            timestamp: Optional timestamp for the data

        Returns:
            Standardized signal data dictionary
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        standardized_signals = {}

        # Process each signal layer
        for layer_name, signals in self.signal_layers.items():
            layer_data = {}

            for signal_name in signals:
                # Get the raw signal data if available
                raw_signal = signal_data.get(signal_name, {})

                # Standardize the signal format
                std_signal = self._standardize_signal(signal_name, raw_signal)

                # Add to layer data
                layer_data[signal_name] = std_signal

            # Add layer data to results
            standardized_signals[layer_name] = layer_data

        # Add timestamp
        standardized_signals["timestamp"] = timestamp

        return standardized_signals

    def collect_market_data(self, market_data: Dict[str, Any], timestamp: str = None) -> Dict[str, Any]:
        """
        Collect and standardize market data

        Args:
            market_data: Raw market data
            timestamp: Optional timestamp for the data

        Returns:
            Standardized market data dictionary
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # Extract key market features
        price_history = market_data.get("price_history", [])
        volume_history = market_data.get("volume_history", [])

        # Calculate market condition features
        volatility_1d = self._calculate_volatility(price_history, 1)
        volatility_7d = self._calculate_volatility(price_history, 7)
        volatility_30d = self._calculate_volatility(price_history, 30)

        trend_1d = self._calculate_trend(price_history, 1)
        trend_7d = self._calculate_trend(price_history, 7)
        trend_30d = self._calculate_trend(price_history, 30)

        volume_change_1d = self._calculate_volume_change(volume_history, 1)
        volume_change_7d = self._calculate_volume_change(volume_history, 7)

        # Extract technical indicators
        rsi = market_data.get("rsi", 50)
        bb_width = market_data.get("bb_width", 0)

        # Construct standardized market data
        std_market_data = {
            "volatility": {
                "1d": volatility_1d,
                "7d": volatility_7d,
                "30d": volatility_30d,
            },
            "trend": {"1d": trend_1d, "7d": trend_7d, "30d": trend_30d},
            "volume": {"1d": volume_change_1d, "7d": volume_change_7d},
            "technical": {"rsi": rsi, "bb_width": bb_width},
            "timestamp": timestamp,
        }

        return std_market_data

    def store_data(
        self,
        signal_data: Dict[str, Any],
        market_data: Dict[str, Any],
        weights: Dict[str, float] = None,
        performance: Dict[str, float] = None,
    ) -> str:
        """
        Store collected data for future training

        Args:
            signal_data: Standardized signal data
            market_data: Standardized market data
            weights: Optional signal weights
            performance: Optional performance metrics

        Returns:
            Path to stored data file
        """
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        # Get timestamp from signal data or use current time
        timestamp = signal_data.get("timestamp", datetime.now().isoformat())

        # Create filename
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        filename = f"{ts.strftime('%Y-%m-%d_%H-%M-%S')}_signals.json"
        file_path = os.path.join(self.data_dir, filename)

        # Create data record
        data_record = {
            "timestamp": timestamp,
            "signal_data": signal_data,
            "market_data": market_data,
        }

        # Add weights if provided
        if weights:
            data_record["weights"] = weights

        # Add performance if provided
        if performance:
            data_record["performance"] = performance

        # Save to file
        with open(file_path, "w") as f:
            json.dump(data_record, f, indent=2)

        return file_path

    def load_training_data(self, days: int = None) -> List[Dict[str, Any]]:
        """
        Load historical data for training

        Args:
            days: Number of days to look back (defaults to self.lookback_days)

        Returns:
            List of data records for training
        """
        if days is None:
            days = self.lookback_days

        # Calculate the cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # List all data files
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith(".json")]

        # Filter by date
        recent_files = [f for f in data_files if f.split("_")[0] >= cutoff_str]

        # Load data from each file
        training_data = []
        for filename in recent_files:
            try:
                with open(os.path.join(self.data_dir, filename), "r") as f:
                    data = json.load(f)
                    # Only include records with performance data
                    if "performance" in data:
                        training_data.append(data)  # type: ignore
            except Exception as e:
                print(f"Error loading training data from {filename}: {str(e)}")

        print(f"Loaded {len(training_data)} training records from the last {days} days")
        return training_data

    def update_performance(self, timestamp: str, performance_data: Dict[str, float]) -> bool:
        """
        Update a stored data record with actual performance data

        Args:
            timestamp: Timestamp of the record to update
            performance_data: Performance metrics to add

        Returns:
            True if successful, False otherwise
        """
        # Format timestamp for filename
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        filename = f"{ts.strftime('%Y-%m-%d_%H-%M-%S')}_signals.json"
        file_path = os.path.join(self.data_dir, filename)

        # Check if file exists
        if not os.path.exists(file_path):
            print(f"No data record found for timestamp {timestamp}")
            return False

        try:
            # Load existing data
            with open(file_path, "r") as f:
                data = json.load(f)

            # Update with performance data
            data["performance"] = performance_data

            # Save updated data
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            print(f"Error updating performance data: {str(e)}")
            return False

    def _standardize_signal(self, signal_name: str, raw_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize signal format

        Args:
            signal_name: Name of the signal
            raw_signal: Raw signal data

        Returns:
            Standardized signal dictionary
        """
        # Default values
        defaults = {
            "signal": "HOLD",
            "strength": 0.0,
            "confidence": 0.5,
            "direction": 0,
        }

        # Create standardized signal
        std_signal = {
            "signal": raw_signal.get("signal", defaults["signal"]),
            "strength": float(raw_signal.get("strength", defaults["strength"])),  # type: ignore
            "confidence": float(raw_signal.get("confidence", defaults["confidence"])),  # type: ignore
        }

        # Convert signal to direction (-1 = SELL, 0 = HOLD, 1 = BUY)
        signal_str = std_signal["signal"].upper() if isinstance(std_signal["signal"], str) else "HOLD"
        if signal_str == "BUY":
            std_signal["direction"] = 1
        elif signal_str == "SELL":
            std_signal["direction"] = -1
        else:
            std_signal["direction"] = 0

        return std_signal

    def _calculate_volatility(self, price_history: List[Dict[str, Any]], days: int) -> float:
        """Calculate price volatility over specified days"""
        if not price_history or len(price_history) < days:
            return 0.0

        # Extract recent prices
        recent_prices = [p.get("close", 0) for p in price_history[-days:]]

        # Calculate returns
        returns = np.diff(recent_prices) / recent_prices[:-1]

        # Calculate volatility (standard deviation of returns)
        volatility = np.std(returns) if len(returns) > 0 else 0.0

        return float(volatility)  # type: ignore

    def _calculate_trend(self, price_history: List[Dict[str, Any]], days: int) -> float:
        """Calculate price trend over specified days"""
        if not price_history or len(price_history) < days:
            return 0.0

        # Extract recent prices
        recent_prices = [p.get("close", 0) for p in price_history[-days:]]

        # Calculate simple trend (ending price / starting price - 1)
        trend = (recent_prices[-1] / recent_prices[0] - 1) if recent_prices[0] > 0 else 0.0

        return float(trend)  # type: ignore

    def _calculate_volume_change(self, volume_history: List[float], days: int) -> float:
        """Calculate volume change over specified days"""
        if not volume_history or len(volume_history) < days:
            return 0.0

        # Extract recent volumes
        recent_volumes = volume_history[-days:]

        # Calculate volume change
        volume_change = (recent_volumes[-1] / recent_volumes[0] - 1) if recent_volumes[0] > 0 else 0.0

        return float(volume_change)  # type: ignore

    def _create_signal_mapping(self) -> Dict[str, Dict[str, str]]:
        """Create mapping between module-specific signal formats"""
        # This mapping helps normalize different signal formats from various modules
        mapping = {}

        # Add mappings for each signal
        # Example: mapping["RSI"] = {"strength": "rsi_value", "confidence": "rsi_confidence"}

        return mapping


# Test functionality
if __name__ == "__main__":
    # Sample test data
    sample_signals = {
        "RSI": {"signal": "BUY", "strength": 0.8, "confidence": 0.7},
        "MACD": {"signal": "SELL", "strength": -0.6, "confidence": 0.8},
        "Bollinger": {"signal": "HOLD", "strength": 0.1, "confidence": 0.5},
        "Chainalysis_Global": {"signal": "BUY", "strength": 0.9, "confidence": 0.85},
        # Add other signals as needed
    }

    sample_market = {
        "price_history": [
            {
                "time": "2025-09-10T00:00:00",
                "open": 45000,
                "high": 46000,
                "low": 44800,
                "close": 45900,
            },
            {
                "time": "2025-09-11T00:00:00",
                "open": 45900,
                "high": 47000,
                "low": 45500,
                "close": 46800,
            },
            {
                "time": "2025-09-12T00:00:00",
                "open": 46800,
                "high": 48000,
                "low": 46500,
                "close": 47500,
            },
        ],
        "volume_history": [1000, 1200, 900],
        "rsi": 65,
        "bb_width": 0.15,
    }

    # Create collector and test functionality
    collector = SignalDataCollector()

    # Collect and standardize signals
    std_signals = collector.collect_signals(sample_signals)
    print("\nStandardized Signals:")
    for layer, signals in std_signals.items():
        if layer != "timestamp":
            print(f"\n{layer}:")
            for signal, data in signals.items():
                print(f"  {signal}: {data}")

    # Collect and standardize market data
    std_market = collector.collect_market_data(sample_market)
    print("\nStandardized Market Data:")
    for category, data in std_market.items():
        if category != "timestamp":
            print(f"\n{category}:")
            for key, value in data.items():
                print(f"  {key}: {value}")

    # Store the data
    file_path = collector.store_data(
        std_signals,
        std_market,
        weights={"RSI": 0.2, "MACD": 0.1, "Bollinger": 0.15, "Chainalysis_Global": 0.3},
        performance={"return": 0.05, "sharpe": 1.2, "max_drawdown": -0.02},
    )

    print(f"\nData stored at: {file_path}")
