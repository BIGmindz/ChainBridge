"""
Sales Forecasting Module

This module provides basic ML-powered sales forecasting capabilities
as an example of ML pipeline integration.
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from core.module_manager import Module


class SalesForecastingModule(Module):
    """Simple sales forecasting using moving averages and trend analysis."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.window_size = config.get("window_size", 7) if config else 7
        self.forecast_periods = config.get("forecast_periods", 5) if config else 5

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "historical_sales": "list of sales records with date and amount",
                "window_size": "integer (optional, default: 7)",
                "forecast_periods": "integer (optional, default: 5)",
            },
            "output": {
                "forecast": "list of forecasted values",
                "trend": "string (UPWARD/DOWNWARD/STABLE)",
                "confidence": "float (0-1)",
                "metrics": {"rmse": "float", "mae": "float", "mape": "float"},
            },
        }

    def simple_moving_average(self, data: List[float], window: int) -> List[float]:
        """Calculate simple moving average."""
        if len(data) < window:
            return data.copy()

        sma = []
        for i in range(len(data)):
            if i < window - 1:
                sma.append(data[i])
            else:
                avg = sum(data[i - window + 1 : i + 1]) / window
                sma.append(avg)

        return sma

    def exponential_smoothing(self, data: List[float], alpha: float = 0.3) -> List[float]:
        """Apply exponential smoothing to data."""
        if not data:
            return []

        smoothed = [data[0]]  # First value remains the same

        for i in range(1, len(data)):
            smoothed_value = alpha * data[i] + (1 - alpha) * smoothed[i - 1]
            smoothed.append(smoothed_value)

        return smoothed

    def calculate_trend(self, data: List[float]) -> tuple:
        """Calculate trend direction and strength."""
        if len(data) < 2:
            return "STABLE", 0.0

        # Calculate linear regression slope
        x = np.arange(len(data))
        y = np.array(data)

        # Simple linear regression
        _n = len(data)
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return "STABLE", 0.0

        slope = numerator / denominator

        # Determine trend direction based on slope
        trend_threshold = abs(y_mean) * 0.01  # 1% of mean as threshold

        if slope > trend_threshold:
            trend = "UPWARD"
        elif slope < -trend_threshold:
            trend = "DOWNWARD"
        else:
            trend = "STABLE"

        # Calculate trend strength (normalized)
        strength = min(1.0, abs(slope) / max(abs(y_mean), 1.0))

        return trend, strength

    def generate_forecast(self, historical_data: List[float], periods: int) -> List[float]:
        """Generate forecast using exponential smoothing and trend analysis."""
        if not historical_data or periods <= 0:
            return []

        # Apply exponential smoothing
        smoothed_data = self.exponential_smoothing(historical_data)

        # Calculate trend
        trend, trend_strength = self.calculate_trend(smoothed_data)

        # Generate forecast
        forecast = []
        last_value = smoothed_data[-1]

        # Calculate average change for trend projection
        if len(smoothed_data) >= 2:
            recent_changes = [smoothed_data[i] - smoothed_data[i - 1] for i in range(1, min(len(smoothed_data), 5))]
            avg_change = np.mean(recent_changes) if recent_changes else 0
        else:
            avg_change = 0

        # Apply trend dampening for longer forecasts
        for i in range(periods):
            dampening_factor = max(0.1, 1.0 - (i * 0.1))  # Reduce trend impact over time
            trend_adjustment = avg_change * dampening_factor

            # Add some noise reduction for stability
            if trend == "STABLE":
                trend_adjustment *= 0.5

            next_value = last_value + trend_adjustment

            # Ensure non-negative forecasts for sales data
            next_value = max(0, next_value)

            forecast.append(next_value)
            last_value = next_value

        return forecast

    def calculate_accuracy_metrics(self, actual: List[float], predicted: List[float]) -> Dict[str, float]:
        """Calculate forecast accuracy metrics."""
        if len(actual) != len(predicted) or len(actual) == 0:
            return {"rmse": 0.0, "mae": 0.0, "mape": 0.0}

        actual_arr = np.array(actual)
        predicted_arr = np.array(predicted)

        # Root Mean Square Error
        rmse = np.sqrt(np.mean((actual_arr - predicted_arr) ** 2))

        # Mean Absolute Error
        mae = np.mean(np.abs(actual_arr - predicted_arr))

        # Mean Absolute Percentage Error (handle division by zero)
        mask = actual_arr != 0
        mape = 0.0
        if np.any(mask):
            mape = np.mean(np.abs((actual_arr[mask] - predicted_arr[mask]) / actual_arr[mask])) * 100

        return {"rmse": float(rmse), "mae": float(mae), "mape": float(mape)}

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process historical sales data and generate forecast."""
        historical_sales = data.get("historical_sales", [])
        if not historical_sales:
            raise ValueError("historical_sales data is required")

        # Extract configuration
        window_size = data.get("window_size", self.window_size)
        forecast_periods = data.get("forecast_periods", self.forecast_periods)

        try:
            # Extract sales values from the data
            sales_values = []
            dates = []

            for record in historical_sales:
                if isinstance(record, dict):
                    # Extract sales amount
                    amount = record.get("amount") or record.get("sales") or record.get("value")
                    if amount is not None:
                        sales_values.append(float(amount))

                    # Extract date if available
                    date = record.get("date") or record.get("timestamp")
                    if date:
                        dates.append(date)

                elif isinstance(record, (int, float)):
                    sales_values.append(float(record))

            if not sales_values:
                raise ValueError("No sales values found in historical data")

            # Generate forecast
            forecast_values = self.generate_forecast(sales_values, forecast_periods)

            # Calculate trend
            trend, trend_strength = self.calculate_trend(sales_values)

            # Calculate confidence based on data consistency
            if len(sales_values) >= 2:
                # Use coefficient of variation as inverse confidence measure
                mean_sales = np.mean(sales_values)
                std_sales = np.std(sales_values)
                cv = (std_sales / mean_sales) if mean_sales > 0 else 1.0
                confidence = max(0.1, min(1.0, 1.0 - cv))
            else:
                confidence = 0.5

            # Prepare forecast dates if dates were provided
            forecast_dates = []
            if dates and len(dates) >= 2:
                try:
                    # Try to determine date pattern
                    last_date = pd.to_datetime(dates[-1])
                    second_last_date = pd.to_datetime(dates[-2])
                    date_diff = last_date - second_last_date

                    for i in range(1, forecast_periods + 1):
                        next_date = last_date + (date_diff * i)
                        forecast_dates.append(next_date.isoformat())
                except Exception:
                    # If date parsing fails, generate sequential dates
                    forecast_dates = [f"forecast_period_{i}" for i in range(1, forecast_periods + 1)]
            else:
                forecast_dates = [f"forecast_period_{i}" for i in range(1, forecast_periods + 1)]

            # Calculate metrics (using simple validation approach)
            metrics = {"rmse": 0.0, "mae": 0.0, "mape": 0.0}
            if len(sales_values) > window_size:
                # Use last few values for validation
                validation_size = min(3, len(sales_values) // 3)
                if validation_size > 0:
                    train_data = sales_values[:-validation_size]
                    actual_values = sales_values[-validation_size:]
                    predicted_values = self.generate_forecast(train_data, validation_size)
                    metrics = self.calculate_accuracy_metrics(actual_values, predicted_values)

            result = {
                "forecast": [
                    {
                        "period": i + 1,
                        "date": forecast_dates[i],
                        "predicted_value": forecast_values[i],
                    }
                    for i in range(len(forecast_values))
                ],
                "trend": trend,
                "trend_strength": trend_strength,
                "confidence": confidence,
                "summary_stats": {
                    "historical_mean": float(np.mean(sales_values)),
                    "historical_std": float(np.std(sales_values)),
                    "historical_min": float(np.min(sales_values)),
                    "historical_max": float(np.max(sales_values)),
                    "data_points": len(sales_values),
                },
                "metrics": metrics,
                "metadata": {
                    "window_size_used": window_size,
                    "forecast_periods": forecast_periods,
                    "module_info": {"name": self.name, "version": self.version},
                },
            }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process sales forecasting: {str(e)}")
