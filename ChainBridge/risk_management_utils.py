"""
RISK MANAGEMENT UTILITIES
Advanced position sizing and risk management functions
"""

import numpy as np
import pandas as pd


def vol_target_position_size(
    price_series: pd.Series,
    max_capital_at_risk: float,
    target_ann_vol: float = 0.25,
    ewm_span: int = 100,
) -> float:
    """
    Calculates position size in USD based on volatility targeting.
    This ensures we take on a consistent level of risk per trade.

    Args:
        price_series: A pandas Series of recent prices.
        max_capital_at_risk: The maximum USD to risk on this trade.
        target_ann_vol: The desired annualized volatility for our position (e.g., 25%).
        ewm_span: The lookback period for the volatility calculation.

    Returns:
        The calculated position size in USD.
    """
    if len(price_series) < ewm_span:
        # Not enough data for a stable volatility estimate, take minimum risk
        return max_capital_at_risk * 0.1

    # Calculate bar-to-bar log returns
    bar_returns = np.log(price_series).diff()

    # Calculate annualized volatility using an Exponentially Weighted Moving Average
    # The annualization factor depends on the bar frequency.
    # This example assumes 5-minute bars: (60/5) bars/hr * 24 hrs/day * 365 days/yr
    ann_factor = np.sqrt(12 * 24 * 365)  # 5-minute bars
    volatility = bar_returns.ewm(span=ewm_span).std().iloc[-1] * ann_factor

    if volatility == 0:
        return 0.0  # Avoid division by zero in flat markets

    # Scale position size based on the ratio of target vol to current vol
    scale_factor = target_ann_vol / volatility

    # Cap leverage at 1x (no borrowing) and ensure position size is not negative
    final_scale = min(1.0, max(0.0, scale_factor))

    calculated_size_usd = max_capital_at_risk * final_scale

    return calculated_size_usd


def calculate_realized_volatility(price_series: pd.Series, window: int = 100) -> float:
    """
    Calculate realized volatility from price series.

    Args:
        price_series: Price data series
        window: Lookback window for volatility calculation

    Returns:
        Annualized volatility as decimal
    """
    if len(price_series) < window:
        return 0.02  # Default 2% volatility

    returns = np.log(price_series / price_series.shift(1)).dropna()
    daily_vol = returns.std() * np.sqrt(252)  # Annualize assuming daily data

    return daily_vol


def get_volatility_adjusted_position_size(
    base_position_size: float,
    current_volatility: float,
    target_volatility: float = 0.25,
    max_leverage: float = 1.0,
) -> float:
    """
    Adjust position size based on current market volatility.

    Args:
        base_position_size: Base position size before volatility adjustment
        current_volatility: Current market volatility (annualized)
        target_volatility: Target volatility level
        max_leverage: Maximum allowed leverage (1.0 = no leverage)

    Returns:
        Adjusted position size
    """
    if current_volatility <= 0:
        return base_position_size * 0.1  # Conservative fallback

    # Scale factor based on volatility ratio
    scale_factor = target_volatility / current_volatility

    # Apply leverage cap
    scale_factor = min(scale_factor, max_leverage)

    # Ensure non-negative
    scale_factor = max(0.0, scale_factor)

    return base_position_size * scale_factor


def calculate_kelly_position_size(
    win_probability: float,
    win_loss_ratio: float,
    capital: float,
    max_risk_pct: float = 0.02,
) -> float:
    """
    Calculate position size using Kelly Criterion.

    Args:
        win_probability: Probability of winning trade
        win_loss_ratio: Average win size / average loss size
        capital: Available capital
        max_risk_pct: Maximum risk per trade as percentage

    Returns:
        Position size in dollars
    """
    # Kelly formula: f = (p*b - q)/b
    # where p = win prob, b = win/loss ratio, q = loss prob
    loss_probability = 1 - win_probability

    if win_loss_ratio <= 0:
        return 0.0

    kelly_fraction = (
        win_probability * win_loss_ratio - loss_probability
    ) / win_loss_ratio

    # Cap Kelly fraction for safety
    kelly_fraction = max(0.0, min(kelly_fraction, 0.25))

    # Convert to position size
    position_size = capital * max_risk_pct * kelly_fraction / 0.25

    return position_size
