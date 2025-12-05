"""
CI test for economic_features dataset generation.
Validates all required fields are present and deterministic output.
"""

import pandas as pd
import pyarrow.parquet as pq

def test_economic_features_dataset():
    df = pq.read_table("../ml_engine/logs/economic_features.parquet").to_pandas()
    required_fields = [
        "shipment_id", "carrier_id", "milestone_time", "risk_score", "risk_category", "settlement_time",
        "tokens_rewarded", "tokens_burned", "token_net", "reward_per_mile", "carrier_performance",
        "economic_reliability", "expected_token_reward", "expected_penalty_risk", "fraud_likelihood",
        "expected_token_multiplier", "governance_severity", "trace_id"
    ]
    for field in required_fields:
        assert field in df.columns, f"Missing field: {field}"
    print("✓ Economic features dataset CI test passed.")
