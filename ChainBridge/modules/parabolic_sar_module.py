"""Parabolic SAR Signal Module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from core.module_manager import Module


@dataclass
class ParabolicSARConfig:
    step: float = 0.02
    max_step: float = 0.2
    min_candles: int = 30


class ParabolicSARModule(Module):
    """Generates stop-and-reverse signals using Parabolic SAR."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        cfg = config or {}
        self.config = ParabolicSARConfig(
            step=cfg.get("step", 0.02),
            max_step=cfg.get("max_step", 0.2),
            min_candles=cfg.get("min_candles", 30),
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {"ohlcv_data": "List of OHLCV candles"},
            "output": {
                "psar": "Latest Parabolic SAR value",
                "trend": "BULLISH/BEARISH",
                "signal": "BUY/SELL/HOLD",
                "confidence": "Signal confidence 0-1",
                "acceleration_factor": "Current acceleration factor",
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        candles = data.get("ohlcv_data", [])
        if len(candles) < self.config.min_candles:
            return self._insufficient_data()

        df = self._to_dataframe(candles)
        psar_series, trend_series, af_series = self._calculate_psar(
            df["high"].values, df["low"].values
        )

        if len(psar_series) == 0:
            return self._insufficient_data()

        current_psar = float(psar_series[-1])
        current_trend = "BULLISH" if trend_series[-1] == 1 else "BEARISH"
        current_price = float(df["close"].iloc[-1])

        signal = self._generate_signal(current_trend, current_price, current_psar)
        confidence = self._confidence(current_trend, current_price, current_psar)

        return {
            "psar": round(current_psar, 2),
            "trend": current_trend,
            "signal": signal,
            "confidence": round(confidence, 3),
            "acceleration_factor": round(float(af_series[-1]), 3),
            "metadata": {
                "step": self.config.step,
                "max_step": self.config.max_step,
                "module_version": self.VERSION,
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

    def _calculate_psar(self, highs: np.ndarray, lows: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        length = len(highs)
        if length < 2:
            return np.array([]), np.array([]), np.array([])

        psar = np.zeros(length)
        trend = np.zeros(length)
        acceleration = np.zeros(length)

        step = self.config.step
        max_step = self.config.max_step

        # Initial trend assumption based on first two candles
        bullish = highs[1] >= highs[0]
        trend[0] = 1 if bullish else -1
        psar[0] = lows[0] if bullish else highs[0]
        ep = highs[0] if bullish else lows[0]
        af = step
        acceleration[0] = af

        for i in range(1, length):
            prev_psar = psar[i - 1]

            psar[i] = prev_psar + af * (ep - prev_psar)

            if bullish:
                psar[i] = min(psar[i], lows[i - 1], lows[i])
            else:
                psar[i] = max(psar[i], highs[i - 1], highs[i])

            reverse = False
            if bullish:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + step, max_step)
                if lows[i] < psar[i]:
                    reverse = True
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + step, max_step)
                if highs[i] > psar[i]:
                    reverse = True

            if reverse:
                bullish = not bullish
                psar[i] = ep
                ep = highs[i] if bullish else lows[i]
                af = step

            trend[i] = 1 if bullish else -1
            acceleration[i] = af

        return psar, trend, acceleration

    def _generate_signal(self, trend: str, price: float, psar_value: float) -> str:
        if trend == "BULLISH" and price > psar_value:
            return "BUY"
        if trend == "BEARISH" and price < psar_value:
            return "SELL"
        return "HOLD"

    def _confidence(self, trend: str, price: float, psar_value: float) -> float:
        distance = abs(price - psar_value)
        if psar_value == 0:
            return 0.3
        distance_pct = distance / psar_value * 100
        if distance_pct > 2:
            base = 0.7
        elif distance_pct > 1:
            base = 0.5
        else:
            base = 0.3
        return min(1.0, base + 0.1)

    def _insufficient_data(self) -> Dict[str, Any]:
        return {
            "psar": None,
            "trend": "UNKNOWN",
            "signal": "HOLD",
            "confidence": 0.0,
            "acceleration_factor": 0.0,
            "error": f"Need at least {self.config.min_candles} candles for Parabolic SAR",
        }

    def get_required_history(self) -> int:
        return self.config.min_candles

    def validate_config(self) -> bool:
        return 0 < self.config.step < self.config.max_step <= 0.5