"""
Economic Anomaly Detector for ChainBridge ML.
Isolation Forest, interpretable rationale, top features.
"""

import pandas as pd
from sklearn.ensemble import IsolationForest
import logging
import uuid

logger = logging.getLogger("maggie.models.anomaly_detector")

class EconomicAnomalyDetector:
    def __init__(self):
        self.model = None
        self.model_version = "v1.0"

    def train(self, df):
        features = ["token_net", "reward_per_mile", "risk_reward_ratio", "event_timing_delta"]
        X = df[features].fillna(0)
        self.model = IsolationForest(contamination=0.05)
        self.model.fit(X)
        logger.info("EconomicAnomalyDetector trained.")

    def predict(self, X):
        anomaly_score = float(self.model.decision_function(X)[0])
        is_outlier = bool(self.model.predict(X)[0] == -1)
        top_signals = self._top_features(X)
        explanation = f"Anomaly detected due to: {', '.join(top_signals)}" if is_outlier else "No anomaly detected."
        trace_id = str(uuid.uuid4())
        return {
            "anomaly_score": anomaly_score,
            "is_outlier": is_outlier,
            "top_signals": top_signals,
            "explanation": explanation,
            "trace_id": trace_id
        }

    def _top_features(self, X):
        # Simple feature ranking by absolute value
        vals = X.iloc[0].abs()
        ranked = vals.sort_values(ascending=False)
        return list(ranked.index[:3])
