#!/usr/bin/env python3
"""
Feature Hygiene Utilities for ML Pipeline

Provides robust preprocessing functions for financial ML features.
Designed to work with tree-based models like LightGBM that don't need
standardization but benefit from outlier handling.
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple
import logging

logger = logging.getLogger(__name__)


def robust_clip(
    X: Union[np.ndarray, pd.DataFrame], lower_percentile: float = 1.0, upper_percentile: float = 99.0, clip_method: str = "percentile"
) -> Union[np.ndarray, pd.DataFrame]:
    """
    Robust feature clipping to handle outliers without standardization.

    This is preferred over StandardScaler for tree-based models like LightGBM
    as it preserves feature interpretability while handling extreme values.

    Args:
        X: Input features (numpy array or pandas DataFrame)
        lower_percentile: Lower percentile for clipping (default 1%)
        upper_percentile: Upper percentile for clipping (default 99%)
        clip_method: Method for determining clip bounds ('percentile', 'iqr', 'mad')

    Returns:
        Clipped features with same type as input
    """
    if isinstance(X, pd.DataFrame):
        return _robust_clip_dataframe(X, lower_percentile, upper_percentile, clip_method)
    elif isinstance(X, np.ndarray):
        return _robust_clip_array(X, lower_percentile, upper_percentile, clip_method)
    else:
        raise ValueError("Input must be numpy array or pandas DataFrame")


def _robust_clip_dataframe(df: pd.DataFrame, lower_percentile: float, upper_percentile: float, clip_method: str) -> pd.DataFrame:
    """Robust clipping for pandas DataFrame."""
    df_clipped = df.copy()

    for col in df.columns:
        if df[col].dtype in ["float64", "float32", "int64", "int32"]:
            lower_bound, upper_bound = _get_clip_bounds(df[col].values, lower_percentile, upper_percentile, clip_method)

            # Count outliers before clipping
            n_outliers_lower = (df[col] < lower_bound).sum()
            n_outliers_upper = (df[col] > upper_bound).sum()

            if n_outliers_lower > 0 or n_outliers_upper > 0:
                logger.debug(
                    f"Column {col}: clipping {n_outliers_lower + n_outliers_upper} outliers "
                    f"({n_outliers_lower} lower, {n_outliers_upper} upper)"
                )

            # Apply clipping
            df_clipped[col] = np.clip(df[col], lower_bound, upper_bound)

    return df_clipped


def _robust_clip_array(arr: np.ndarray, lower_percentile: float, upper_percentile: float, clip_method: str) -> np.ndarray:
    """Robust clipping for numpy array."""
    arr_clipped = arr.copy()

    # Handle multi-dimensional arrays
    if arr.ndim == 1:
        lower_bound, upper_bound = _get_clip_bounds(arr, lower_percentile, upper_percentile, clip_method)
        arr_clipped = np.clip(arr, lower_bound, upper_bound)
    else:
        # Apply clipping to each column
        for col_idx in range(arr.shape[1]):
            lower_bound, upper_bound = _get_clip_bounds(arr[:, col_idx], lower_percentile, upper_percentile, clip_method)
            arr_clipped[:, col_idx] = np.clip(arr[:, col_idx], lower_bound, upper_bound)

    return arr_clipped


def _get_clip_bounds(values: np.ndarray, lower_percentile: float, upper_percentile: float, clip_method: str) -> Tuple[float, float]:
    """Calculate clipping bounds using specified method."""
    if clip_method == "percentile":
        lower_bound = np.percentile(values, lower_percentile)
        upper_bound = np.percentile(values, upper_percentile)

    elif clip_method == "iqr":
        # IQR method: Q1 - 1.5*IQR to Q3 + 1.5*IQR
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

    elif clip_method == "mad":
        # MAD method: median ± 3*MAD
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        lower_bound = median - 3 * mad
        upper_bound = median + 3 * mad

    else:
        raise ValueError(f"Unknown clip_method: {clip_method}")

    return lower_bound, upper_bound


def winsorize_features(X: Union[np.ndarray, pd.DataFrame], limits: Tuple[float, float] = (0.05, 0.05)) -> Union[np.ndarray, pd.DataFrame]:
    """
    Winsorize features by limiting extreme values to percentiles.

    Args:
        X: Input features
        limits: Tuple of (lower_limit, upper_limit) as fractions

    Returns:
        Winsorized features
    """
    lower_limit, upper_limit = limits

    if isinstance(X, pd.DataFrame):
        return X.apply(lambda x: _winsorize_series(x, lower_limit, upper_limit), axis=0)
    elif isinstance(X, np.ndarray):
        if X.ndim == 1:
            return _winsorize_array(X, lower_limit, upper_limit)
        else:
            return np.apply_along_axis(lambda x: _winsorize_array(x, lower_limit, upper_limit), axis=0, arr=X)
    else:
        raise ValueError("Input must be numpy array or pandas DataFrame")


def _winsorize_series(series: pd.Series, lower_limit: float, upper_limit: float) -> pd.Series:
    """Winsorize a pandas Series."""
    lower_percentile = lower_limit * 100
    upper_percentile = (1 - upper_limit) * 100

    lower_bound = np.percentile(series, lower_percentile)
    upper_bound = np.percentile(series, upper_percentile)

    return np.clip(series, lower_bound, upper_bound)


def _winsorize_array(arr: np.ndarray, lower_limit: float, upper_limit: float) -> np.ndarray:
    """Winsorize a numpy array."""
    lower_percentile = lower_limit * 100
    upper_percentile = (1 - upper_limit) * 100

    lower_bound = np.percentile(arr, lower_percentile)
    upper_bound = np.percentile(arr, upper_percentile)

    return np.clip(arr, lower_bound, upper_bound)


def remove_constant_features(X: Union[np.ndarray, pd.DataFrame], threshold: float = 1e-10) -> Union[np.ndarray, pd.DataFrame]:
    """
    Remove features with constant or near-constant values.

    Args:
        X: Input features
        threshold: Variance threshold below which features are removed

    Returns:
        Features with constant columns removed
    """
    if isinstance(X, pd.DataFrame):
        variances = X.var()
        constant_cols = variances[variances < threshold].index
        if len(constant_cols) > 0:
            logger.info(f"Removing {len(constant_cols)} constant features: {list(constant_cols)}")
            return X.drop(columns=constant_cols)
        return X

    elif isinstance(X, np.ndarray):
        if X.ndim == 1:
            return X if np.var(X) >= threshold else np.array([])

        # For 2D arrays
        variances = np.var(X, axis=0)
        non_constant_mask = variances >= threshold

        if not np.all(non_constant_mask):
            n_removed = np.sum(~non_constant_mask)
            logger.info(f"Removing {n_removed} constant features")

        return X[:, non_constant_mask]

    else:
        raise ValueError("Input must be numpy array or pandas DataFrame")


def handle_missing_values(X: Union[np.ndarray, pd.DataFrame], strategy: str = "median") -> Union[np.ndarray, pd.DataFrame]:
    """
    Handle missing values in features.

    Args:
        X: Input features
        strategy: Imputation strategy ('median', 'mean', 'mode', 'constant')

    Returns:
        Features with missing values handled
    """
    if isinstance(X, pd.DataFrame):
        return _handle_missing_dataframe(X, strategy)
    elif isinstance(X, np.ndarray):
        return _handle_missing_array(X, strategy)
    else:
        raise ValueError("Input must be numpy array or pandas DataFrame")


def _handle_missing_dataframe(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Handle missing values in DataFrame."""
    df_filled = df.copy()

    for col in df.columns:
        if df[col].isnull().any():
            if strategy == "median":
                fill_value = df[col].median()
            elif strategy == "mean":
                fill_value = df[col].mean()
            elif strategy == "mode":
                fill_value = df[col].mode().iloc[0] if not df[col].mode().empty else 0
            elif strategy == "constant":
                fill_value = 0
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            df_filled[col] = df[col].fillna(fill_value)
            logger.debug(f"Filled {df[col].isnull().sum()} missing values in {col} with {fill_value}")

    return df_filled


def _handle_missing_array(arr: np.ndarray, strategy: str) -> np.ndarray:
    """Handle missing values in numpy array."""
    arr_filled = arr.copy()

    if np.ma.is_masked(arr_filled):
        arr_filled = arr_filled.filled(np.nan)

    mask = np.isnan(arr_filled)

    if not np.any(mask):
        return arr_filled

    if arr.ndim == 1:
        if strategy == "median":
            fill_value = np.nanmedian(arr)
        elif strategy == "mean":
            fill_value = np.nanmean(arr)
        elif strategy == "constant":
            fill_value = 0
        else:
            raise ValueError(f"Strategy {strategy} not supported for 1D arrays")

        arr_filled[mask] = fill_value

    else:
        # Handle each column separately
        for col_idx in range(arr.shape[1]):
            col_data = arr[:, col_idx]
            col_mask = np.isnan(col_data)

            if np.any(col_mask):
                if strategy == "median":
                    fill_value = np.nanmedian(col_data)
                elif strategy == "mean":
                    fill_value = np.nanmean(col_data)
                elif strategy == "constant":
                    fill_value = 0
                else:
                    raise ValueError(f"Unknown strategy: {strategy}")

                arr_filled[col_mask, col_idx] = fill_value

    return arr_filled
