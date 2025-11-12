"""Fibonacci Retracement Signal Module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from core.module_manager import Module


@dataclass
class FibonacciConfig:
    lookback_period: int = 120  # number of candles to evaluate for swing points
    tolerance_pct: float = 0.25  # percent distance to consider "touching" a level
    min_range_pct: float = 1.0  # minimum % range to consider the structure meaningful


class FibonacciRetracementModule(Module):
    """Generates signals based on Fibonacci retracement levels."""

    VERSION = "1.0.0"
    RATIOS: Tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        cfg = config or {}
        self.config = FibonacciConfig(
            lookback_period=cfg.get("lookback_period", 120),
            tolerance_pct=cfg.get("tolerance_pct", 0.25),
            min_range_pct=cfg.get("min_range_pct", 1.0),
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {"ohlcv_data": "List of OHLCV candles [ts, open, high, low, close, volume]"},
            "output": {
                "trend": "UPTREND/DOWNTREND/NEUTRAL",
                "levels": "Dict of retracement levels and prices",
                "nearest_level": "Closest Fibonacci level to current price",
                "signal": "BUY/SELL/HOLD based on interaction with level",
                "confidence": "Signal confidence 0-1",
                "structure_range_pct": "Percent range between swing high/low",
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        candles = data.get("ohlcv_data", [])
        if not candles or len(candles) < self.config.lookback_period:
            return self._insufficient_data()

        df = self._to_dataframe(candles)
        window = df.tail(self.config.lookback_period).copy()
        swing_high = float(window["high"].max())
        swing_low = float(window["low"].min())
        current_price = float(window["close"].iloc[-1])

        price_range = swing_high - swing_low
        if price_range <= 0:
            return self._insufficient_data(reason="Invalid price range")

        structure_range_pct = (price_range / swing_low) * 100 if swing_low else 0
        if structure_range_pct < self.config.min_range_pct:
            return self._insufficient_data(reason="Range too small for reliable levels")

        trend = "UPTREND" if current_price >= window["close"].iloc[0] else "DOWNTREND"
        levels = self._compute_levels(swing_high, swing_low, trend)
        nearest_level, distance_pct = self._find_nearest_level(current_price, levels)

        signal = self._generate_signal(current_price, nearest_level, trend, distance_pct)
        confidence = self._confidence(distance_pct, structure_range_pct)

        return {
            "trend": trend,
            "levels": levels,
            "nearest_level": {
                "level": nearest_level[0],
                "price": round(nearest_level[1], 2),
                "distance_pct": round(distance_pct, 3),
            },
            "current_price": round(current_price, 2),
            "swing_high": round(swing_high, 2),
            "swing_low": round(swing_low, 2),
            "structure_range_pct": round(structure_range_pct, 2),
            "signal": signal,
            "confidence": round(confidence, 3),
            "metadata": {
                "module_version": self.VERSION,
                "lookback_period": self.config.lookback_period,
            },
        }

    def _to_dataframe(self, candles: List[List[Any]]) -> pd.DataFrame:
        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        return df.astype(
            {
                "timestamp": int,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,
            }
        )

    def _compute_levels(self, swing_high: float, swing_low: float, trend: str) -> Dict[str, float]:
        price_range = swing_high - swing_low
        levels: Dict[str, float] = {}

        if trend == "UPTREND":
            for ratio in self.RATIOS:
                level_price = swing_high - price_range * ratio
                levels[f"{int(ratio * 100)}%"] = round(level_price, 2)
            levels["0% (High)"] = round(swing_high, 2)
            levels["100% (Low)"] = round(swing_low, 2)
        else:
            for ratio in self.RATIOS:
                level_price = swing_low + price_range * ratio
                levels[f"{int(ratio * 100)}%"] = round(level_price, 2)
            levels["0% (Low)"] = round(swing_low, 2)
            levels["100% (High)"] = round(swing_high, 2)
        return levels

    def _find_nearest_level(self, price: float, levels: Dict[str, float]) -> Tuple[Tuple[str, float], float]:
        closest_level = min(levels.items(), key=lambda item: abs(price - item[1]))
        distance_pct = abs(price - closest_level[1]) / closest_level[1] * 100 if closest_level[1] else np.inf
        return closest_level, distance_pct

    def _generate_signal(self, price: float, nearest: Tuple[str, float], trend: str, distance_pct: float) -> str:
        tolerance = self.config.tolerance_pct
        level_price = nearest[1]

        if distance_pct <= tolerance:
            if trend == "UPTREND":
                # Buying interest near key support levels
                if price <= level_price and "100%" not in nearest[0]:
                    return "BUY"
                return "HOLD"
            if trend == "DOWNTREND":
                if price >= level_price and "100%" not in nearest[0]:
                    return "SELL"
                return "HOLD"
        return "HOLD"

    def _confidence(self, distance_pct: float, structure_range_pct: float) -> float:
        if distance_pct == np.inf:
            return 0.0
        proximity_score = max(0.0, 1 - (distance_pct / (self.config.tolerance_pct * 2)))
        structure_score = min(1.0, structure_range_pct / (self.config.min_range_pct * 3))
        return max(0.1, (proximity_score * 0.6 + structure_score * 0.4))

    def _insufficient_data(self, reason: str | None = None) -> Dict[str, Any]:
        return {
            "trend": "NEUTRAL",
            "levels": {},
            "nearest_level": None,
            "current_price": None,
            "swing_high": None,
            "swing_low": None,
            "structure_range_pct": 0.0,
            "signal": "HOLD",
            "confidence": 0.0,
            "error": reason or "Insufficient data for Fibonacci analysis",
        }

    def get_required_history(self) -> int:
        return self.config.lookback_period

    def validate_config(self) -> bool:
        return self.config.lookback_period >= 50 and 0 < self.config.tolerance_pct <= 1
