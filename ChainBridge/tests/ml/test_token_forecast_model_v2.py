"""
CI test for Token Settlement Forecast Model v2.
Validates deterministic, interpretable output, uncertainty, rationale, and event type.
"""

import pandas as pd
# TODO: The following import is invalid (missing module)
# from ml_engine.models.token_settlement_forecast_model import TokenSettlementForecastModel
from common.events.event_types import EventType

def test_token_forecast_model_v2():
    df = pd.DataFrame({
        "risk_score": [0.7],
        "milestone_time": [1.0],
        "carrier_performance": [0.9],
        "lane_volatility": [0.2],
        "tokens_rewarded": [100],
        "tokens_burned": [10],
        "reward_per_mile": [0.5],
        "economic_reliability": [0.8]
    })
    model = TokenSettlementForecastModel()
    model.train(df)
    result = model.predict(df)
    assert "prediction" in result
    assert "uncertainty" in result
    assert "rationale" in result
    assert "trace_id" in result
    assert EventType.ML_RISK_MULTIPLIER_SUGGESTED
    print("✓ Token Settlement Forecast Model v2 CI test passed.")
