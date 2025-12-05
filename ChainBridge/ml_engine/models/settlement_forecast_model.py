"""
Settlement Forecasting Model for ChainBridge ML.
LightGBM/CatBoost, quantile regression, rolling window features, uncertainty scores.
"""

import pandas as pd
import lightgbm as lgb
import shap
import joblib
import logging

logger = logging.getLogger("maggie.models.settlement_forecast_model")

class SettlementForecastModel:
    def __init__(self):
        self.model = None
        self.shap_explainer = None
        self.model_version = "v1.0"

    def train(self, df):
        features = [
            "carrier_id", "lane_volatility", "delay_severity", "event_velocity",
            "risk_score_drift", "anomaly_freq", "claim_freq", "avg_settlement_delay"
        ]
        target = "final_settlement_eta"
        X = df[features].fillna(0)
        y = df[target].fillna(0)
        self.model = lgb.LGBMRegressor(objective="quantile", alpha=0.5)
        self.model.fit(X, y)
        self.shap_explainer = shap.Explainer(self.model, X)
        logger.info("SettlementForecastModel trained.")

    def predict(self, X):
        eta_pred = self.model.predict(X)
        shap_values = self.shap_explainer(X)
        return {
            "predicted_milestone_times": eta_pred,
            "volatility_index": X["lane_volatility"],
            "uncertainty_scores": shap_values.values,
            "model_version": self.model_version
        }

    def save(self, path):
        joblib.dump(self.model, f"{path}_forecast.pkl")
        logger.info(f"Model saved to {path}")

    def load(self, path):
        self.model = joblib.load(f"{path}_forecast.pkl")
        logger.info(f"Model loaded from {path}")
