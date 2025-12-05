"""
Risk→Settlement Correlation Model for ChainBridge ML.
Gradient Boosted Trees + Logistic Regression, SHAP interpretability.
"""

import pandas as pd
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
import shap
import joblib
import logging

logger = logging.getLogger("maggie.models.risk_settlement_model")

class RiskSettlementModel:
    def __init__(self):
        self.gbm = None
        self.lr = None
        self.shap_explainer = None
        self.model_version = "v1.0"

    def train(self, df):
        features = [
            "risk_score_drift", "carrier_id", "lane_volatility", "delay_severity",
            "event_velocity", "anomaly_freq", "claim_freq", "avg_settlement_delay"
        ]
        target = "settlement_delay"
        X = df[features].fillna(0)
        y = df[target].fillna(0)
        self.gbm = lgb.LGBMRegressor()
        self.gbm.fit(X, y)
        self.lr = LogisticRegression()
        self.lr.fit(X, (y > y.median()).astype(int))
        self.shap_explainer = shap.Explainer(self.gbm, X)
        logger.info("RiskSettlementModel trained.")

    def predict(self, X):
        delay_pred = self.gbm.predict(X)
        hold_prob = self.lr.predict_proba(X)[:, 1]
        shap_values = self.shap_explainer(X)
        return {
            "settlement_delay_probability": delay_pred,
            "hold_likelihood": hold_prob,
            "carrier_risk_index": X["carrier_id"],
            "feature_contributions": shap_values.values,
            "model_version": self.model_version
        }

    def save(self, path):
        joblib.dump(self.gbm, f"{path}_gbm.pkl")
        joblib.dump(self.lr, f"{path}_lr.pkl")
        logger.info(f"Model saved to {path}")

    def load(self, path):
        self.gbm = joblib.load(f"{path}_gbm.pkl")
        self.lr = joblib.load(f"{path}_lr.pkl")
        logger.info(f"Model loaded from {path}")
