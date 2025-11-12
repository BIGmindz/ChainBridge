"""Ichimoku Cloud Signal Module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from core.module_manager import Module


@dataclass
class IchimokuConfig:
    conversion_period: int = 9
    base_period: int = 26
    span_b_period: int = 52
    displacement: int = 26


class IchimokuCloudModule(Module):
    """Comprehensive trend detection using Ichimoku Kinko Hyo."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        cfg = config or {}
        self.config = IchimokuConfig(
            conversion_period=cfg.get("conversion_period", 9),
            base_period=cfg.get("base_period", 26),
            span_b_period=cfg.get("span_b_period", 52),
            displacement=cfg.get("displacement", 26),
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {"ohlcv_data": "List of OHLCV candles"},
            "output": {
                "trend": "BULLISH/BEARISH/NEUTRAL",
                "cloud_position": "Price position relative to cloud",
                "signal": "BUY/SELL/HOLD",
                "confidence": "Signal confidence 0-1",
                "components": {
                    "conversion_line": "Tenkan-sen",
                    "base_line": "Kijun-sen",
                    "leading_span_a": "Senkou Span A",
                    "leading_span_b": "Senkou Span B",
                    "lagging_span": "Chikou Span",
                },
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        candles = data.get("ohlcv_data", [])
        required = self.get_required_history()
        if len(candles) < required:
            return self._insufficient_data(required)

        df = self._to_dataframe(candles)
        ichimoku = self._calculate_ichimoku(df)
        if ichimoku is None:
            return self._insufficient_data(required)

        tenkan, kijun, span_a, span_b, chikou = ichimoku
        current_price = float(df["close"].iloc[-1])

        cloud_top = max(span_a[-1], span_b[-1])
        cloud_bottom = min(span_a[-1], span_b[-1])
        cloud_position = self._cloud_position(current_price, cloud_bottom, cloud_top)
        trend = self._trend_direction(
            current_price, tenkan[-1], kijun[-1], cloud_position, chikou
        )

        signal = self._generate_signal(trend, tenkan[-1], kijun[-1])
        confidence = self._confidence(
            trend, cloud_position, tenkan[-1], kijun[-1], current_price
        )

        return {
            "trend": trend,
            "cloud_position": cloud_position,
            "signal": signal,
            "confidence": round(confidence, 3),
            "components": {
                "conversion_line": round(float(tenkan[-1]), 2),
                "base_line": round(float(kijun[-1]), 2),
                "leading_span_a": round(float(span_a[-1]), 2),
                "leading_span_b": round(float(span_b[-1]), 2),
                "lagging_span": (
                    round(float(chikou[-1]), 2) if not np.isnan(chikou[-1]) else None
                ),
            },
            "metadata": {
                "module_version": self.VERSION,
                "conversion_period": self.config.conversion_period,
                "base_period": self.config.base_period,
                "span_b_period": self.config.span_b_period,
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

    def _calculate_ichimoku(self, df: pd.DataFrame):
        high = df["high"]
        low = df["low"]
        close = df["close"]

        cp = self.config.conversion_period
        bp = self.config.base_period
        sp = self.config.span_b_period
        disp = self.config.displacement

        high_cp = high.rolling(window=cp).max()
        low_cp = low.rolling(window=cp).min()
        tenkan = (high_cp + low_cp) / 2

        high_bp = high.rolling(window=bp).max()
        low_bp = low.rolling(window=bp).min()
        kijun = (high_bp + low_bp) / 2

        span_a = ((tenkan + kijun) / 2).shift(disp)
        high_sp = high.rolling(window=sp).max()
        low_sp = low.rolling(window=sp).min()
        span_b = ((high_sp + low_sp) / 2).shift(disp)

        chikou = close.shift(-disp)

        valid_mask = (
            (~tenkan.isna()) & (~kijun.isna()) & (~span_a.isna()) & (~span_b.isna())
        )
        if not valid_mask.any():
            return None

        idx = np.where(valid_mask)[0]
        return (
            tenkan.iloc[idx].values,
            kijun.iloc[idx].values,
            span_a.iloc[idx].values,
            span_b.iloc[idx].values,
            chikou.iloc[idx].values,
        )

    def _cloud_position(
        self, price: float, cloud_bottom: float, cloud_top: float
    ) -> str:
        if price > cloud_top:
            return "ABOVE_CLOUD"
        if price < cloud_bottom:
            return "BELOW_CLOUD"
        return "INSIDE_CLOUD"

    def _trend_direction(
        self,
        price: float,
        tenkan: float,
        kijun: float,
        cloud_position: str,
        chikou: np.ndarray,
    ) -> str:
        chikou_latest = chikou[-1]
        chikou_confirmation = (
            chikou_latest > price if not np.isnan(chikou_latest) else False
        )

        if cloud_position == "ABOVE_CLOUD" and tenkan > kijun and chikou_confirmation:
            return "BULLISH"
        if (
            cloud_position == "BELOW_CLOUD"
            and tenkan < kijun
            and not chikou_confirmation
        ):
            return "BEARISH"
        return "NEUTRAL"

    def _generate_signal(self, trend: str, tenkan: float, kijun: float) -> str:
        if trend == "BULLISH" and tenkan > kijun:
            return "BUY"
        if trend == "BEARISH" and tenkan < kijun:
            return "SELL"
        return "HOLD"

    def _confidence(
        self,
        trend: str,
        cloud_position: str,
        tenkan: float,
        kijun: float,
        price: float,
    ) -> float:
        spread = abs(tenkan - kijun)
        spread_pct = (spread / price) * 100 if price else 0

        base = 0.3
        if trend == "BULLISH" and cloud_position == "ABOVE_CLOUD":
            base = 0.6
        elif trend == "BEARISH" and cloud_position == "BELOW_CLOUD":
            base = 0.6

        spread_bonus = min(0.4, spread_pct / 5)
        return min(1.0, base + spread_bonus)

    def _insufficient_data(self, required: int) -> Dict[str, Any]:
        return {
            "trend": "NEUTRAL",
            "cloud_position": "UNKNOWN",
            "signal": "HOLD",
            "confidence": 0.0,
            "components": {},
            "error": f"Need at least {required} candles for Ichimoku Cloud",
        }

    def get_required_history(self) -> int:
        return self.config.span_b_period + self.config.displacement

    def validate_config(self) -> bool:
        return (
            self.config.conversion_period
            > 0
            < self.config.base_period
            < self.config.span_b_period
        )
