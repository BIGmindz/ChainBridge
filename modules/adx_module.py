"""ADX (Average Directional Index) Module."""

from typing import Any, Dict, List
import numpy as np
import pandas as pd

from core.module_manager import Module


class ADXModule(Module):
    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        config = config or {}
        self.period = config.get("period", 14)
        self.adx_smoothing = config.get("adx_smoothing", 14)
        self.weak_trend_threshold = config.get("weak_trend_threshold", 25)
        self.strong_trend_threshold = config.get("strong_trend_threshold", 50)
        self.very_strong_trend_threshold = config.get("very_strong_trend_threshold", 75)
        self.di_crossover_threshold = config.get("di_crossover_threshold", 5)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {"ohlcv_data": "List of OHLCV candles"},
            "output": {
                "adx_value": "Current ADX reading",
                "plus_di": "+DI",
                "minus_di": "-DI",
                "trend_strength": "WEAK/STRONG/VERY_STRONG/EXTREME",
                "trend_direction": "BULLISH/BEARISH/NEUTRAL",
                "signal": "BUY/SELL/HOLD",
                "confidence": "Signal confidence",
                "trend_change": "STRENGTHENING/WEAKENING/STABLE",
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ohlcv = data.get("ohlcv_data", [])
        min_required = max(self.period, self.adx_smoothing) * 2
        if len(ohlcv) < min_required:
            return self._insufficient_data_response(min_required)

        df = self._ohlcv_to_dataframe(ohlcv)
        metrics = self._calculate_adx(df)

        adx_val = float(metrics["adx"].iloc[-1])
        plus_di = float(metrics["plus_di"].iloc[-1])
        minus_di = float(metrics["minus_di"].iloc[-1])

        signal = self._generate_signal(adx_val, plus_di, minus_di)
        confidence = self._calculate_confidence(adx_val, plus_di, minus_di)

        return {
            "adx_value": round(adx_val, 2),
            "plus_di": round(plus_di, 2),
            "minus_di": round(minus_di, 2),
            "trend_strength": self._classify_trend_strength(adx_val),
            "trend_direction": self._determine_trend_direction(plus_di, minus_di),
            "signal": signal,
            "confidence": round(confidence, 3),
            "trend_change": self._analyze_trend_change(metrics["adx"]),
        }

    def _ohlcv_to_dataframe(self, ohlcv: List[List[Any]]) -> pd.DataFrame:
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})

    def _calculate_adx(self, df: pd.DataFrame) -> pd.DataFrame:
        high, low, close = df["high"], df["low"], df["close"]
        tr = self._true_range(high, low, close)
        plus_dm, minus_dm = self._directional_movement(high, low)

        atr = self._wilder_smoothing(tr, self.period)
        plus_di = 100 * self._wilder_smoothing(plus_dm, self.period) / atr
        minus_di = 100 * self._wilder_smoothing(minus_dm, self.period) / atr

        di_sum = plus_di + minus_di
        di_diff = (plus_di - minus_di).abs()
        dx = (100 * di_diff / di_sum.replace(0, np.nan)).fillna(0)
        adx = self._wilder_smoothing(dx, self.adx_smoothing)

        return pd.DataFrame({"adx": adx, "plus_di": plus_di, "minus_di": minus_di})

    def _true_range(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    def _directional_movement(self, high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
        return plus_dm, minus_dm

    def _wilder_smoothing(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(alpha=1 / period, adjust=False).mean()

    def _classify_trend_strength(self, adx: float) -> str:
        if adx >= self.very_strong_trend_threshold:
            return "EXTREME"
        if adx >= self.strong_trend_threshold:
            return "VERY_STRONG"
        if adx >= self.weak_trend_threshold:
            return "STRONG"
        return "WEAK"

    def _determine_trend_direction(self, plus_di: float, minus_di: float) -> str:
        diff = plus_di - minus_di
        if abs(diff) < self.di_crossover_threshold:
            return "NEUTRAL"
        return "BULLISH" if diff > 0 else "BEARISH"

    def _generate_signal(self, adx: float, plus_di: float, minus_di: float) -> str:
        if adx < self.weak_trend_threshold:
            return "HOLD"
        if plus_di - minus_di > self.di_crossover_threshold:
            return "BUY"
        if minus_di - plus_di > self.di_crossover_threshold:
            return "SELL"
        return "HOLD"

    def _calculate_confidence(self, adx: float, plus_di: float, minus_di: float) -> float:
        base = 0.2 if adx < self.weak_trend_threshold else 0.7 if adx >= self.strong_trend_threshold else 0.5
        di_spread = abs(plus_di - minus_di)
        di_factor = min(1.0, di_spread / 20)
        return min(1.0, base * (0.7 + 0.3 * di_factor))

    def _analyze_trend_change(self, adx_series: pd.Series) -> str:
        recent = adx_series.tail(3)
        if len(recent) < 3:
            return "INSUFFICIENT_DATA"
        change = recent.iloc[-1] - recent.iloc[0]
        if change > 2:
            return "STRENGTHENING"
        if change < -2:
            return "WEAKENING"
        return "STABLE"

    def _insufficient_data_response(self, needed: int) -> Dict[str, Any]:
        return {
            "adx_value": None,
            "plus_di": None,
            "minus_di": None,
            "trend_strength": "UNKNOWN",
            "trend_direction": "UNKNOWN",
            "signal": "HOLD",
            "confidence": 0.0,
            "trend_change": "INSUFFICIENT_DATA",
            "error": f"Need at least {needed} candles",
        }

    def get_required_history(self) -> int:
        return max(self.period, self.adx_smoothing) * 3

    def validate_config(self) -> bool:
        return 5 <= self.period <= 50 and 5 <= self.adx_smoothing <= 50