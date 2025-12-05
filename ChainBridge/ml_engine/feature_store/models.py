"""
SQLAlchemy models for ML feature store.
Shipment, Carrier, Risk/Finance features.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Float, Integer, DateTime

Base = declarative_base()

class ShipmentFeature(Base):
    __tablename__ = "shipment_features"
    shipment_id = Column(String, primary_key=True)
    dwell_time = Column(Float)
    eta_drift = Column(Float)
    iot_alerts_count = Column(Integer)
    delay_severity = Column(Float)
    origin = Column(String)
    destination = Column(String)
    lane_volatility = Column(Float)
    event_velocity = Column(Float)
    token_net = Column(Float)
    reward_per_mile = Column(Float)
    token_volatility_index = Column(Float)
    risk_reward_ratio = Column(Float)
    token_burn_rate = Column(Float)
    economic_reliability = Column(Float)
    expected_token_reward = Column(Float)
    expected_penalty_risk = Column(Float)
    settlement_cycle_entropy = Column(Float)
    reward_distribution_kurtosis = Column(Float)
    event_timing_delta = Column(Float)
    ml_confidence_band = Column(Float)
    economic_reliability_score = Column(Float)
    version = Column(Integer)
    updated_at = Column(DateTime)

class CarrierFeature(Base):
    __tablename__ = "carrier_features"
    carrier_id = Column(String, primary_key=True)
    on_time_pct = Column(Float)
    anomaly_freq = Column(Float)
    claim_freq = Column(Float)
    avg_settlement_delay = Column(Float)
    version = Column(Integer)
    updated_at = Column(DateTime)

class RiskFinanceFeature(Base):
    __tablename__ = "risk_finance_features"
    risk_score_drift = Column(Float)
    fraud_signal_freq = Column(Float)
    settlement_timing_var = Column(Float)
    token_rewards_per_shipment = Column(Float)
    token_volatility_index = Column(Float)
    risk_reward_ratio = Column(Float)
    token_burn_rate = Column(Float)
    economic_reliability = Column(Float)
    version = Column(Integer)
    updated_at = Column(DateTime)
