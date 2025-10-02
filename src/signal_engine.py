"""
Signal Engine Module

This module contains the logic for generating trading signals.
Currently implements RSI (Relative Strength Index) calculations using Wilder's method.
"""

import math
from typing import List

import pandas as pd


def wilder_rsi(close: pd.Series, period: int = 14) -> float:
    """Wilder's RSI using EMA smoothing."""
    if len(close) < max(2, period + 1):
        return float("nan")  # type: ignore
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    last_gain = float(avg_gain.iloc[-1])  # type: ignore
    last_loss = float(avg_loss.iloc[-1])  # type: ignore
    if last_loss == 0 and last_gain == 0:
        return 50.0
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return float(100 - (100 / (1 + rs)))  # type: ignore


def calculate_rsi_from_ohlcv(ohlcv: List[List[float]], period: int) -> float:
    """OHLCV rows: [ts, open, high, low, close, volume]."""
    if not ohlcv:
        return float("nan")  # type: ignore
    closes = [row[4] for row in ohlcv if len(row) >= 5]
    series = pd.Series(closes, dtype=float)
    if len(series) < period + 5:
        return float("nan")  # type: ignore
    return wilder_rsi(series, period=period)


def generate_signal(rsi_val: float, buy_threshold: float, sell_threshold: float) -> str:
    """Generate BUY/SELL/HOLD signal based on RSI value and thresholds."""
    if math.isnan(rsi_val):  # type: ignore
        return "HOLD"

    if rsi_val < buy_threshold:
        return "BUY"
    elif rsi_val > sell_threshold:
        return "SELL"
    else:
        return "HOLD"
