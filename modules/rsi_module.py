"""
RSI Module

This module integrates the existing RSI functionality from benson_rsi_bot.py
into the modular architecture.
"""

import math
from typing import Any, Dict, List

import pandas as pd

from core.module_manager import Module


class RSIModule(Module):
    """RSI (Relative Strength Index) calculation and signal generation module."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.default_period = config.get("period", 14) if config else 14
        self.buy_threshold = config.get("buy_threshold", 30) if config else 30
        self.sell_threshold = config.get("sell_threshold", 70) if config else 70

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "price_data": "list of price records with close prices",
                "period": "integer (optional, default: 14)",
                "buy_threshold": "float (optional, default: 30)",
                "sell_threshold": "float (optional, default: 70)",
            },
            "output": {
                "rsi_value": "float",
                "signal": "string (BUY/SELL/HOLD)",
                "confidence": "float (0-1)",
                "metadata": {
                    "period_used": "integer",
                    "data_points": "integer",
                    "thresholds": "dict",
                },
            },
        }

    def wilder_rsi(self, close: pd.Series, period: int = 14) -> float:
        """
        Calculate Wilder's RSI using EMA smoothing.
        This is the same implementation from benson_rsi_bot.py
        """
        if len(close) < period + 5:
            return float("nan")

        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

        if avg_loss.iloc[-1] == 0:
            return 100.0

        rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
        return 100 - (100 / (1 + rs))

    def generate_signal(
        self, rsi_value: float, buy_threshold: float, sell_threshold: float
    ) -> tuple:
        """Generate trading signal and confidence based on RSI value."""
        if math.isnan(rsi_value):
            return "HOLD", 0.0

        if rsi_value <= buy_threshold:
            # Calculate confidence based on how far below buy threshold
            confidence = min(1.0, (buy_threshold - rsi_value) / buy_threshold)
            return "BUY", confidence
        elif rsi_value >= sell_threshold:
            # Calculate confidence based on how far above sell threshold
            confidence = min(1.0, (rsi_value - sell_threshold) / (100 - sell_threshold))
            return "SELL", confidence
        else:
            return "HOLD", 0.0

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process price data and generate RSI signals."""
        price_data = data.get("price_data", [])
        if not price_data:
            raise ValueError("price_data is required")

        # Extract configuration
        period = data.get("period", self.default_period)
        buy_threshold = data.get("buy_threshold", self.buy_threshold)
        sell_threshold = data.get("sell_threshold", self.sell_threshold)

        try:
            # Extract close prices from price data
            if isinstance(price_data[0], dict):
                # Data is in dictionary format
                closes = []
                for record in price_data:
                    if "close" in record:
                        closes.append(float(record["close"]))
                    elif "price" in record:
                        closes.append(float(record["price"]))
                    else:
                        raise ValueError(
                            "No 'close' or 'price' field found in price data"
                        )
            elif isinstance(price_data[0], (list, tuple)):
                # Data is in OHLCV format - use close price (index 4)
                closes = [float(row[4]) for row in price_data if len(row) >= 5]
            else:
                # Assume it's a list of close prices
                closes = [float(price) for price in price_data]

            if len(closes) < period + 5:
                return {
                    "rsi_value": float("nan"),
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "metadata": {
                        "period_used": period,
                        "data_points": len(closes),
                        "thresholds": {"buy": buy_threshold, "sell": sell_threshold},
                        "error": "Insufficient data points for RSI calculation",
                    },
                }

            # Calculate RSI
            close_series = pd.Series(closes, dtype=float)
            rsi_value = self.wilder_rsi(close_series, period)

            # Generate signal and confidence
            signal, confidence = self.generate_signal(
                rsi_value, buy_threshold, sell_threshold
            )

            result = {
                "rsi_value": rsi_value,
                "signal": signal,
                "confidence": confidence,
                "current_price": closes[-1],
                "metadata": {
                    "period_used": period,
                    "data_points": len(closes),
                    "thresholds": {"buy": buy_threshold, "sell": sell_threshold},
                    "module_info": {"name": self.name, "version": self.version},
                },
            }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process RSI calculation: {str(e)}")

    def backtest_strategy(
        self, historical_data: List[Dict[str, Any]], initial_balance: float = 10000
    ) -> Dict[str, Any]:
        """Simple backtesting functionality for RSI strategy."""
        if not historical_data:
            raise ValueError("Historical data is required for backtesting")

        balance = initial_balance
        position = 0
        trades = []

        for i, data_point in enumerate(historical_data):
            result = self.process({"price_data": historical_data[: i + 1]})

            if math.isnan(result["rsi_value"]):
                continue

            signal = result["signal"]
            price = result["current_price"]

            if signal == "BUY" and position == 0:
                # Buy signal - enter position
                position = balance / price
                balance = 0
                trades.append(
                    {
                        "type": "BUY",
                        "price": price,
                        "rsi": result["rsi_value"],
                        "confidence": result["confidence"],
                        "position": position,
                    }
                )
            elif signal == "SELL" and position > 0:
                # Sell signal - exit position
                balance = position * price
                trades.append(
                    {
                        "type": "SELL",
                        "price": price,
                        "rsi": result["rsi_value"],
                        "confidence": result["confidence"],
                        "pnl": balance - initial_balance,
                    }
                )
                position = 0

        # Calculate final portfolio value
        final_price = (
            historical_data[-1]["close"]
            if "close" in historical_data[-1]
            else historical_data[-1]["price"]
        )
        final_value = balance + (position * final_price)

        return {
            "initial_balance": initial_balance,
            "final_value": final_value,
            "total_return": final_value - initial_balance,
            "return_percentage": ((final_value - initial_balance) / initial_balance)
            * 100,
            "total_trades": len(trades),
            "trades": trades,
        }
