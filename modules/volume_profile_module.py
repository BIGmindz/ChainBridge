"""
Volume Profile Module

This module implements Volume Profile analysis and signal generation, providing
a volume-based signal that is uncorrelated to price-based indicators like RSI, MACD, and Bollinger Bands.
"""

import math
from typing import Any, Dict, List, Tuple

from core.module_manager import Module


class VolumeProfileModule(Module):
    """Volume Profile analysis and signal generation module."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.lookback_periods = config.get("lookback_periods", 50) if config else 50
        self.volume_bins = config.get("volume_bins", 20) if config else 20
        self.poc_threshold = config.get("poc_threshold", 0.3) if config else 0.3  # Point of Control threshold
        self.volume_trend_periods = config.get("volume_trend_periods", 10) if config else 10

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "price_data": "list of price records with OHLCV data",
                "lookback_periods": "integer (optional, default: 50)",
                "volume_bins": "integer (optional, default: 20)",
                "poc_threshold": "float (optional, default: 0.3)",
                "volume_trend_periods": "integer (optional, default: 10)",
            },
            "output": {
                "point_of_control": "float (price level with highest volume)",
                "value_area_high": "float (70% volume area high)",
                "value_area_low": "float (70% volume area low)",
                "volume_profile": "list of volume distribution",
                "current_price_position": "string (ABOVE_POC/BELOW_POC/AT_POC)",
                "volume_trend": "string (INCREASING/DECREASING/STABLE)",
                "signal": "string (BUY/SELL/HOLD)",
                "confidence": "float (0-1)",
                "volume_analysis": {
                    "relative_volume": "float",
                    "volume_breakout": "boolean",
                    "price_volume_divergence": "boolean",
                },
                "metadata": {
                    "lookback_periods_used": "integer",
                    "volume_bins_used": "integer",
                    "data_points": "integer",
                },
            },
        }

    def calculate_volume_profile(
        self, price_data: List[Dict], lookback: int, bins: int
    ) -> Tuple[List[Tuple[float, float, float]], float, float, float]:
        """
        Calculate Volume Profile for the given price data.

        Returns:
            Tuple of (volume_profile, point_of_control, value_area_high, value_area_low)
            where volume_profile is a list of (price_level, volume, percentage)
        """
        if len(price_data) < lookback:
            lookback = len(price_data)

        # Extract relevant data
        recent_data = price_data[-lookback:]

        # Find price range
        all_prices = []
        volumes = []

        for candle in recent_data:
            if isinstance(candle, dict):
                high = float(candle.get("high", candle.get("close", 0)))
                low = float(candle.get("low", candle.get("close", 0)))
                volume = float(candle.get("volume", 1))
            else:  # Assume OHLCV format
                high = float(candle[2])
                low = float(candle[3])
                volume = float(candle[5]) if len(candle) > 5 else 1

            all_prices.extend([high, low])
            volumes.append(volume)

        if not all_prices:
            return [], 0.0, 0.0, 0.0

        price_min = min(all_prices)
        price_max = max(all_prices)

        if price_max == price_min:
            return [(price_min, sum(volumes), 100.0)], price_min, price_min, price_min

        # Create price bins
        price_range = price_max - price_min
        bin_size = price_range / bins

        # Initialize volume profile
        volume_profile = []
        for i in range(bins):
            price_level = price_min + (i + 0.5) * bin_size  # Mid-point of bin
            volume_profile.append([price_level, 0.0, 0.0])

        # Distribute volume across price levels
        total_volume = 0
        for candle in recent_data:
            if isinstance(candle, dict):
                high = float(candle.get("high", candle.get("close", 0)))
                low = float(candle.get("low", candle.get("close", 0)))
                _close = float(candle.get("close", 0))
                volume = float(candle.get("volume", 1))
            else:  # Assume OHLCV format
                high = float(candle[2])
                low = float(candle[3])
                _close = float(candle[4])
                volume = float(candle[5]) if len(candle) > 5 else 1

            total_volume += volume

            # Find which bins this candle's price range covers
            low_bin = max(0, min(bins - 1, int((low - price_min) / bin_size)))
            high_bin = max(0, min(bins - 1, int((high - price_min) / bin_size)))

            # Distribute volume across the bins (weighted by price action)
            bins_covered = max(1, high_bin - low_bin + 1)
            volume_per_bin = volume / bins_covered

            for bin_idx in range(low_bin, high_bin + 1):
                volume_profile[bin_idx][1] += volume_per_bin

        # Calculate percentages and find POC
        max_volume = 0
        point_of_control = price_min

        for i, (price, vol, _) in enumerate(volume_profile):
            percentage = (vol / total_volume * 100) if total_volume > 0 else 0
            volume_profile[i][2] = percentage

            if vol > max_volume:
                max_volume = vol
                point_of_control = price

        # Calculate Value Area (70% of volume around POC)
        volume_profile.sort(key=lambda x: x[1], reverse=True)  # Sort by volume

        cumulative_volume = 0
        value_area_volumes = []
        target_volume = total_volume * 0.7  # 70% value area

        for price, vol, perc in volume_profile:
            cumulative_volume += vol
            value_area_volumes.append((price, vol, perc))
            if cumulative_volume >= target_volume:
                break

        # Find value area high and low
        if value_area_volumes:
            value_area_prices = [item[0] for item in value_area_volumes]
            value_area_high = max(value_area_prices)
            value_area_low = min(value_area_prices)
        else:
            value_area_high = point_of_control
            value_area_low = point_of_control

        # Convert back to tuples for return
        volume_profile_tuples = [(price, vol, perc) for price, vol, perc in volume_profile]

        return volume_profile_tuples, point_of_control, value_area_high, value_area_low

    def analyze_volume_trend(self, volumes: List[float], periods: int) -> str:
        """Analyze volume trend over specified periods."""
        if len(volumes) < periods:
            return "STABLE"

        recent_volumes = volumes[-periods:]
        if len(recent_volumes) < 2:
            return "STABLE"

        # Calculate simple trend using linear regression
        x = list(range(len(recent_volumes)))
        y = recent_volumes

        n = len(recent_volumes)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)

        if n * sum_x2 - sum_x * sum_x == 0:
            return "STABLE"

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

        # Determine trend based on slope relative to average volume
        avg_volume = sum(y) / len(y)
        threshold = avg_volume * 0.05  # 5% threshold

        if slope > threshold:
            return "INCREASING"
        elif slope < -threshold:
            return "DECREASING"
        else:
            return "STABLE"

    def calculate_relative_volume(self, current_volume: float, historical_volumes: List[float]) -> float:
        """Calculate relative volume (current vs average)."""
        if not historical_volumes:
            return 1.0

        avg_volume = sum(historical_volumes) / len(historical_volumes)
        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    def detect_volume_breakout(
        self,
        current_volume: float,
        historical_volumes: List[float],
        multiplier: float = 2.0,
    ) -> bool:
        """Detect if current volume represents a breakout."""
        if not historical_volumes:
            return False

        avg_volume = sum(historical_volumes) / len(historical_volumes)
        return current_volume > (avg_volume * multiplier)

    def detect_price_volume_divergence(self, prices: List[float], volumes: List[float], periods: int = 5) -> bool:
        """Detect divergence between price and volume trends."""
        if len(prices) < periods or len(volumes) < periods:
            return False

        # Calculate price trend
        recent_prices = prices[-periods:]
        price_change = recent_prices[-1] - recent_prices[0]

        # Calculate volume trend
        volume_trend = self.analyze_volume_trend(volumes, periods)

        # Detect divergence
        if price_change > 0 and volume_trend == "DECREASING":
            return True  # Price up but volume down (bearish divergence)
        elif price_change < 0 and volume_trend == "INCREASING":
            return True  # Price down but volume up (bullish divergence)

        return False

    def generate_signal(
        self,
        current_price: float,
        point_of_control: float,
        value_area_high: float,
        value_area_low: float,
        volume_trend: str,
        relative_volume: float,
        volume_breakout: bool,
        price_volume_divergence: bool,
    ) -> Tuple[str, float]:
        """
        Generate trading signal based on Volume Profile analysis.

        Returns:
            Tuple of (signal, confidence)
        """
        signal = "HOLD"
        confidence = 0.0

        # Determine price position relative to POC and Value Area
        poc_distance = abs(current_price - point_of_control) / point_of_control

        # 1. POC and Value Area Analysis
        if current_price < value_area_low:
            # Price below value area - potential buy opportunity
            if volume_trend == "INCREASING" or volume_breakout:
                signal = "BUY"
                confidence = min(0.8, 0.4 + (relative_volume - 1.0) * 0.4)

        elif current_price > value_area_high:
            # Price above value area - potential sell opportunity
            if volume_trend == "INCREASING" or volume_breakout:
                signal = "SELL"
                confidence = min(0.8, 0.4 + (relative_volume - 1.0) * 0.4)

        # 2. POC Rejection/Acceptance
        elif poc_distance < 0.01:  # Very close to POC (within 1%)
            if volume_breakout and relative_volume > 1.5:
                # High volume at POC could indicate breakout
                if current_price > point_of_control:
                    signal = "BUY"
                else:
                    signal = "SELL"
                confidence = min(0.7, relative_volume * 0.3)

        # 3. Volume Breakout Confirmation
        if volume_breakout and relative_volume > 2.0:
            # Significant volume breakout
            if current_price > point_of_control:
                signal = "BUY" if signal != "SELL" else signal
                confidence = max(confidence, min(0.9, relative_volume * 0.2))
            elif current_price < point_of_control:
                signal = "SELL" if signal != "BUY" else signal
                confidence = max(confidence, min(0.9, relative_volume * 0.2))

        # 4. Price-Volume Divergence
        if price_volume_divergence:
            # Adjust signal confidence based on divergence
            if signal == "BUY":
                confidence = max(0.6, confidence)  # Increase buy confidence on bullish divergence
            elif signal == "SELL":
                confidence = max(0.6, confidence)  # Increase sell confidence on bearish divergence
            else:
                # No existing signal, but divergence suggests potential reversal
                if current_price < point_of_control:
                    signal = "BUY"
                    confidence = 0.5
                elif current_price > point_of_control:
                    signal = "SELL"
                    confidence = 0.5

        # 5. Volume Trend Confirmation
        if signal != "HOLD":
            if volume_trend == "INCREASING":
                confidence = min(1.0, confidence * 1.2)  # Boost confidence
            elif volume_trend == "DECREASING":
                confidence = max(0.1, confidence * 0.8)  # Reduce confidence

        return signal, max(0.0, min(1.0, confidence))

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process price and volume data and generate Volume Profile signals."""
        price_data = data.get("price_data", [])
        if not price_data:
            raise ValueError("price_data is required")

        # Extract configuration
        lookback_periods = data.get("lookback_periods", self.lookback_periods)
        volume_bins = data.get("volume_bins", self.volume_bins)
        poc_threshold = data.get("poc_threshold", self.poc_threshold)
        volume_trend_periods = data.get("volume_trend_periods", self.volume_trend_periods)

        try:
            # Validate data format and extract OHLCV
            if not price_data:
                raise ValueError("No price data provided")

            # Check if we have volume data
            has_volume = False
            if isinstance(price_data[0], dict):
                has_volume = "volume" in price_data[0]
            elif isinstance(price_data[0], (list, tuple)):
                has_volume = len(price_data[0]) > 5

            if not has_volume:
                # If no volume data, use uniform volume (less effective but still functional)
                for i, record in enumerate(price_data):
                    if isinstance(record, dict):
                        price_data[i]["volume"] = 1000  # Default volume
                    elif isinstance(record, (list, tuple)):
                        price_data[i] = list(record) + [1000]  # Add default volume

            # Need sufficient data
            min_periods = max(lookback_periods, 20)
            if len(price_data) < min_periods:
                return {
                    "point_of_control": float("nan"),
                    "value_area_high": float("nan"),
                    "value_area_low": float("nan"),
                    "volume_profile": [],
                    "current_price_position": "UNKNOWN",
                    "volume_trend": "STABLE",
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "volume_analysis": {
                        "relative_volume": 1.0,
                        "volume_breakout": False,
                        "price_volume_divergence": False,
                    },
                    "current_price": float("nan"),
                    "metadata": {
                        "lookback_periods_used": lookback_periods,
                        "volume_bins_used": volume_bins,
                        "data_points": len(price_data),
                        "min_required": min_periods,
                        "error": "Insufficient data points for Volume Profile calculation",
                    },
                }

            # Calculate Volume Profile
            volume_profile, poc, value_area_high, value_area_low = self.calculate_volume_profile(price_data, lookback_periods, volume_bins)

            # Get current price and volume
            if isinstance(price_data[-1], dict):
                current_price = float(price_data[-1].get("close", price_data[-1].get("price", 0)))
                current_volume = float(price_data[-1].get("volume", 1))
            else:
                current_price = float(price_data[-1][4])  # Close price
                current_volume = float(price_data[-1][5]) if len(price_data[-1]) > 5 else 1

            # Extract historical data for analysis
            historical_prices = []
            historical_volumes = []

            for record in price_data:
                if isinstance(record, dict):
                    historical_prices.append(float(record.get("close", record.get("price", 0))))
                    historical_volumes.append(float(record.get("volume", 1)))
                else:
                    historical_prices.append(float(record[4]))
                    historical_volumes.append(float(record[5]) if len(record) > 5 else 1)

            # Analyze volume characteristics
            volume_trend = self.analyze_volume_trend(historical_volumes, volume_trend_periods)
            relative_volume = self.calculate_relative_volume(current_volume, historical_volumes[:-1])
            volume_breakout = self.detect_volume_breakout(current_volume, historical_volumes[:-1])
            price_volume_divergence = self.detect_price_volume_divergence(historical_prices, historical_volumes, volume_trend_periods)

            # Determine price position relative to POC
            if abs(current_price - poc) / poc < poc_threshold:
                price_position = "AT_POC"
            elif current_price > poc:
                price_position = "ABOVE_POC"
            else:
                price_position = "BELOW_POC"

            # Generate signal
            signal, confidence = self.generate_signal(
                current_price,
                poc,
                value_area_high,
                value_area_low,
                volume_trend,
                relative_volume,
                volume_breakout,
                price_volume_divergence,
            )

            result = {
                "point_of_control": poc,
                "value_area_high": value_area_high,
                "value_area_low": value_area_low,
                "volume_profile": [
                    {"price_level": price, "volume": vol, "percentage": perc} for price, vol, perc in volume_profile[:10]  # Top 10 levels
                ],
                "current_price_position": price_position,
                "volume_trend": volume_trend,
                "signal": signal,
                "confidence": confidence,
                "current_price": current_price,
                "current_volume": current_volume,
                "volume_analysis": {
                    "relative_volume": relative_volume,
                    "volume_breakout": volume_breakout,
                    "price_volume_divergence": price_volume_divergence,
                    "volume_above_average": relative_volume > 1.0,
                    "high_volume_threshold": relative_volume > 1.5,
                },
                "support_resistance": {
                    "poc_support_resistance": poc,
                    "value_area_support": value_area_low,
                    "value_area_resistance": value_area_high,
                    "price_in_value_area": value_area_low <= current_price <= value_area_high,
                },
                "metadata": {
                    "lookback_periods_used": lookback_periods,
                    "volume_bins_used": volume_bins,
                    "volume_trend_periods_used": volume_trend_periods,
                    "data_points": len(price_data),
                    "has_volume_data": has_volume,
                    "module_info": {
                        "name": self.name,
                        "version": self.version,
                        "signal_type": "volume_indicator",
                    },
                },
            }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process Volume Profile calculation: {str(e)}")

    def backtest_strategy(self, historical_data: List[Dict[str, Any]], initial_balance: float = 10000) -> Dict[str, Any]:
        """Simple backtesting functionality for Volume Profile strategy."""
        if not historical_data:
            raise ValueError("Historical data is required for backtesting")

        balance = initial_balance
        position = 0
        trades = []
        signals_history = []

        min_periods = max(self.lookback_periods, 20)

        for i in range(min_periods, len(historical_data)):
            window_data = historical_data[: i + 1]
            result = self.process({"price_data": window_data})

            if math.isnan(result["point_of_control"]):
                continue

            signal = result["signal"]
            price = result["current_price"]
            confidence = result["confidence"]

            signals_history.append(
                {
                    "date": i,
                    "price": price,
                    "volume": result["current_volume"],
                    "poc": result["point_of_control"],
                    "relative_volume": result["volume_analysis"]["relative_volume"],
                    "signal": signal,
                    "confidence": confidence,
                    "volume_trend": result["volume_trend"],
                }
            )

            # Trade on medium to high confidence signals
            if confidence >= 0.5:
                if signal == "BUY" and position == 0:
                    position = balance / price
                    balance = 0
                    trades.append(
                        {
                            "type": "BUY",
                            "price": price,
                            "volume": result["current_volume"],
                            "relative_volume": result["volume_analysis"]["relative_volume"],
                            "confidence": confidence,
                            "position": position,
                        }
                    )
                elif signal == "SELL" and position > 0:
                    balance = position * price
                    pnl = balance - initial_balance
                    trades.append(
                        {
                            "type": "SELL",
                            "price": price,
                            "volume": result["current_volume"],
                            "relative_volume": result["volume_analysis"]["relative_volume"],
                            "confidence": confidence,
                            "pnl": pnl,
                        }
                    )
                    position = 0

        # Calculate final portfolio value
        final_price = historical_data[-1]["close"] if "close" in historical_data[-1] else historical_data[-1]["price"]
        final_value = balance + (position * final_price)

        return {
            "initial_balance": initial_balance,
            "final_value": final_value,
            "total_return": final_value - initial_balance,
            "return_percentage": ((final_value - initial_balance) / initial_balance) * 100,
            "total_trades": len(trades),
            "total_signals": len(signals_history),
            "volume_breakout_trades": len([t for t in trades if t.get("relative_volume", 1) > 1.5]),
            "high_confidence_trades": len([t for t in trades if t.get("confidence", 0) > 0.7]),
            "signal_accuracy": self._calculate_signal_accuracy(signals_history),
            "trades": trades,
            "signals_history": signals_history[-10:],  # Last 10 signals for inspection
        }

    def _calculate_signal_accuracy(self, signals_history: List[Dict]) -> float:
        """Calculate the accuracy of signals based on price movement after signal."""
        if len(signals_history) < 2:
            return 0.0

        correct_signals = 0
        total_actionable_signals = 0

        for i in range(len(signals_history) - 1):
            current_signal = signals_history[i]
            next_signal = signals_history[i + 1]

            if current_signal["signal"] in ["BUY", "SELL"]:
                total_actionable_signals += 1
                price_change = next_signal["price"] - current_signal["price"]

                if current_signal["signal"] == "BUY" and price_change > 0:
                    correct_signals += 1
                elif current_signal["signal"] == "SELL" and price_change < 0:
                    correct_signals += 1

        return correct_signals / total_actionable_signals if total_actionable_signals > 0 else 0.0
