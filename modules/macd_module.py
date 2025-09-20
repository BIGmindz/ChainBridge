"""
MACD (Moving Average Convergence Divergence) Module

This module implements MACD calculation and signal generation, providing
a momentum-based signal that is uncorrelated to RSI.
"""

import math
from typing import Any, Dict, List, Tuple

import pandas as pd

from core.module_manager import Module


class MACDModule(Module):
    """MACD (Moving Average Convergence Divergence) calculation and signal generation module."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.fast_period = config.get("fast_period", 12) if config else 12
        self.slow_period = config.get("slow_period", 26) if config else 26
        self.signal_period = config.get("signal_period", 9) if config else 9

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "price_data": "list of price records with close prices",
                "fast_period": "integer (optional, default: 12)",
                "slow_period": "integer (optional, default: 26)",
                "signal_period": "integer (optional, default: 9)",
            },
            "output": {
                "macd_line": "float",
                "signal_line": "float",
                "histogram": "float",
                "signal": "string (BUY/SELL/HOLD)",
                "confidence": "float (0-1)",
                "signal_strength": "string (WEAK/MODERATE/STRONG)",
                "metadata": {
                    "fast_period_used": "integer",
                    "slow_period_used": "integer",
                    "signal_period_used": "integer",
                    "data_points": "integer",
                },
            },
        }

    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return prices.ewm(span=period, adjust=False).mean()

    def calculate_macd(
        self, prices: pd.Series, fast_period: int, slow_period: int, signal_period: int
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD, Signal Line, and Histogram.

        Returns:
            Tuple of (MACD Line, Signal Line, Histogram)
        """
        # Calculate EMAs
        ema_fast = self.calculate_ema(prices, fast_period)
        ema_slow = self.calculate_ema(prices, slow_period)

        # MACD Line = EMA(fast) - EMA(slow)
        macd_line = ema_fast - ema_slow

        # Signal Line = EMA of MACD Line
        signal_line = self.calculate_ema(macd_line, signal_period)

        # Histogram = MACD Line - Signal Line
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def generate_signal(
        self,
        macd_current: float,
        signal_current: float,
        histogram_current: float,
        macd_prev: float,
        signal_prev: float,
        histogram_prev: float,
    ) -> Tuple[str, float, str]:
        """
        Generate trading signal based on MACD analysis.

        Returns:
            Tuple of (signal, confidence, strength)
        """
        if any(math.isnan(x) for x in [macd_current, signal_current, histogram_current]):
            return "HOLD", 0.0, "WEAK"

        signal = "HOLD"
        confidence = 0.0
        strength = "WEAK"

        # MACD Crossover Signals
        if macd_current > signal_current and macd_prev <= signal_prev:
            # Bullish crossover: MACD crosses above signal line
            signal = "BUY"
            confidence = min(1.0, abs(macd_current - signal_current) / max(abs(macd_current), 0.01))

        elif macd_current < signal_current and macd_prev >= signal_prev:
            # Bearish crossover: MACD crosses below signal line
            signal = "SELL"
            confidence = min(1.0, abs(signal_current - macd_current) / max(abs(signal_current), 0.01))

        # Zero Line Crossover (additional confirmation)
        elif macd_current > 0 and macd_prev <= 0:
            # Bullish momentum: MACD crosses above zero line
            if signal == "HOLD":
                signal = "BUY"
                confidence = min(0.7, abs(macd_current) / max(abs(macd_current), 0.01))

        elif macd_current < 0 and macd_prev >= 0:
            # Bearish momentum: MACD crosses below zero line
            if signal == "HOLD":
                signal = "SELL"
                confidence = min(0.7, abs(macd_current) / max(abs(macd_current), 0.01))

        # Histogram Analysis (momentum strength)
        if abs(histogram_current) > abs(histogram_prev):
            if confidence > 0:
                confidence = min(1.0, confidence * 1.2)  # Increase confidence for strengthening momentum

        # Determine signal strength based on multiple factors
        histogram_strength = abs(histogram_current)
        macd_magnitude = abs(macd_current)

        if confidence >= 0.7 and histogram_strength > macd_magnitude * 0.3:
            strength = "STRONG"
        elif confidence >= 0.4 and histogram_strength > macd_magnitude * 0.1:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        return signal, confidence, strength

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process price data and generate MACD signals."""
        price_data = data.get("price_data", [])
        if not price_data:
            raise ValueError("price_data is required")

        # Extract configuration
        fast_period = data.get("fast_period", self.fast_period)
        slow_period = data.get("slow_period", self.slow_period)
        signal_period = data.get("signal_period", self.signal_period)

        # Validate periods
        if slow_period <= fast_period:
            raise ValueError("slow_period must be greater than fast_period")

        try:
            # Extract close prices from price data
            if isinstance(price_data[0], dict):
                closes = []
                for record in price_data:
                    if "close" in record:
                        closes.append(float(record["close"]))
                    elif "price" in record:
                        closes.append(float(record["price"]))
                    else:
                        raise ValueError("No 'close' or 'price' field found in price data")
            elif isinstance(price_data[0], (list, tuple)):
                # Data is in OHLCV format - use close price (index 4)
                closes = [float(row[4]) for row in price_data if len(row) >= 5]
            else:
                # Assume it's a list of close prices
                closes = [float(price) for price in price_data]

            # Need enough data for MACD calculation
            min_periods = max(slow_period + signal_period, 34)  # Conservative minimum
            if len(closes) < min_periods:
                return {
                    "macd_line": float("nan"),
                    "signal_line": float("nan"),
                    "histogram": float("nan"),
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "signal_strength": "WEAK",
                    "current_price": closes[-1] if closes else float("nan"),
                    "metadata": {
                        "fast_period_used": fast_period,
                        "slow_period_used": slow_period,
                        "signal_period_used": signal_period,
                        "data_points": len(closes),
                        "min_required": min_periods,
                        "error": "Insufficient data points for MACD calculation",
                    },
                }

            # Calculate MACD
            close_series = pd.Series(closes, dtype=float)
            macd_line, signal_line, histogram = self.calculate_macd(close_series, fast_period, slow_period, signal_period)

            # Get current and previous values for signal generation
            macd_current = float(macd_line.iloc[-1])
            signal_current = float(signal_line.iloc[-1])
            histogram_current = float(histogram.iloc[-1])

            # Get previous values (if available)
            if len(macd_line) >= 2:
                macd_prev = float(macd_line.iloc[-2])
                signal_prev = float(signal_line.iloc[-2])
                histogram_prev = float(histogram.iloc[-2])
            else:
                macd_prev = macd_current
                signal_prev = signal_current
                histogram_prev = histogram_current

            # Generate signal and confidence
            signal, confidence, strength = self.generate_signal(
                macd_current,
                signal_current,
                histogram_current,
                macd_prev,
                signal_prev,
                histogram_prev,
            )

            result = {
                "macd_line": macd_current,
                "signal_line": signal_current,
                "histogram": histogram_current,
                "signal": signal,
                "confidence": confidence,
                "signal_strength": strength,
                "current_price": closes[-1],
                "trend_analysis": {
                    "macd_above_signal": macd_current > signal_current,
                    "macd_above_zero": macd_current > 0,
                    "histogram_increasing": (histogram_current > histogram_prev if len(histogram) >= 2 else False),
                    "momentum_direction": ("BULLISH" if macd_current > signal_current else "BEARISH"),
                },
                "metadata": {
                    "fast_period_used": fast_period,
                    "slow_period_used": slow_period,
                    "signal_period_used": signal_period,
                    "data_points": len(closes),
                    "calculation_window": min_periods,
                    "module_info": {
                        "name": self.name,
                        "version": self.version,
                        "signal_type": "momentum_indicator",
                    },
                },
            }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process MACD calculation: {str(e)}")

    def backtest_strategy(self, historical_data: List[Dict[str, Any]], initial_balance: float = 10000) -> Dict[str, Any]:
        """Simple backtesting functionality for MACD strategy."""
        if not historical_data:
            raise ValueError("Historical data is required for backtesting")

        balance = initial_balance
        position = 0
        trades = []
        signals_history = []

        for i in range(max(34, self.slow_period + self.signal_period), len(historical_data)):
            # Use sufficient lookback window for MACD calculation
            window_data = historical_data[: i + 1]
            result = self.process({"price_data": window_data})

            if math.isnan(result["macd_line"]):
                continue

            signal = result["signal"]
            price = result["current_price"]
            confidence = result["confidence"]

            signals_history.append(
                {
                    "date": i,
                    "price": price,
                    "macd_line": result["macd_line"],
                    "signal_line": result["signal_line"],
                    "histogram": result["histogram"],
                    "signal": signal,
                    "confidence": confidence,
                }
            )

            # Only trade on high confidence signals
            if confidence >= 0.5:
                if signal == "BUY" and position == 0:
                    # Buy signal - enter position
                    position = balance / price
                    balance = 0
                    trades.append(
                        {
                            "type": "BUY",
                            "price": price,
                            "macd": result["macd_line"],
                            "signal_line": result["signal_line"],
                            "confidence": confidence,
                            "position": position,
                        }
                    )
                elif signal == "SELL" and position > 0:
                    # Sell signal - exit position
                    balance = position * price
                    pnl = balance - initial_balance
                    trades.append(
                        {
                            "type": "SELL",
                            "price": price,
                            "macd": result["macd_line"],
                            "signal_line": result["signal_line"],
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
