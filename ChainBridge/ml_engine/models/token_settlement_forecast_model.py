"""
Token-Settlement Forecasting Model for ChainBridge ML.
Predicts expected token reward, settlement time, burn probability, with rationale and traceability.
"""

import pandas as pd
from sklearn.linear_model import Ridge, LogisticRegression
import joblib
import logging
from datetime import datetime
import uuid

logger = logging.getLogger("maggie.models.token_settlement_forecast_model")

class TokenSettlementForecastModel:
    def __init__(self):
        self.reward_model = None
        self.settlement_model = None
        self.burn_model = None
        self.model_version = "v2.0"

    def train(self, df):
        self.features = [
            "risk_score", "milestone_time", "carrier_performance", "lane_volatility",
            "tokens_rewarded", "tokens_burned", "reward_per_mile", "economic_reliability"
        ]
        X = df[self.features].fillna(0)
        y_reward = df["tokens_rewarded"].fillna(0)
        y_settlement = df["settlement_time"].fillna(0)
        y_burn = (df["tokens_burned"] > 0).astype(int)
        self.reward_model = Ridge()
        self.reward_model.fit(X, y_reward)
        self.settlement_model = Ridge()
        self.settlement_model.fit(X, y_settlement)
        self.burn_model = LogisticRegression()
        self.burn_model.fit(X, y_burn)
        logger.info("TokenSettlementForecastModel v2 trained.")

    def predict(self, X):
        expected_reward = float(self.reward_model.predict(X)[0])
        expected_settlement_time = float(self.settlement_model.predict(X)[0])
        expected_burn = float(self.burn_model.predict_proba(X)[0, 1])
        expected_net = expected_reward - expected_burn
        # Uncertainty band: std of coefficients
        uncertainty = float((self.reward_model.coef_.std() + self.settlement_model.coef_.std()) / 2)
        # Top features: sorted by absolute weight
        feature_weights = dict(zip(self.features, self.reward_model.coef_))
        top_features = sorted(self.features, key=lambda f: abs(feature_weights[f]), reverse=True)[:3]
        rationale = f"Prediction based on weighted features: {top_features}."
        trace_id = str(uuid.uuid4())
        return {
            "prediction": {
                "expected_reward": expected_reward,
                "expected_burn": expected_burn,
                "expected_net": expected_net,
                "expected_settlement_time": datetime.fromtimestamp(expected_settlement_time)
            },
            "uncertainty": uncertainty,
            "top_features": top_features,
            "feature_weights": feature_weights,
            "rationale": rationale,
            "trace_id": trace_id
        }

    def save(self, path):
        joblib.dump(self.reward_model, f"{path}_reward.pkl")
        joblib.dump(self.settlement_model, f"{path}_settlement.pkl")
        joblib.dump(self.burn_model, f"{path}_burn.pkl")
        logger.info(f"Model saved to {path}")

    def load(self, path):
        self.reward_model = joblib.load(f"{path}_reward.pkl")
        self.settlement_model = joblib.load(f"{path}_settlement.pkl")
        self.burn_model = joblib.load(f"{path}_burn.pkl")
        logger.info(f"Model loaded from {path}")
