"""
ChainIQ ML Training Dataset Utilities

Defines data structures and loaders for training ML models offline.
This module is ONLY used during model training, NOT in the request path.

Key Structures:
- ShipmentTrainingRow: A single training example (features + labels + metadata)
- Data loaders: Functions to load/generate training data

Safety: This module should NOT slow down FastAPI imports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.features import ShipmentFeaturesV0


class ShipmentTrainingRow(BaseModel):
    """
    A single training example for ChainIQ ML models.

    Combines:
    - Input features (ShipmentFeaturesV0)
    - Ground truth labels (outcomes like claims, disputes, delays)
    - Metadata (when recorded, data source, etc.)

    Used ONLY during offline training, not in production scoring.
    """

    # Input features (all 50+ fields from ShipmentFeaturesV0)
    features: ShipmentFeaturesV0

    # === Risk Model Labels ===
    # Binary outcomes indicating "bad" shipments
    had_claim: bool = Field(description="Did this shipment result in an insurance claim?")
    had_dispute: bool = Field(description="Did customer dispute charges or delivery?")
    severe_delay: bool = Field(description="Was shipment delayed > 48 hours beyond ETA?")
    loss_amount: float | None = Field(
        default=None,
        ge=0.0,
        description="Dollar value of loss (if any). None if no loss occurred.",
    )

    # === Anomaly Model Labels (optional) ===
    # Manual flags for known unusual shipments (semi-supervised learning)
    is_known_anomaly: bool = Field(
        default=False,
        description="Was this shipment manually flagged as anomalous by ops team?",
    )
    anomaly_type: Literal["route_deviation", "custody_gap", "temp_excursion", "other"] | None = Field(
        default=None,
        description="Type of anomaly if known. None if not anomalous or unsupervised.",
    )

    # === Metadata ===
    recorded_at: datetime = Field(description="When this label/outcome was recorded (not shipment start time)")
    data_source: Literal["production", "synthetic", "backfill"] = Field(
        default="production",
        description="Where this training row came from",
    )
    model_version_at_scoring: str | None = Field(
        default=None,
        description="What model version scored this shipment originally (for tracking)",
    )

    @property
    def bad_outcome(self) -> bool:
        """
        Composite risk label: did ANY bad thing happen?

        Used as the primary target for risk classification models.
        """
        return self.had_claim or self.had_dispute or self.severe_delay

    # === Convenience Properties (delegate to features) ===
    # These properties enable direct access like row.shipment_id instead of row.features.shipment_id

    @property
    def shipment_id(self) -> str:
        """Shipment identifier (delegates to features.shipment_id)."""
        return self.features.shipment_id

    @property
    def planned_transit_hours(self) -> float:
        """Planned transit hours (delegates to features.planned_transit_hours)."""
        return self.features.planned_transit_hours

    @property
    def actual_transit_hours(self) -> float | None:
        """Actual transit hours (delegates to features.actual_transit_hours)."""
        return self.features.actual_transit_hours

    @property
    def eta_deviation_hours(self) -> float:
        """ETA deviation hours (delegates to features.eta_deviation_hours)."""
        return self.features.eta_deviation_hours

    @property
    def num_route_deviations(self) -> int:
        """Number of route deviations (delegates to features.num_route_deviations)."""
        return self.features.num_route_deviations

    @property
    def max_route_deviation_km(self) -> float:
        """Max route deviation km (delegates to features.max_route_deviation_km)."""
        return self.features.max_route_deviation_km

    @property
    def handoff_count(self) -> int:
        """Handoff count (delegates to features.handoff_count)."""
        return self.features.handoff_count

    @property
    def total_dwell_hours(self) -> float:
        """Total dwell hours (delegates to features.total_dwell_hours)."""
        return self.features.total_dwell_hours

    @property
    def max_single_dwell_hours(self) -> float:
        """Max single dwell hours (delegates to features.max_single_dwell_hours)."""
        return self.features.max_single_dwell_hours

    @property
    def max_custody_gap_hours(self) -> float:
        """Max custody gap hours (delegates to features.max_custody_gap_hours)."""
        return self.features.max_custody_gap_hours

    @property
    def temp_mean(self) -> float | None:
        """Temperature mean (delegates to features.temp_mean)."""
        return self.features.temp_mean

    @property
    def temp_std(self) -> float | None:
        """Temperature std (delegates to features.temp_std)."""
        return self.features.temp_std

    @property
    def temp_out_of_range_pct(self) -> float | None:
        """Temperature out of range % (delegates to features.temp_out_of_range_pct)."""
        return self.features.temp_out_of_range_pct

    @property
    def sensor_uptime_pct(self) -> float | None:
        """Sensor uptime % (delegates to features.sensor_uptime_pct)."""
        return self.features.sensor_uptime_pct

    @property
    def missing_required_docs(self) -> int:
        """Missing required docs (delegates to features.missing_required_docs)."""
        return self.features.missing_required_docs

    @property
    def delay_flag(self) -> int:
        """Delay flag (delegates to features.delay_flag)."""
        return self.features.delay_flag

    @property
    def prior_losses_flag(self) -> int:
        """Prior losses flag (delegates to features.prior_losses_flag)."""
        return self.features.prior_losses_flag

    @property
    def carrier_on_time_pct_90d(self) -> float:
        """Carrier on-time % 90d (delegates to features.carrier_on_time_pct_90d)."""
        return self.features.carrier_on_time_pct_90d

    @property
    def shipper_on_time_pct_90d(self) -> float:
        """Shipper on-time % 90d (delegates to features.shipper_on_time_pct_90d)."""
        return self.features.shipper_on_time_pct_90d

    @property
    def lane_sentiment_score(self) -> float:
        """Lane sentiment score (delegates to features.lane_sentiment_score)."""
        return self.features.lane_sentiment_score

    @property
    def sentiment_trend_7d(self) -> float:
        """Sentiment trend 7d (delegates to features.sentiment_trend_7d)."""
        return self.features.sentiment_trend_7d

    @property
    def sentiment_volatility_30d(self) -> float:
        """Sentiment volatility 30d (delegates to features.sentiment_volatility_30d)."""
        return self.features.sentiment_volatility_30d

    @property
    def macro_logistics_sentiment_score(self) -> float:
        """Macro logistics sentiment score (delegates to features.macro_logistics_sentiment_score)."""
        return self.features.macro_logistics_sentiment_score


def build_training_row_from_features(
    features: ShipmentFeaturesV0,
    label: bool,
    *,
    metadata: dict | None = None,
) -> ShipmentTrainingRow:
    """
    Convenience builder for creating training rows from features + simple label.

    Args:
        features: Full ShipmentFeaturesV0 instance
        label: True if this was a "bad" shipment (claim/dispute/delay)
        metadata: Optional dict with keys like 'recorded_at', 'data_source'

    Returns:
        ShipmentTrainingRow with label mapped to had_claim/had_dispute/severe_delay

    Example:
        >>> row = build_training_row_from_features(
        ...     features=some_features,
        ...     label=True,  # Bad outcome
        ...     metadata={'data_source': 'synthetic'}
        ... )
    """
    metadata = metadata or {}

    # Simple heuristic: if label is True, assume it's a severe delay
    # (In real backfill, you'd map specific outcome types)
    return ShipmentTrainingRow(
        features=features,
        had_claim=False,  # Default False unless metadata says otherwise
        had_dispute=False,
        severe_delay=label,  # Map the simple boolean here
        loss_amount=None,
        recorded_at=metadata.get("recorded_at", datetime.now()),
        data_source=metadata.get("data_source", "production"),
        model_version_at_scoring=metadata.get("model_version_at_scoring"),
    )


def load_training_data(path: str) -> list[ShipmentTrainingRow]:
    """
    Load training data from a file.

    Args:
        path: File path (CSV, JSON, or parquet)

    Returns:
        List of ShipmentTrainingRow instances

    Raises:
        FileNotFoundError: If path doesn't exist
        ValueError: If file format is unsupported or invalid

    TODO (v0.2): This is a stub. Real implementation in PAC-004 will:
        - Support CSV/JSON/parquet formats
        - Use pandas for efficient loading
        - Validate schema matches ShipmentTrainingRow
        - Handle missing labels gracefully

    Example:
        >>> rows = load_training_data("data/shipments_2025_train.csv")
        >>> print(f"Loaded {len(rows)} training examples")
    """
    import os

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Training data not found at {path}. " "For v0.2, use generate_synthetic_training_data() to create sample data."
        )

    # TODO: Implement real loading logic
    # For now, just raise a clear error
    raise NotImplementedError("load_training_data() not yet implemented. " "Use generate_synthetic_training_data() for v0.2 smoke tests.")


def generate_synthetic_training_data(
    n_samples: int = 100,
    *,
    positive_rate: float = 0.15,
    seed: int | None = None,
) -> list[ShipmentTrainingRow]:
    """
    Generate synthetic training data for testing and development.

    Uses ShipmentFeaturesV0 schema with probabilistic rules:
    - High delay → higher chance of bad_outcome
    - Prior losses → higher chance of bad_outcome
    - Low sentiment → higher chance of bad_outcome

    Args:
        n_samples: Number of training rows to generate
        positive_rate: Target fraction of bad_outcome=True examples (0-1)
        seed: Random seed for reproducibility

    Returns:
        List of synthetic ShipmentTrainingRow instances

    Example:
        >>> rows = generate_synthetic_training_data(n_samples=1000, positive_rate=0.2)
        >>> print(f"Generated {len(rows)} rows, {sum(r.bad_outcome for r in rows)} positive")
    """
    import random

    if seed is not None:
        random.seed(seed)

    rows = []
    corridors = ["US-MX", "CN-NL", "US-CA", "DE-FR"]
    modes = ["truck", "ocean", "air"]
    commodities = ["electronics", "textiles", "food", "machinery"]
    financing_types = ["LC", "OA", "DP"]

    for i in range(n_samples):
        # Generate base features with some randomness
        delay_flag = random.random() < 0.3  # 30% of shipments delayed
        prior_losses = random.random() < 0.1  # 10% have prior losses
        low_sentiment = random.random() < 0.25  # 25% low sentiment

        # Probabilistic bad outcome based on risk factors
        risk_score = 0.05  # Base 5% bad rate
        if delay_flag:
            risk_score += 0.3
        if prior_losses:
            risk_score += 0.4
        if low_sentiment:
            risk_score += 0.2

        bad_outcome = random.random() < min(risk_score, 0.95)  # Cap at 95%

        # Create features
        features = ShipmentFeaturesV0(
            shipment_id=f"SYNTH-{i:05d}",
            corridor=random.choice(corridors),
            origin_country=random.choice(corridors).split("-")[0],
            destination_country=random.choice(corridors).split("-")[1],
            mode=random.choice(modes),
            commodity_category=random.choice(commodities),
            financing_type=random.choice(financing_types),
            counterparty_risk_bucket=random.choice(["low", "medium", "high"]),
            planned_transit_hours=48.0 + random.gauss(0, 10),
            actual_transit_hours=48.0 + random.gauss(0, 15) + (24 if delay_flag else 0),
            eta_deviation_hours=random.gauss(0, 5) + (12 if delay_flag else 0),
            num_route_deviations=random.randint(0, 3),
            max_route_deviation_km=random.uniform(0, 50),
            total_dwell_hours=random.uniform(2, 24),
            max_single_dwell_hours=random.uniform(1, 12),
            handoff_count=random.randint(2, 6),
            max_custody_gap_hours=random.uniform(0.5, 8),
            delay_flag=1 if delay_flag else 0,
            has_iot_telemetry=random.choice([0, 1]),
            temp_mean=random.uniform(18, 25),
            temp_std=random.uniform(0.5, 3),
            temp_min=random.uniform(15, 20),
            temp_max=random.uniform(22, 28),
            temp_out_of_range_pct=random.uniform(0, 0.1),
            sensor_uptime_pct=random.uniform(0.8, 1.0),
            doc_count=random.randint(8, 15),
            missing_required_docs=random.randint(0, 2),
            duplicate_doc_flag=random.choice([0, 1]),
            doc_inconsistency_flag=random.choice([0, 1]),
            doc_age_days=random.uniform(1, 10),
            collateral_value=random.uniform(50000, 500000),
            collateral_value_bucket=random.choice(["low", "medium", "high"]),
            shipper_on_time_pct_90d=random.uniform(0.6, 0.98),
            carrier_on_time_pct_90d=random.uniform(0.6, 0.98),
            corridor_disruption_index_90d=random.uniform(0.1, 0.8),
            prior_exceptions_count_180d=random.randint(0, 10),
            prior_losses_flag=1 if prior_losses else 0,
            lane_sentiment_score=random.uniform(0.2, 0.8) - (0.3 if low_sentiment else 0),
            macro_logistics_sentiment_score=random.uniform(0.3, 0.7),
            sentiment_trend_7d=random.uniform(-0.2, 0.2),
            sentiment_volatility_30d=random.uniform(0.1, 0.4),
            sentiment_provider="synthetic_v0",
        )

        # Create training row
        row = ShipmentTrainingRow(
            features=features,
            had_claim=bad_outcome and random.random() < 0.4,  # 40% of bad → claim
            had_dispute=bad_outcome and random.random() < 0.3,  # 30% of bad → dispute
            severe_delay=bad_outcome and delay_flag,  # Delayed bad outcomes
            loss_amount=random.uniform(1000, 50000) if bad_outcome else None,
            recorded_at=datetime.now(),
            data_source="synthetic",
            model_version_at_scoring="0.1.0",
        )

        rows.append(row)

    return rows


# Example usage for testing
if __name__ == "__main__":
    # Generate some synthetic data
    print("Generating 100 synthetic training rows...")
    rows = generate_synthetic_training_data(n_samples=100, positive_rate=0.2, seed=42)

    print(f"Total rows: {len(rows)}")
    print(f"Bad outcomes: {sum(r.bad_outcome for r in rows)}")
    print(f"Had claims: {sum(r.had_claim for r in rows)}")
    print(f"Severe delays: {sum(r.severe_delay for r in rows)}")

    # Show first example
    print("\nFirst training row:")
    print(f"  Shipment ID: {rows[0].features.shipment_id}")
    print(f"  Corridor: {rows[0].features.corridor}")
    print(f"  Delay flag: {rows[0].features.delay_flag}")
    print(f"  Bad outcome: {rows[0].bad_outcome}")
    print(f"  Labels: claim={rows[0].had_claim}, dispute={rows[0].had_dispute}, delay={rows[0].severe_delay}")
