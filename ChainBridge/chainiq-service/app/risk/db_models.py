"""SQLAlchemy models for ChainIQ risk metrics.

These models mirror the contracts in app/risk/metrics_schemas.py and are designed
to be compatible with Postgres (production) and SQLite (testing).
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

# Create a local Base since chainiq-service doesn't have a shared one yet.
# If a shared app.database module is added later, this should be refactored to use it.
Base = declarative_base()


class RiskEvaluation(Base):
    """Persistence model for individual risk evaluations."""

    __tablename__ = "risk_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    model_version = Column(String, nullable=False)

    # Context identifiers
    shipment_id = Column(String, nullable=False, index=True)
    carrier_id = Column(String, nullable=False, index=True)
    lane_id = Column(String, nullable=False)

    # Scoring results
    risk_score = Column(Integer, nullable=False)
    risk_band = Column(String, nullable=False)

    # Rich data (stored as JSON)
    primary_reasons = Column(JSON, nullable=False)
    features_snapshot = Column(JSON, nullable=False)

    # Outcome fields for metrics computation (populated by labeling/ETL)
    is_incident = Column(Boolean, nullable=True)
    is_loss = Column(Boolean, nullable=True)
    loss_value = Column(Float, nullable=True)

    def __repr__(self):
        return f"<RiskEvaluation(id={self.evaluation_id}, score={self.risk_score})>"


class RiskModelMetrics(Base):
    """Persistence model for aggregated risk model performance metrics."""

    __tablename__ = "risk_model_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String, nullable=False, index=True)

    # Time window
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)

    # Basic aggregates
    eval_count = Column(Integer, nullable=False)
    avg_score = Column(Float, nullable=True)

    # Percentiles
    p50_score = Column(Float, nullable=True)
    p90_score = Column(Float, nullable=True)
    p99_score = Column(Float, nullable=True)

    # Band distribution
    risk_band_counts = Column(JSON, nullable=False, default=dict)

    # Maggie-style metrics
    critical_incident_recall = Column(Float, nullable=True)
    high_risk_precision = Column(Float, nullable=True)
    ops_workload_percent = Column(Float, nullable=True)
    incident_rate_low = Column(Float, nullable=True)
    incident_rate_medium = Column(Float, nullable=True)
    incident_rate_high = Column(Float, nullable=True)
    calibration_monotonic = Column(Integer, nullable=True)  # SQLite bool workaround
    calibration_ratio_high_vs_low = Column(Float, nullable=True)
    loss_value_coverage_pct = Column(Float, nullable=True)

    # Red flag results
    has_failures = Column(Integer, nullable=True)  # SQLite bool workaround
    has_warnings = Column(Integer, nullable=True)  # SQLite bool workaround
    fail_messages = Column(JSON, nullable=True)
    warning_messages = Column(JSON, nullable=True)

    # Metadata
    data_freshness_ts = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<RiskModelMetrics(version={self.model_version}, window={self.window_start})>"
