"""VWAP (Volume Weighted Average Price) Module."""

from typing import Any, Dict, List
import numpy as np
import pandas as pd

from core.module_manager import Module


class VWAPModule(Module):
    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        config = config or {}
        self.session_reset_hours = config.get("session_reset_hours", [0, 8, 16])
        self.min_volume_threshold = config.get("min_volume_threshold", 1000)
        self.deviation_threshold = config.get("deviation_threshold", 0.5)
        self.strong_deviation_threshold = config.get("strong_deviation_threshold", 1.0)
        self.slope_period = config.get("slope_period", 10)
        self.slope_threshold = config.get("slope_threshold", 0.001)

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {"ohlcv_data": "List of OHLCV candles"},
            "output": {
                "vwap_value": "Current VWAP",
                "price_position": "ABOVE/BELOW",
                "deviation_pct": "Deviation percentage",
                "signal": "BUY/SELL/HOLD",
                "signal_strength": "STRONG/WEAK/NEUTRAL",
                "vwap_slope": "Slope direction",
                "volume_profile": "Volume distribution above/below VWAP",
                "confidence": "Signal confidence",
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ohlcv = data.get("ohlcv_data", [])
        if len(ohlcv) < 2:
            return self._insufficient_data("Need at least 2 candles")

        df = self._ohlcv_to_dataframe(ohlcv)
        df = df[df["volume"] >= self.min_volume_threshold]
        if len(df) < 2:
            return self._insufficient_data("Insufficient volume data")

        vwap_df = self._calculate_vwap(df)
        if vwap_df.empty:
            return self._insufficient_data("Unable to compute VWAP")

        current_price = df["close"].iloc[-1]
        current_vwap = float(vwap_df["vwap"].iloc[-1])
        deviation_pct = (current_price - current_vwap) / current_vwap * 100
        price_position = "ABOVE" if current_price > current_vwap else "BELOW"

        signal = self._generate_signal(current_price, current_vwap, deviation_pct)
        signal_strength = self._signal_strength(abs(deviation_pct))
        vwap_slope = self._calculate_slope(vwap_df)
        volume_profile = self._volume_profile(df, vwap_df)
        confidence = self._confidence(
            abs(deviation_pct), df["volume"].iloc[-1], vwap_slope
        )

        return {
            "vwap_value": round(current_vwap, 6),
            "price_position": price_position,
            "deviation_pct": round(deviation_pct, 3),
            "signal": signal,
            "signal_strength": signal_strength,
            "vwap_slope": vwap_slope,
            "volume_profile": volume_profile,
            "confidence": round(confidence, 3),
        }

    def _ohlcv_to_dataframe(self, ohlcv: List[List[Any]]) -> pd.DataFrame:
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df = df.astype(
            {
                "timestamp": int,
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,
            }
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["hour"] = df["datetime"].dt.hour
        return df

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
        df["price_volume"] = df["typical_price"] * df["volume"]
        df["session_reset"] = df["hour"].isin(self.session_reset_hours)
        df["session_id"] = df["session_reset"].cumsum()

        frames = []
        for session in df["session_id"].unique():
            session_df = df[df["session_id"] == session].copy()
            session_df["cum_price_volume"] = session_df["price_volume"].cumsum()
            session_df["cum_volume"] = session_df["volume"].cumsum()
            session_df["vwap"] = (
                session_df["cum_price_volume"] / session_df["cum_volume"]
            )
            frames.append(session_df)

        return pd.concat(frames, ignore_index=True)[
            ["vwap", "volume", "typical_price", "datetime"]
        ]

    def _generate_signal(self, price: float, vwap: float, deviation: float) -> str:
        abs_dev = abs(deviation)
        if abs_dev >= self.strong_deviation_threshold:
            return "SELL" if price > vwap else "BUY"
        if abs_dev >= self.deviation_threshold:
            return "BUY" if price > vwap else "SELL"
        return "HOLD"

    def _signal_strength(self, deviation: float) -> str:
        if deviation >= self.strong_deviation_threshold:
            return "STRONG"
        if deviation >= self.deviation_threshold:
            return "WEAK"
        return "NEUTRAL"

    def _calculate_slope(self, vwap_df: pd.DataFrame) -> Dict[str, Any]:
        if len(vwap_df) < self.slope_period:
            return {"direction": "UNKNOWN", "strength": 0.0}
        recent = vwap_df["vwap"].tail(self.slope_period)
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        avg_price = recent.mean()
        slope_pct = (slope / avg_price) * 100 if avg_price > 0 else 0
        if slope_pct > self.slope_threshold:
            direction = "RISING"
        elif slope_pct < -self.slope_threshold:
            direction = "FALLING"
        else:
            direction = "FLAT"
        return {"direction": direction, "strength": round(abs(slope_pct), 4)}

    def _volume_profile(
        self, df: pd.DataFrame, vwap_df: pd.DataFrame
    ) -> Dict[str, Any]:
        recent = min(20, len(df))
        prices = df.tail(recent)
        vwap = vwap_df.tail(recent)
        above = prices[prices["close"] > vwap["vwap"]]["volume"].sum()
        below = prices[prices["close"] <= vwap["vwap"]]["volume"].sum()
        total = above + below
        if total == 0:
            return {"profile": "NO_DATA", "above_vwap_pct": 0, "below_vwap_pct": 0}
        above_pct = above / total * 100
        below_pct = below / total * 100
        if above_pct > 60:
            profile = "BULLISH_VOLUME"
        elif below_pct > 60:
            profile = "BEARISH_VOLUME"
        else:
            profile = "BALANCED_VOLUME"
        return {
            "profile": profile,
            "above_vwap_pct": round(above_pct, 1),
            "below_vwap_pct": round(below_pct, 1),
        }

    def _confidence(
        self, deviation: float, volume: float, slope: Dict[str, Any]
    ) -> float:
        base = (
            0.8
            if deviation >= self.strong_deviation_threshold
            else 0.6 if deviation >= self.deviation_threshold else 0.3
        )
        volume_factor = min(1.0, volume / (self.min_volume_threshold * 5))
        slope_strength = slope.get("strength", 0)
        slope_factor = min(1.0, slope_strength)
        return min(1.0, base * (0.6 + 0.2 * volume_factor + 0.2 * slope_factor))

    def _insufficient_data(self, msg: str) -> Dict[str, Any]:
        return {
            "vwap_value": None,
            "price_position": "UNKNOWN",
            "deviation_pct": 0.0,
            "signal": "HOLD",
            "signal_strength": "NEUTRAL",
            "vwap_slope": {"direction": "UNKNOWN", "strength": 0.0},
            "volume_profile": {
                "profile": "NO_DATA",
                "above_vwap_pct": 0,
                "below_vwap_pct": 0,
            },
            "confidence": 0.0,
            "error": msg,
        }

    def get_required_history(self) -> int:
        return max(self.slope_period * 2, 20)

    def validate_config(self) -> bool:
        return 0 < self.deviation_threshold < self.strong_deviation_threshold <= 10
