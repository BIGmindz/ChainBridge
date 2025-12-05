"""
CI test for Economic Anomaly Detector.
Validates anomaly score, outlier flag, top signals, explanation, and event type.
"""

import pandas as pd
# TODO: The following import is invalid (missing module)
from ml_engine.models.anomaly_detector import EconomicAnomalyDetector
from common.events.event_types import EventType

def test_anomaly_detector():
    df = pd.DataFrame({
        "token_net": [100],
        "reward_per_mile": [0.5],
        "risk_reward_ratio": [0.1],
        "event_timing_delta": [5.0]
    })
    model = EconomicAnomalyDetector()
    model.train(df)
    result = model.predict(df)
    assert "anomaly_score" in result
    assert "is_outlier" in result
    assert "top_signals" in result
    assert "explanation" in result
    assert "trace_id" in result
    assert EventType.ML_ANOMALY_DETECTED
    print("✓ Economic Anomaly Detector CI test passed.")
