"""
Economic Reliability Model for ChainBridge ML.
Outputs reliability score, volatility index, risk-adjusted ROI, fraud likelihood, expected token multiplier, with rationale and traceability.
"""

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import ElasticNet
import joblib
import logging
import uuid

logger = logging.getLogger("maggie.models.economic_reliability_model")

class EconomicReliabilityModel:
    def __init__(self):
        self.reliability_model = None
        self.volatility_model = None
        self.fraud_model = None
        self.multiplier_model = None
        self.model_version = "v2.0"

    def train(self, df):
        self.features = [
            "carrier_performance", "lane_volatility", "risk_score", "reward_per_mile",
            "tokens_rewarded", "tokens_burned", "economic_reliability"
        ]
        X = df[self.features].fillna(0)
        y_reliability = df["economic_reliability"].fillna(0)
        y_volatility = df["lane_volatility"].fillna(0)
        y_fraud = df["fraud_likelihood"].fillna(0)
        y_multiplier = df["expected_token_multiplier"].fillna(0)
        self.reliability_model = GradientBoostingRegressor()
        self.reliability_model.fit(X, y_reliability)
        self.volatility_model = ElasticNet()
        self.volatility_model.fit(X, y_volatility)
        self.fraud_model = ElasticNet()
        self.fraud_model.fit(X, y_fraud)
        self.multiplier_model = ElasticNet()
        self.multiplier_model.fit(X, y_multiplier)
        logger.info("EconomicReliabilityModel v2 trained.")

    def predict(self, X):
        reliability_score = float(self.reliability_model.predict(X)[0])
        volatility_index = float(self.volatility_model.predict(X)[0])
        fraud_likelihood = float(self.fraud_model.predict(X)[0])
        expected_multiplier = float(self.multiplier_model.predict(X)[0])
        # Anomaly score: difference from mean reliability
        anomaly_score = abs(reliability_score - self.reliability_model.predict(X).mean())
        # Risk multiplier correction: based on volatility and fraud
        risk_multiplier_correction = float(volatility_index * (1 + fraud_likelihood))
        # Uncertainty: std of reliability model's feature importances
        uncertainty = float(np.std(self.reliability_model.feature_importances_)) if hasattr(self.reliability_model, "feature_importances_") else 0.0
        # Top features: sorted by importance
        if hasattr(self.reliability_model, "feature_importances_"):
            feature_weights = dict(zip(self.features, self.reliability_model.feature_importances_))
            top_features = sorted(self.features, key=lambda f: abs(feature_weights[f]), reverse=True)[:3]
        else:
            feature_weights = {f: 0.0 for f in self.features}
            top_features = self.features[:3]
        governance_rationale = f"Prediction based on weighted features: {top_features}."
        trace_id = str(uuid.uuid4())
        return {
            "reliability_score": reliability_score,
            "volatility_index": volatility_index,
            "fraud_likelihood": fraud_likelihood,
            "expected_multiplier": expected_multiplier,
            "anomaly_score": anomaly_score,
            "risk_multiplier_correction": risk_multiplier_correction,
            "uncertainty": uncertainty,
            "top_features": top_features,
            "feature_weights": feature_weights,
            "governance_rationale": governance_rationale,
            "trace_id": trace_id
        }

    def save(self, path):
        joblib.dump(self.reliability_model, f"{path}_reliability.pkl")
        joblib.dump(self.volatility_model, f"{path}_volatility.pkl")
        joblib.dump(self.fraud_model, f"{path}_fraud.pkl")
        joblib.dump(self.multiplier_model, f"{path}_multiplier.pkl")
        logger.info(f"Model saved to {path}")

    def load(self, path):
        self.reliability_model = joblib.load(f"{path}_reliability.pkl")
        self.volatility_model = joblib.load(f"{path}_volatility.pkl")
        self.fraud_model = joblib.load(f"{path}_fraud.pkl")
        self.multiplier_model = joblib.load(f"{path}_multiplier.pkl")
        logger.info(f"Model loaded from {path}")
