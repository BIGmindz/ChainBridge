"""
Enhanced Technical Indicators Module
Adds advanced technical analysis with visually appealing indicators
"""

import talib
import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class IndicatorConfig:
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    atr_period: int = 14
    ema_periods: List[int] = (8, 13, 21, 55)
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_slow: int = 3
    volume_ma_period: int = 20
    roc_period: int = 10
    mfi_period: int = 14
    adx_period: int = 14


class EnhancedTechnicalIndicators:
    def __init__(self, config: IndicatorConfig = None):
        self.config = config or IndicatorConfig()

    def calculate_all(self, df: pd.DataFrame) -> Dict:
        """Calculate all technical indicators with visual appeal scores."""
        results = {}

        # Core Price Action
        results.update(self._calculate_price_action(df))

        # Momentum Indicators
        results.update(self._calculate_momentum(df))

        # Volume Analysis
        results.update(self._calculate_volume_analysis(df))

        # Trend Analysis
        results.update(self._calculate_trend_analysis(df))

        return results

    def _calculate_price_action(self, df: pd.DataFrame) -> Dict:
        """Calculate price action indicators with visual scores."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # Bollinger Bands with volatility scoring
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            close,
            timeperiod=self.config.bb_period,
            nbdevup=self.config.bb_std,
            nbdevdn=self.config.bb_std,
        )

        bb_width = (bb_upper - bb_lower) / bb_middle
        bb_position = (close - bb_lower) / (bb_upper - bb_lower)

        # ATR for volatility
        atr = talib.ATR(high, low, close, timeperiod=self.config.atr_period)
        atr_pct = atr / close * 100

        return {
            "bollinger_bands": {
                "upper": bb_upper,
                "middle": bb_middle,
                "lower": bb_lower,
                "width": bb_width,
                "position": bb_position,
                "volatility_score": self._normalize_score(bb_width),
                "signal": self._get_bb_signal(
                    bb_position[-1] if len(bb_position) > 0 else 0
                ),
                "alert_level": self._get_alert_level(
                    bb_position[-1] if len(bb_position) > 0 else 0
                ),
            },
            "atr": {
                "value": atr,
                "percentage": atr_pct,
                "volatility_score": self._normalize_score(atr_pct),
                "alert_level": self._get_volatility_alert(
                    atr_pct[-1] if len(atr_pct) > 0 else 0
                ),
            },
        }

    def _calculate_momentum(self, df: pd.DataFrame) -> Dict:
        """Calculate momentum indicators with excitement scores."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        # RSI with trend strength
        rsi = talib.RSI(close, timeperiod=self.config.rsi_period)

        # MACD with signal strength
        macd, signal, hist = talib.MACD(
            close,
            fastperiod=self.config.macd_fast,
            slowperiod=self.config.macd_slow,
            signalperiod=self.config.macd_signal,
        )

        # Stochastic with momentum scoring
        slowk, slowd = talib.STOCH(
            high,
            low,
            close,
            fastk_period=self.config.stoch_k,
            slowk_period=self.config.stoch_slow,
            slowk_matype=0,
            slowd_period=self.config.stoch_d,
            slowd_matype=0,
        )

        # MFI for volume-weighted momentum
        mfi = talib.MFI(high, low, close, volume, timeperiod=self.config.mfi_period)

        return {
            "rsi": {
                "value": rsi,
                "trend_strength": self._get_rsi_strength(
                    rsi[-1] if len(rsi) > 0 else 50
                ),
                "signal": self._get_rsi_signal(rsi[-1] if len(rsi) > 0 else 50),
                "alert_level": self._get_alert_level(rsi[-1] if len(rsi) > 0 else 50),
            },
            "macd": {
                "macd": macd,
                "signal": signal,
                "histogram": hist,
                "momentum_score": self._normalize_score(hist),
                "signal_strength": self._get_macd_strength(
                    hist[-1] if len(hist) > 0 else 0
                ),
                "alert_level": self._get_macd_alert(hist[-1] if len(hist) > 0 else 0),
            },
            "stochastic": {
                "k": slowk,
                "d": slowd,
                "momentum_score": self._get_stoch_momentum(
                    slowk[-1] if len(slowk) > 0 else 50,
                    slowd[-1] if len(slowd) > 0 else 50,
                ),
                "signal": self._get_stoch_signal(
                    slowk[-1] if len(slowk) > 0 else 50,
                    slowd[-1] if len(slowd) > 0 else 50,
                ),
                "alert_level": self._get_stoch_alert(
                    slowk[-1] if len(slowk) > 0 else 50
                ),
            },
            "mfi": {
                "value": mfi,
                "flow_score": self._normalize_score(mfi),
                "signal": self._get_mfi_signal(mfi[-1] if len(mfi) > 0 else 50),
                "alert_level": self._get_mfi_alert(mfi[-1] if len(mfi) > 0 else 50),
            },
        }

    def _calculate_volume_analysis(self, df: pd.DataFrame) -> Dict:
        """Calculate volume-based indicators with intensity scores."""
        close = df["close"].values
        volume = df["volume"].values

        # Volume MA
        volume_ma = talib.SMA(volume, timeperiod=self.config.volume_ma_period)
        volume_ratio = np.where(volume_ma != 0, volume / volume_ma, 1)

        # OBV with trend scoring
        obv = talib.OBV(close, volume)
        obv_ma = talib.SMA(obv, timeperiod=self.config.volume_ma_period)
        obv_ratio = np.where(obv_ma != 0, obv / obv_ma, 1)

        return {
            "volume_analysis": {
                "volume_ma": volume_ma,
                "volume_ratio": volume_ratio,
                "intensity_score": self._normalize_score(volume_ratio),
                "signal": self._get_volume_signal(
                    volume_ratio[-1] if len(volume_ratio) > 0 else 1
                ),
                "alert_level": self._get_volume_alert(
                    volume_ratio[-1] if len(volume_ratio) > 0 else 1
                ),
            },
            "obv": {
                "value": obv,
                "ma": obv_ma,
                "ratio": obv_ratio,
                "trend_score": self._normalize_score(obv_ratio),
                "signal": self._get_obv_signal(
                    obv_ratio[-1] if len(obv_ratio) > 0 else 1
                ),
                "alert_level": self._get_obv_alert(
                    obv_ratio[-1] if len(obv_ratio) > 0 else 1
                ),
            },
        }

    def _calculate_trend_analysis(self, df: pd.DataFrame) -> Dict:
        """Calculate trend indicators with strength scoring."""
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        # Multiple EMAs
        emas = {}
        for period in self.config.ema_periods:
            emas[f"ema_{period}"] = talib.EMA(close, timeperiod=period)

        # ADX for trend strength
        adx = talib.ADX(high, low, close, timeperiod=self.config.adx_period)

        return {
            "ema_cloud": {
                "emas": emas,
                "cloud_strength": self._get_ema_cloud_strength(
                    emas, close[-1] if len(close) > 0 else 0
                ),
                "signal": self._get_ema_signal(
                    emas, close[-1] if len(close) > 0 else 0
                ),
                "alert_level": self._get_ema_alert(
                    emas, close[-1] if len(close) > 0 else 0
                ),
            },
            "adx": {
                "value": adx,
                "trend_strength": self._normalize_score(adx),
                "signal": self._get_adx_signal(adx[-1] if len(adx) > 0 else 0),
                "alert_level": self._get_adx_alert(adx[-1] if len(adx) > 0 else 0),
            },
        }

    # Helper Methods
    def _normalize_score(self, values: np.ndarray) -> np.ndarray:
        """Normalize values to 0-100 scale."""
        if len(values) == 0:
            return np.array([])
        min_val = np.min(values)
        max_val = np.max(values)
        if max_val == min_val:
            return np.full_like(values, 50)
        return ((values - min_val) / (max_val - min_val)) * 100

    def _get_bb_signal(self, position: float) -> str:
        if position > 0.95:
            return "🔴 OVERBOUGHT!"
        if position < 0.05:
            return "🟢 OVERSOLD!"
        return "⚪ NEUTRAL"

    def _get_rsi_signal(self, value: float) -> str:
        if value > 70:
            return "🔴 OVERBOUGHT!"
        if value < 30:
            return "🟢 OVERSOLD!"
        return "⚪ NEUTRAL"

    def _get_macd_signal(self, hist: float) -> str:
        if hist > 0:
            return "🟢 BULLISH"
        if hist < 0:
            return "🔴 BEARISH"
        return "⚪ NEUTRAL"

    def _get_alert_level(self, value: float) -> str:
        if value > 90:
            return "🚨 EXTREME!"
        if value > 70:
            return "⚠️ HIGH!"
        if value > 30:
            return "📊 MODERATE"
        if value > 10:
            return "ℹ️ LOW"
        return "😴 MINIMAL"

    def _get_volatility_alert(self, value: float) -> str:
        if value > 5:
            return "🚨 HIGH VOLATILITY!"
        if value > 2:
            return "⚠️ MODERATE VOLATILITY"
        return "😴 LOW VOLATILITY"

    def _get_rsi_strength(self, value: float) -> str:
        if value > 80:
            return "EXTREMELY OVERBOUGHT"
        if value > 70:
            return "OVERBOUGHT"
        if value < 20:
            return "EXTREMELY OVERSOLD"
        if value < 30:
            return "OVERSOLD"
        return "NEUTRAL"

    def _get_macd_strength(self, value: float) -> str:
        if abs(value) < 0.1:
            return "WEAK"
        if abs(value) < 0.5:
            return "MODERATE"
        return "STRONG"

    def _get_macd_alert(self, value: float) -> str:
        if abs(value) > 1.0:
            return "🚨 STRONG MOMENTUM!"
        if abs(value) > 0.5:
            return "⚠️ BUILDING MOMENTUM"
        return "ℹ️ WEAK MOMENTUM"

    def _get_stoch_momentum(self, k: float, d: float) -> float:
        return abs(k - d)

    def _get_stoch_signal(self, k: float, d: float) -> str:
        if k > d and k < 20:
            return "🟢 BULLISH DIVERGENCE"
        if k < d and k > 80:
            return "🔴 BEARISH DIVERGENCE"
        return "⚪ NEUTRAL"

    def _get_stoch_alert(self, value: float) -> str:
        if value > 80:
            return "🚨 OVERBOUGHT!"
        if value < 20:
            return "🚨 OVERSOLD!"
        return "ℹ️ NEUTRAL"

    def _get_mfi_signal(self, value: float) -> str:
        if value > 80:
            return "🔴 OVERBOUGHT"
        if value < 20:
            return "🟢 OVERSOLD"
        return "⚪ NEUTRAL"

    def _get_mfi_alert(self, value: float) -> str:
        if value > 90:
            return "🚨 EXTREME BUYING!"
        if value < 10:
            return "🚨 EXTREME SELLING!"
        return "ℹ️ NORMAL FLOW"

    def _get_volume_signal(self, ratio: float) -> str:
        if ratio > 2.0:
            return "🚨 VOLUME SPIKE!"
        if ratio > 1.5:
            return "⚠️ HIGH VOLUME"
        if ratio < 0.5:
            return "ℹ️ LOW VOLUME"
        return "📊 NORMAL VOLUME"

    def _get_volume_alert(self, ratio: float) -> str:
        if ratio > 3.0:
            return "🚨 EXTREME VOLUME!"
        if ratio > 2.0:
            return "⚠️ HIGH ACTIVITY"
        return "ℹ️ NORMAL"

    def _get_obv_signal(self, ratio: float) -> str:
        if ratio > 1.1:
            return "🟢 ACCUMULATION"
        if ratio < 0.9:
            return "🔴 DISTRIBUTION"
        return "⚪ NEUTRAL"

    def _get_obv_alert(self, ratio: float) -> str:
        if abs(ratio - 1) > 0.2:
            return "🚨 STRONG FLOW!"
        if abs(ratio - 1) > 0.1:
            return "⚠️ MODERATE FLOW"
        return "ℹ️ WEAK FLOW"

    def _get_ema_cloud_strength(self, emas: Dict[str, np.ndarray], price: float) -> str:
        above_count = 0
        total = 0
        for ema_arr in emas.values():
            if len(ema_arr) > 0:
                total += 1
                if price > ema_arr[-1]:
                    above_count += 1

        if total == 0:
            return "NEUTRAL"

        ratio = above_count / total
        if ratio > 0.8:
            return "VERY BULLISH"
        if ratio > 0.6:
            return "BULLISH"
        if ratio < 0.2:
            return "VERY BEARISH"
        if ratio < 0.4:
            return "BEARISH"
        return "NEUTRAL"

    def _get_ema_signal(self, emas: Dict[str, np.ndarray], price: float) -> str:
        strength = self._get_ema_cloud_strength(emas, price)
        if "VERY" in strength:
            return f"🚨 {strength}!"
        return f"⚠️ {strength}"

    def _get_ema_alert(self, emas: Dict[str, np.ndarray], price: float) -> str:
        strength = self._get_ema_cloud_strength(emas, price)
        if "VERY" in strength:
            return "🚨 STRONG TREND!"
        if "NEUTRAL" not in strength:
            return "⚠️ TRENDING"
        return "ℹ️ RANGING"

    def _get_adx_signal(self, value: float) -> str:
        if value > 50:
            return "🚨 STRONG TREND!"
        if value > 25:
            return "⚠️ TRENDING"
        return "ℹ️ NO TREND"

    def _get_adx_alert(self, value: float) -> str:
        if value > 40:
            return "🚨 STRONG TREND!"
        if value > 20:
            return "⚠️ MODERATE TREND"
        return "😴 WEAK TREND"
