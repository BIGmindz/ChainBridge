"""Utility functions for engineering Bollinger Band features.

This module provides functions to calculate Bollinger Bands and their derivative
features for use in machine learning models.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_bollinger_band_features(
    df: pd.DataFrame,
    price_col: str = "price",
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.DataFrame:
    """Calculate and append Bollinger Band features to ``df``.

    Args:
        df: DataFrame with at least a price column and a datetime index.
        price_col: The name of the column containing the price data.
        period: The lookback period for the moving average.
        std_dev: The number of standard deviations for the bands.

    Returns:
        The original DataFrame with new columns:
        - bb_width: The normalized width of the bands.
        - bb_percent_b: The position of the price within the bands (%B).
        - bb_squeeze: A nullable binary flag indicating a volatility squeeze.
    """
    if price_col not in df.columns:
        raise ValueError(f"Price column '{price_col}' not found in DataFrame.")

    working_df = df.copy()
    price_series = pd.to_numeric(working_df[price_col], errors="coerce")

    # Calculate Middle Band (SMA) and Standard Deviation
    middle_band = price_series.rolling(window=period, min_periods=period).mean()
    rolling_std = price_series.rolling(window=period, min_periods=period).std()

    # Calculate Upper and Lower Bands
    upper_band = middle_band + (rolling_std * std_dev)
    lower_band = middle_band - (rolling_std * std_dev)
    band_range = upper_band - lower_band

    safe_middle_band = middle_band.mask(middle_band == 0)
    safe_band_range = band_range.mask(band_range == 0)

    # --- Feature 1: Band Width (Volatility) ---
    bb_width = band_range / safe_middle_band
    bb_width = bb_width.replace([np.inf, -np.inf], pd.NA)
    working_df["bb_width"] = bb_width.astype("Float64")  # type: ignore

    # --- Feature 2: %B (Position within Bands) ---
    percent_b = (price_series - lower_band) / safe_band_range
    percent_b = percent_b.replace([np.inf, -np.inf], pd.NA)
    working_df["bb_percent_b"] = percent_b.clip(lower=0.0, upper=1.0).astype("Float64")  # type: ignore

    # --- Feature 3: Volatility Squeeze ---
    # A squeeze is identified when the current band width is in the bottom 10th percentile
    # of its own rolling history (e.g., over the last 100 periods).
    squeeze_threshold = bb_width.rolling(window=100, min_periods=period).quantile(0.10, interpolation="linear")
    squeeze_series = pd.Series(pd.NA, index=working_df.index, dtype="Int64")
    valid_mask = bb_width.notna() & squeeze_threshold.notna()
    squeeze_series.loc[valid_mask] = (bb_width.loc[valid_mask] < squeeze_threshold.loc[valid_mask]).astype("int64")  # type: ignore
    working_df["bb_squeeze"] = squeeze_series

    return working_df
