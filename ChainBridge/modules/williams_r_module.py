"""
Williams %R Module

Momentum oscillator measuring overbought/oversold levels using price range.
"""

from typing import Any, Dict, List
import pandas as pd

from core.module_manager import Module


class WilliamsRModule(Module):
    """Williams %R momentum oscillator module."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        config = config or {}
        self.period = config.get("period", 14)
        self.overbought_threshold = config.get("overbought_threshold", -20)
        self.oversold_threshold = config.get("oversold_threshold", -80)
        self.strong_overbought = config.get("strong_overbought", -10)
        self.strong_oversold = config.get("strong_oversold", -90)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "ohlcv_data": "List of OHLCV candles [ts, open, high, low, close, volume]"
            },
            "output": {
                "williams_r_value": "Latest Williams %R reading (-100 to 0)",
                "signal": "BUY/SELL/HOLD decision",
                "signal_strength": "STRONG/NEUTRAL",
                "market_condition": "OVERBOUGHT/OVERSOLD/NEUTRAL",
                "confidence": "Signal confidence 0-1",
                "trend_divergence": "NO/BULLISH/BEARISH divergence",
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ohlcv = data.get("ohlcv_data", [])
        if len(ohlcv) < self.period:
            return self._insufficient_data_response()

        df = self._ohlcv_to_dataframe(ohlcv)
        williams_series = self._calculate_williams_r(df)
        if williams_series.empty:
            return self._insufficient_data_response()

        value = float(williams_series.iloc[-1])
        signal = self._generate_signal(value)
        confidence = self._calculate_confidence(value)
        divergence = self._detect_divergence(df, williams_series)

        return {
            "williams_r_value": round(value, 2),
            "signal": signal,
            "signal_strength": self._get_signal_strength(value),
            "market_condition": self._get_market_condition(value),
            "confidence": round(confidence, 3),
            "trend_divergence": divergence,
            "metadata": {"period": self.period, "module_version": self.VERSION},
        }

    def _ohlcv_to_dataframe(self, ohlcv: List[List[Any]]) -> pd.DataFrame:
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        return df.astype(
            {
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,
            }
        )

    def _calculate_williams_r(self, df: pd.DataFrame) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        highest_high = high.rolling(self.period).max()
        lowest_low = low.rolling(self.period).min()
        return ((highest_high - close) / (highest_high - lowest_low)) * -100

    def _generate_signal(self, value: float) -> str:
        if value <= self.oversold_threshold:
            return "BUY"
        if value >= self.overbought_threshold:
            return "SELL"
        return "HOLD"

    def _get_signal_strength(self, value: float) -> str:
        if value <= self.strong_oversold or value >= self.strong_overbought:
            return "STRONG"
        return "NEUTRAL"

    def _get_market_condition(self, value: float) -> str:
        if value >= self.overbought_threshold:
            return "OVERBOUGHT"
        if value <= self.oversold_threshold:
            return "OVERSOLD"
        return "NEUTRAL"

    def _calculate_confidence(self, value: float) -> float:
        if value >= self.overbought_threshold:
            distance = abs(value - self.overbought_threshold)
            max_distance = abs(0 - self.overbought_threshold)
        elif value <= self.oversold_threshold:
            distance = abs(value - self.oversold_threshold)
            max_distance = abs(-100 - self.oversold_threshold)
        else:
            return 0.3
        return min(1.0, distance / max_distance)

    def _detect_divergence(self, df: pd.DataFrame, wr: pd.Series) -> str:
        if len(df) < self.period * 2:
            return "INSUFFICIENT_DATA"
        prices = df["close"].tail(self.period)
        wr_recent = wr.tail(self.period)
        price_trend = prices.iloc[-1] - prices.iloc[0]
        wr_trend = wr_recent.iloc[-1] - wr_recent.iloc[0]
        if price_trend > 0 and wr_trend < 0:
            return "BEARISH_DIVERGENCE"
        if price_trend < 0 and wr_trend > 0:
            return "BULLISH_DIVERGENCE"
        return "NO_DIVERGENCE"

    def _insufficient_data_response(self) -> Dict[str, Any]:
        return {
            "williams_r_value": None,
            "signal": "HOLD",
            "signal_strength": "NEUTRAL",
            "market_condition": "UNKNOWN",
            "confidence": 0.0,
            "trend_divergence": "INSUFFICIENT_DATA",
            "error": f"Need at least {self.period} candles",
        }

    def get_required_history(self) -> int:
        return self.period + 5

    def validate_config(self) -> bool:
        return -100 <= self.oversold_threshold < self.overbought_threshold <= 0
