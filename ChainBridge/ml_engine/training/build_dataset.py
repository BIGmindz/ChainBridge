"""
Daily training dataset generator for ChainBridge ML.
Reads last 24h events, joins with feature store, outputs ML-ready Parquet.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from ..ingestion.config import PARQUET_PATH, POSTGRES_URI
from ..feature_store.models import ShipmentFeature, CarrierFeature, RiskFinanceFeature
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger("maggie.training.build_dataset")
engine = create_engine(POSTGRES_URI)
Session = sessionmaker(bind=engine)

# Read last 24h events from Parquet
now = datetime.utcnow()
start_time = now - timedelta(hours=24)

def build_daily_dataset():
    events = pq.read_table(PARQUET_PATH).to_pandas()
    events = events[events["timestamp"] >= start_time.isoformat()]
    session = Session()
    # Feature store joins
    shipment_features = pd.read_sql(session.query(ShipmentFeature).statement, session.bind)
    carrier_features = pd.read_sql(session.query(CarrierFeature).statement, session.bind)
    risk_features = pd.read_sql(session.query(RiskFinanceFeature).statement, session.bind)

    # Load settlement events (from Parquet or DB)
    try:
        settlement_events = pq.read_table("../ml_engine/logs/settlement_events.parquet").to_pandas()
    except Exception:
        settlement_events = pd.DataFrame()

    # Load streaming features (from aggregator output)
    try:
        streaming_features = pd.read_parquet("../ml_engine/logs/streaming_features.parquet")
    except Exception:
        streaming_features = pd.DataFrame()

    # Load lane attributes (from DB or static file)
    try:
        lane_attributes = pd.read_parquet("../ml_engine/logs/lane_attributes.parquet")
    except Exception:
        lane_attributes = pd.DataFrame()

    # Merge all features
    dataset = events.merge(shipment_features, on="shipment_id", how="left")
    dataset = dataset.merge(carrier_features, on="carrier_id", how="left")
    dataset = dataset.merge(risk_features, left_on="shipment_id", right_on="shipment_id", how="left")
    if not settlement_events.empty:
        dataset = dataset.merge(settlement_events, on="shipment_id", how="left", suffixes=("", "_settlement"))
    if not streaming_features.empty:
        dataset = dataset.merge(streaming_features, on="shipment_id", how="left", suffixes=("", "_stream"))
    if not lane_attributes.empty:
        dataset = dataset.merge(lane_attributes, on=["origin", "destination"], how="left", suffixes=("", "_lane"))

    # Output Parquet
    table = pa.Table.from_pandas(dataset)
    pq.write_table(table, "../ml_engine/logs/daily_training_dataset.parquet")
    # Output economic features
    economic_features = dataset[[
        "shipment_id", "carrier_id", "milestone_time", "risk_score", "risk_category", "settlement_time",
        "tokens_rewarded", "tokens_burned", "token_net", "reward_per_mile", "carrier_performance",
        "economic_reliability", "expected_token_reward", "expected_penalty_risk", "fraud_likelihood",
        "expected_token_multiplier", "governance_severity", "trace_id"
    ]].copy()
    pq.write_table(pa.Table.from_pandas(economic_features), "../ml_engine/logs/economic_features.parquet")
    logger.info(f"Daily dataset generated: {len(dataset)} rows, columns: {list(dataset.columns)}. Economic features: {len(economic_features)} rows.")

if __name__ == "__main__":
    build_daily_dataset()
