# ChainIQ v0.1 Specification

> **🩷 MAGGIE — GID-10 — Machine Learning & Applied AI Lead**
>
> This document defines the glass-box risk brain for ChainBridge logistics operations.
> Version: 0.1 | Status: DRAFT | Last Updated: 2024-12-07

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Input Schema (ShipmentRiskContext)](#2-input-schema-shipmentriskcontext)
3. [Output Schema (ShipmentRiskAssessment)](#3-output-schema-shipmentriskassessment)
4. [Model Architecture](#4-model-architecture)
5. [Feature Engineering](#5-feature-engineering)
6. [Decision Mapping](#6-decision-mapping)
7. [Explanation Generation](#7-explanation-generation)
8. [API Contract](#8-api-contract)
9. [Evaluation Plan (Retrospective Pilot)](#9-evaluation-plan-retrospective-pilot)
10. [Integration Notes](#10-integration-notes)

---

## 1. Executive Summary

### BLUF (Bottom Line Up Front)

ChainIQ v0.1 is a **glass-box risk scoring engine** that predicts shipment disruption probability and translates it into actionable decisions for ChainPay settlement policies. It prioritizes:

- **Explainability**: Every score has human-readable factor attributions
- **Commercial Impact**: Directly reduces bad-freight payouts and operator cognitive load
- **Robustness**: Simple, interpretable models that degrade gracefully under domain shift

### Commercial ROI Targets

| Metric | Target | How Measured |
|--------|--------|--------------|
| Bad-freight payout reduction | 15-25% | % of late/damaged shipments caught in top risk decile |
| Operator time saved | 30% | Fewer manual reviews via auto-approve on low-risk |
| False positive rate | <20% | Shipments flagged HOLD/ESCALATE that were actually fine |

### Glass-Box Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ChainIQ v0.1 Risk Brain                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ ShipmentRisk │───▶│   Feature    │───▶│  Gradient Boosted    │  │
│  │   Context    │    │  Engineering │    │  Tree (XGBoost) +    │  │
│  │   (Input)    │    │              │    │  SHAP Explanations   │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                      │              │
│                                                      ▼              │
│                      ┌──────────────────────────────────────────┐  │
│                      │          Explanation Engine              │  │
│                      │  • Top Factors (SHAP values)             │  │
│                      │  • Human-readable summaries              │  │
│                      │  • Risk component breakdown              │  │
│                      └──────────────────┬───────────────────────┘  │
│                                         │                          │
│                                         ▼                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  Decision Engine                              │  │
│  │  risk_score → APPROVE | HOLD | TIGHTEN_TERMS | ESCALATE      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                         │                          │
│                                         ▼                          │
│                      ┌──────────────────────────────────────────┐  │
│                      │       ShipmentRiskAssessment             │  │
│                      │              (Output)                     │  │
│                      └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Input Schema (ShipmentRiskContext)

This is the contract Cody's backend must fulfill when calling ChainIQ.

### Primary Schema

```python
from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class ShipmentEventLite(BaseModel):
    """Minimal event representation for risk scoring."""
    type: str = Field(
        ...,
        description="Event type code",
        examples=["DEPARTED_PORT", "ARRIVED_PORT", "CUSTOMS_HOLD", "TEMPERATURE_ALARM",
                  "VESSEL_DELAY", "PORT_CONGESTION", "DOCUMENTATION_ISSUE"]
    )
    timestamp: datetime
    location: Optional[str] = Field(None, description="Location code or name")
    metadata: Optional[dict] = Field(default_factory=dict, description="Event-specific data")


class ShipmentRiskContext(BaseModel):
    """
    Input context for ChainIQ risk scoring.

    Required fields are marked with `...` (no default).
    Optional fields have sensible defaults or None.
    """

    # === IDENTIFIERS ===
    shipment_id: str = Field(..., description="Unique shipment identifier")
    tenant_id: str = Field(..., description="Customer tenant ID for partitioning/logging")

    # === MODE & ROUTE ===
    mode: Literal["OCEAN", "TRUCK", "AIR", "RAIL", "INTERMODAL"] = Field(
        ..., description="Primary transport mode"
    )
    origin_country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    origin_region: Optional[str] = Field(None, description="State/province/port region")
    destination_country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    destination_region: Optional[str] = Field(None, description="State/province/port region")
    lane_id: Optional[str] = Field(
        None,
        description="Pre-computed lane identifier (or derived from O/D pair)"
    )

    # === TIMING ===
    planned_departure: datetime = Field(..., description="Scheduled departure datetime (UTC)")
    planned_arrival: datetime = Field(..., description="Scheduled arrival datetime (UTC)")
    actual_departure: Optional[datetime] = Field(None, description="Actual departure (if known)")
    actual_arrival: Optional[datetime] = Field(None, description="Actual arrival (if completed)")

    # === CARRIER & LOGISTICS ===
    carrier_code: Optional[str] = Field(None, description="SCAC or carrier identifier")
    distance_km: Optional[float] = Field(None, ge=0, description="Route distance in kilometers")

    # === CARGO CHARACTERISTICS ===
    commodity_type: Optional[str] = Field(None, description="Commodity classification code")
    temperature_controlled: Optional[bool] = Field(False, description="Requires temp control")
    value_usd: Optional[float] = Field(None, ge=0, description="Declared cargo value in USD")

    # === HISTORICAL/CONTEXTUAL FEATURES ===
    events: List[ShipmentEventLite] = Field(
        default_factory=list,
        description="Timeline of events for this shipment"
    )
    prior_incident_rate_lane: Optional[float] = Field(
        None, ge=0, le=1,
        description="Historical incident rate for this lane (0-1)"
    )
    prior_incident_rate_carrier: Optional[float] = Field(
        None, ge=0, le=1,
        description="Historical incident rate for this carrier (0-1)"
    )
    seasonality_index: Optional[float] = Field(
        None,
        description="Seasonal risk multiplier (1.0 = baseline)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-2024-001234",
                "tenant_id": "tenant-acme-corp",
                "mode": "OCEAN",
                "origin_country": "CN",
                "origin_region": "Shanghai",
                "destination_country": "US",
                "destination_region": "Los Angeles",
                "planned_departure": "2024-12-01T08:00:00Z",
                "planned_arrival": "2024-12-21T18:00:00Z",
                "carrier_code": "MAEU",
                "distance_km": 11500,
                "commodity_type": "ELECTRONICS",
                "temperature_controlled": False,
                "value_usd": 250000,
                "events": [
                    {"type": "DEPARTED_PORT", "timestamp": "2024-12-01T10:30:00Z", "location": "CNSHA"}
                ],
                "prior_incident_rate_lane": 0.12,
                "prior_incident_rate_carrier": 0.08
            }
        }
```

### Field Requirements Matrix

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| shipment_id | ✅ | - | Must be unique per request |
| tenant_id | ✅ | - | Used for logging, not scoring |
| mode | ✅ | - | Affects model path selection |
| origin_country | ✅ | - | ISO 3166-1 alpha-2 |
| destination_country | ✅ | - | ISO 3166-1 alpha-2 |
| planned_departure | ✅ | - | UTC datetime |
| planned_arrival | ✅ | - | UTC datetime |
| All others | ❌ | None/0/[] | Model handles gracefully |

---

## 3. Output Schema (ShipmentRiskAssessment)

This is the glass-box contract that Sonny (UI) and Cody (backend) rely on.

### Primary Schema

```python
from datetime import datetime
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

class TopFactor(BaseModel):
    """Single explainability factor contributing to risk score."""
    feature_name: str = Field(..., description="Internal feature name")
    direction: Literal["INCREASES_RISK", "DECREASES_RISK"] = Field(
        ..., description="Impact direction on risk"
    )
    magnitude: float = Field(
        ..., ge=0, le=100,
        description="Relative contribution (0-100 scale)"
    )
    human_label: str = Field(
        ...,
        description="Human-readable explanation",
        examples=["Lane historically experiences 15% delays", "Peak shipping season"]
    )


class ShipmentRiskAssessment(BaseModel):
    """
    ChainIQ v0.1 output for a single shipment risk assessment.

    All scores are 0-100 scale where higher = more risk (except resilience).
    """

    # === IDENTIFIERS ===
    shipment_id: str = Field(..., description="Echo of input shipment_id")
    assessed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of this assessment"
    )
    model_version: str = Field(default="chainiq-v0.1", description="Model version tag")

    # === COMPOSITE RISK SCORES ===
    risk_score: float = Field(
        ..., ge=0, le=100,
        description="Overall risk score (0=safe, 100=critical)"
    )
    operational_risk: float = Field(
        ..., ge=0, le=100,
        description="Risk of delays, routing issues, capacity problems"
    )
    financial_risk: float = Field(
        ..., ge=0, le=100,
        description="Risk of cost overruns, claims, value loss"
    )
    fraud_risk: float = Field(
        ..., ge=0, le=100,
        description="Risk of fraudulent documentation or activity"
    )
    esg_risk: float = Field(
        default=0.0, ge=0, le=100,
        description="Environmental/social/governance risk (placeholder for v0)"
    )

    # === RESILIENCE (INVERSE OF RISK) ===
    resilience_score: float = Field(
        ..., ge=0, le=100,
        description="Overall resilience (100=very resilient, 0=fragile)"
    )

    # === DECISION ===
    decision: Literal["APPROVE", "HOLD", "TIGHTEN_TERMS", "ESCALATE"] = Field(
        ..., description="Recommended action based on risk thresholds"
    )
    decision_confidence: float = Field(
        ..., ge=0, le=1,
        description="Model confidence in this decision (0-1)"
    )

    # === EXPLAINABILITY ===
    top_factors: List[TopFactor] = Field(
        ..., min_length=1, max_length=10,
        description="Top contributing factors to risk score"
    )
    summary_reason: str = Field(
        ..., max_length=500,
        description="Natural language summary of risk assessment"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Risk tags for filtering/grouping",
        examples=[["PORT_CONGESTION", "LANE_VOLATILE", "HIGH_VALUE"]]
    )

    # === METADATA ===
    data_quality_score: float = Field(
        default=1.0, ge=0, le=1,
        description="Quality of input data (1=complete, 0=sparse)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "shipment_id": "SHP-2024-001234",
                "assessed_at": "2024-12-07T14:30:00Z",
                "model_version": "chainiq-v0.1",
                "risk_score": 67.5,
                "operational_risk": 72.0,
                "financial_risk": 58.0,
                "fraud_risk": 12.0,
                "esg_risk": 0.0,
                "resilience_score": 32.5,
                "decision": "TIGHTEN_TERMS",
                "decision_confidence": 0.82,
                "top_factors": [
                    {
                        "feature_name": "lane_incident_rate",
                        "direction": "INCREASES_RISK",
                        "magnitude": 35.2,
                        "human_label": "This lane has 15% historical delay rate"
                    },
                    {
                        "feature_name": "seasonal_peak",
                        "direction": "INCREASES_RISK",
                        "magnitude": 22.1,
                        "human_label": "December is peak shipping season with congestion"
                    },
                    {
                        "feature_name": "carrier_reliability",
                        "direction": "DECREASES_RISK",
                        "magnitude": 15.0,
                        "human_label": "Carrier MAEU has strong on-time performance"
                    }
                ],
                "summary_reason": "Medium-high risk due to volatile Shanghai-LA lane during peak season. Carrier reliability partially offsets lane risk. Recommend tightened payment terms.",
                "tags": ["LANE_VOLATILE", "PEAK_SEASON", "HIGH_VALUE"]
            }
        }
```

### Score Interpretation Guide

| Score Range | Risk Level | Typical Decision |
|-------------|------------|------------------|
| 0-30 | Low | APPROVE |
| 30-60 | Medium | APPROVE (with monitoring) |
| 60-80 | High | TIGHTEN_TERMS |
| 80-100 | Critical | HOLD / ESCALATE |

---

## 4. Model Architecture

### 4.1 Target Definition

**Primary Task**: Binary classification predicting probability of "bad outcome"

```python
# Bad outcome definition (configurable)
BAD_OUTCOME_THRESHOLDS = {
    "late_days": 3,           # Late by > 3 days = bad
    "damage_claim": True,     # Any damage claim = bad
    "cost_overrun_pct": 0.15, # Cost > 15% over quote = bad
}

def is_bad_outcome(shipment: dict) -> bool:
    """Label function for training data."""
    if shipment.get("days_late", 0) > BAD_OUTCOME_THRESHOLDS["late_days"]:
        return True
    if shipment.get("has_damage_claim", False):
        return True
    if shipment.get("cost_overrun_pct", 0) > BAD_OUTCOME_THRESHOLDS["cost_overrun_pct"]:
        return True
    return False
```

### 4.2 Model Family Selection

**Primary Model**: Gradient Boosted Trees (XGBoost)
- Handles mixed feature types well
- Native feature importance
- SHAP integration for explanations
- Fast inference

**Backup Model**: Logistic Regression
- Fully interpretable coefficients
- Used when explainability is paramount
- Fallback for sparse-data tenants

### 4.3 Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GLOBAL BASE MODEL                            │
│  • Trained on anonymized public + aggregate customer data       │
│  • Captures universal patterns: seasonality, mode effects, etc. │
│  • ~80% of predictive power                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TENANT-SPECIFIC OVERLAY                         │
│  • Fine-tuned on tenant's historical data (when available)      │
│  • Captures tenant-specific carrier relationships, lanes        │
│  • Additive adjustment to base predictions                      │
│  • Stored separately, never leaks to other tenants              │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Model Configuration

```python
MODEL_CONFIG = {
    "xgboost": {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
        "min_child_weight": 10,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
    },
    "logistic": {
        "penalty": "l2",
        "C": 1.0,
        "max_iter": 1000,
        "random_state": 42,
    },
    "calibration": {
        "method": "isotonic",  # Better for well-calibrated probabilities
        "cv": 5,
    }
}
```

---

## 5. Feature Engineering

### 5.1 Feature Groups

```python
FEATURE_GROUPS = {
    "lane": [
        "origin_country_encoded",
        "destination_country_encoded",
        "origin_region_encoded",
        "destination_region_encoded",
        "lane_id_encoded",
        "distance_km",
        "distance_bucket",  # SHORT/MEDIUM/LONG
        "is_cross_border",
        "lane_historical_delay_rate",
        "lane_historical_claim_rate",
    ],

    "carrier": [
        "carrier_code_encoded",
        "carrier_historical_delay_rate",
        "carrier_historical_claim_rate",
        "carrier_volume_tier",  # SMALL/MEDIUM/LARGE
    ],

    "temporal": [
        "departure_month",
        "departure_day_of_week",
        "departure_quarter",
        "is_peak_season",     # Nov-Feb for retail, varies by commodity
        "is_holiday_period",
        "transit_days_planned",
        "lead_time_days",     # booking to departure
    ],

    "cargo": [
        "mode_encoded",
        "commodity_type_encoded",
        "is_temperature_controlled",
        "value_bucket",       # LOW/MEDIUM/HIGH/VERY_HIGH
        "value_per_km",       # proxy for cargo density
    ],

    "events": [
        "event_count",
        "has_customs_hold",
        "has_port_congestion",
        "has_temperature_alarm",
        "has_documentation_issue",
        "hours_since_last_event",
        "departure_delay_hours",  # actual vs planned departure
    ],

    "contextual": [
        "prior_incident_rate_lane",
        "prior_incident_rate_carrier",
        "seasonality_index",
        "data_completeness_score",  # fraction of optional fields provided
    ],
}

ALL_FEATURES = [f for group in FEATURE_GROUPS.values() for f in group]
```

### 5.2 Feature Engineering Functions

```python
def engineer_features(context: ShipmentRiskContext) -> dict:
    """Transform raw context into model features."""
    features = {}

    # === LANE FEATURES ===
    features["distance_km"] = context.distance_km or estimate_distance(
        context.origin_country, context.destination_country
    )
    features["distance_bucket"] = bucket_distance(features["distance_km"])
    features["is_cross_border"] = context.origin_country != context.destination_country
    features["lane_historical_delay_rate"] = context.prior_incident_rate_lane or 0.10  # default

    # === TEMPORAL FEATURES ===
    features["departure_month"] = context.planned_departure.month
    features["departure_day_of_week"] = context.planned_departure.weekday()
    features["is_peak_season"] = features["departure_month"] in [11, 12, 1, 2]
    features["transit_days_planned"] = (
        context.planned_arrival - context.planned_departure
    ).days

    # === CARGO FEATURES ===
    features["value_bucket"] = bucket_value(context.value_usd)
    features["is_temperature_controlled"] = int(context.temperature_controlled or False)

    # === EVENT FEATURES ===
    features["event_count"] = len(context.events)
    event_types = [e.type for e in context.events]
    features["has_customs_hold"] = int("CUSTOMS_HOLD" in event_types)
    features["has_port_congestion"] = int("PORT_CONGESTION" in event_types)
    features["has_documentation_issue"] = int("DOCUMENTATION_ISSUE" in event_types)

    # === DEPARTURE DELAY ===
    if context.actual_departure and context.planned_departure:
        delta = (context.actual_departure - context.planned_departure).total_seconds()
        features["departure_delay_hours"] = delta / 3600
    else:
        features["departure_delay_hours"] = 0

    # === DATA QUALITY ===
    optional_fields = ["carrier_code", "distance_km", "commodity_type", "value_usd"]
    provided = sum(1 for f in optional_fields if getattr(context, f) is not None)
    features["data_completeness_score"] = provided / len(optional_fields)

    return features
```

### 5.3 Encoding Strategy

| Feature Type | Encoding Method |
|--------------|-----------------|
| Country codes | Target encoding (historical delay rate) or embedding |
| Carrier codes | Target encoding + frequency encoding |
| Commodity types | One-hot for top N, group rest as "OTHER" |
| Numeric | Standard scaling, clip outliers at 1st/99th percentile |
| Boolean | Binary (0/1) |

---

## 6. Decision Mapping

### 6.1 Threshold-Based Decision Rules

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class DecisionThresholds:
    """Configurable thresholds for decision mapping."""
    approve_max: float = 30.0
    tighten_terms_max: float = 70.0
    hold_max: float = 85.0
    # Above hold_max → ESCALATE

    # Value-based adjustments
    high_value_threshold_usd: float = 100_000
    high_value_tighten_reduction: float = 10.0  # Lower threshold for high-value


def map_risk_to_decision(
    risk_score: float,
    value_usd: float | None = None,
    thresholds: DecisionThresholds = DecisionThresholds()
) -> tuple[Literal["APPROVE", "HOLD", "TIGHTEN_TERMS", "ESCALATE"], float]:
    """
    Map risk score to actionable decision.

    Returns:
        (decision, confidence) where confidence reflects margin from threshold.
    """
    # Adjust thresholds for high-value shipments
    effective_tighten_max = thresholds.tighten_terms_max
    if value_usd and value_usd > thresholds.high_value_threshold_usd:
        effective_tighten_max -= thresholds.high_value_tighten_reduction

    # Decision logic
    if risk_score <= thresholds.approve_max:
        margin = (thresholds.approve_max - risk_score) / thresholds.approve_max
        return "APPROVE", min(0.95, 0.7 + 0.3 * margin)

    elif risk_score <= effective_tighten_max:
        # In the medium zone - APPROVE but with caution
        margin = (effective_tighten_max - risk_score) / (effective_tighten_max - thresholds.approve_max)
        if margin > 0.5:
            return "APPROVE", 0.5 + 0.2 * margin
        else:
            return "TIGHTEN_TERMS", 0.5 + 0.2 * (1 - margin)

    elif risk_score <= thresholds.hold_max:
        return "TIGHTEN_TERMS", 0.7

    elif risk_score <= 95:
        return "HOLD", 0.8

    else:
        return "ESCALATE", 0.9
```

### 6.2 Decision Matrix

| Risk Score | Value < $100K | Value ≥ $100K | Notes |
|------------|---------------|---------------|-------|
| 0-30 | APPROVE (high confidence) | APPROVE (high confidence) | Fast-track payment |
| 30-50 | APPROVE (medium confidence) | APPROVE (lower confidence) | Standard flow |
| 50-60 | APPROVE (tagged MEDIUM_RISK) | TIGHTEN_TERMS | Enhanced monitoring |
| 60-70 | TIGHTEN_TERMS | TIGHTEN_TERMS | Partial milestone hold |
| 70-85 | TIGHTEN_TERMS | HOLD | Manual review queue |
| 85-95 | HOLD | HOLD | Exception workflow |
| 95-100 | ESCALATE | ESCALATE | Senior review required |

### 6.3 Tags Generation

```python
def generate_risk_tags(
    context: ShipmentRiskContext,
    features: dict,
    risk_score: float
) -> list[str]:
    """Generate semantic tags for filtering and grouping."""
    tags = []

    # Value-based
    if (context.value_usd or 0) > 100_000:
        tags.append("HIGH_VALUE")

    # Lane volatility
    if features.get("lane_historical_delay_rate", 0) > 0.15:
        tags.append("LANE_VOLATILE")

    # Seasonal
    if features.get("is_peak_season"):
        tags.append("PEAK_SEASON")

    # Event-based
    if features.get("has_customs_hold"):
        tags.append("CUSTOMS_RISK")
    if features.get("has_port_congestion"):
        tags.append("PORT_CONGESTION")

    # Mode-specific
    if context.mode == "OCEAN" and features.get("transit_days_planned", 0) > 25:
        tags.append("LONG_HAUL_OCEAN")

    # Risk level
    if risk_score >= 70:
        tags.append("HIGH_RISK")
    elif risk_score >= 50:
        tags.append("MEDIUM_RISK")

    return tags
```

---

## 7. Explanation Generation

### 7.1 SHAP-Based Factor Extraction

```python
import shap
import numpy as np

# Human-readable labels for features
FEATURE_LABELS = {
    "lane_historical_delay_rate": "Lane historically experiences {value:.0%} delays",
    "is_peak_season": "Peak shipping season (November-February)",
    "departure_delay_hours": "Departure already delayed by {value:.1f} hours",
    "has_customs_hold": "Customs hold event detected",
    "has_port_congestion": "Port congestion event detected",
    "carrier_historical_delay_rate": "Carrier has {value:.0%} historical delay rate",
    "transit_days_planned": "Long transit time ({value:.0f} days)",
    "value_bucket": "High-value cargo (${value:,.0f})",
    "distance_km": "Long-distance route ({value:,.0f} km)",
    "is_temperature_controlled": "Temperature-controlled cargo (higher complexity)",
    "data_completeness_score": "Incomplete shipment data (quality: {value:.0%})",
}


def extract_top_factors(
    shap_values: np.ndarray,
    feature_names: list[str],
    feature_values: dict,
    top_n: int = 5
) -> list[TopFactor]:
    """Convert SHAP values into human-readable TopFactor explanations."""

    # Sort by absolute SHAP value
    abs_shap = np.abs(shap_values)
    top_indices = np.argsort(abs_shap)[-top_n:][::-1]

    factors = []
    for idx in top_indices:
        feat_name = feature_names[idx]
        shap_val = shap_values[idx]
        raw_val = feature_values.get(feat_name, 0)

        # Determine direction
        direction = "INCREASES_RISK" if shap_val > 0 else "DECREASES_RISK"

        # Generate human label
        template = FEATURE_LABELS.get(feat_name, f"{feat_name}: {{value}}")
        try:
            human_label = template.format(value=raw_val)
        except:
            human_label = f"{feat_name} = {raw_val}"

        # Magnitude as percentage of total SHAP contribution
        total_shap = np.sum(abs_shap)
        magnitude = (abs(shap_val) / total_shap * 100) if total_shap > 0 else 0

        factors.append(TopFactor(
            feature_name=feat_name,
            direction=direction,
            magnitude=round(magnitude, 1),
            human_label=human_label
        ))

    return factors


def generate_summary_reason(
    risk_score: float,
    decision: str,
    top_factors: list[TopFactor],
    context: ShipmentRiskContext
) -> str:
    """Generate natural language summary of the risk assessment."""

    # Risk level descriptor
    if risk_score < 30:
        risk_level = "Low risk"
    elif risk_score < 60:
        risk_level = "Moderate risk"
    elif risk_score < 80:
        risk_level = "Elevated risk"
    else:
        risk_level = "High risk"

    # Top increasing factors
    increasing = [f for f in top_factors if f.direction == "INCREASES_RISK"][:2]
    decreasing = [f for f in top_factors if f.direction == "DECREASES_RISK"][:1]

    # Build summary
    parts = [f"{risk_level} ({risk_score:.0f}/100)"]

    if increasing:
        drivers = " and ".join([f.human_label.lower() for f in increasing])
        parts.append(f"driven by {drivers}")

    if decreasing:
        parts.append(f"Partially offset by {decreasing[0].human_label.lower()}")

    # Decision rationale
    decision_rationale = {
        "APPROVE": "Recommend standard payment terms.",
        "TIGHTEN_TERMS": "Recommend tightened payment terms or milestone holds.",
        "HOLD": "Recommend manual review before proceeding.",
        "ESCALATE": "Requires senior review due to critical risk indicators.",
    }
    parts.append(decision_rationale.get(decision, ""))

    return " ".join(parts)
```

### 7.2 Example Explanation Output

```json
{
  "top_factors": [
    {
      "feature_name": "lane_historical_delay_rate",
      "direction": "INCREASES_RISK",
      "magnitude": 32.5,
      "human_label": "Lane historically experiences 18% delays"
    },
    {
      "feature_name": "is_peak_season",
      "direction": "INCREASES_RISK",
      "magnitude": 21.3,
      "human_label": "Peak shipping season (November-February)"
    },
    {
      "feature_name": "carrier_historical_delay_rate",
      "direction": "DECREASES_RISK",
      "magnitude": 15.8,
      "human_label": "Carrier has 5% historical delay rate"
    }
  ],
  "summary_reason": "Elevated risk (67/100) driven by lane historically experiences 18% delays and peak shipping season. Partially offset by carrier has 5% historical delay rate. Recommend tightened payment terms or milestone holds."
}
```

---

## 8. API Contract

### 8.1 Risk Scoring Endpoint

```yaml
# POST /api/v1/risk/score
# Scores one or more shipments for risk

Request:
  Content-Type: application/json
  Body:
    shipments: array[ShipmentRiskContext]  # 1-100 items
    options:
      include_factors: boolean             # default: true
      include_summary: boolean             # default: true
      max_factors: integer                 # default: 5, max: 10

Response:
  Content-Type: application/json
  Body:
    assessments: array[ShipmentRiskAssessment]
    meta:
      model_version: string
      processing_time_ms: integer
      batch_size: integer

Errors:
  400: Invalid request schema
  422: Validation error (e.g., invalid country code)
  500: Model inference error
  503: Model not loaded
```

### 8.2 Risk Simulation Endpoint

```yaml
# POST /api/v1/risk/simulation
# Compares risk under different scenarios (what-if analysis)

Request:
  Content-Type: application/json
  Body:
    base_context: ShipmentRiskContext
    variations:
      - name: string                       # e.g., "alternative_carrier"
        overrides:                         # partial ShipmentRiskContext
          carrier_code: string
          # ... any field to override
      - name: string
        overrides: {...}

Response:
  Content-Type: application/json
  Body:
    base_assessment: ShipmentRiskAssessment
    variation_assessments:
      - name: string
        assessment: ShipmentRiskAssessment
        delta_risk_score: float            # difference from base
    recommendation:
      best_variation: string | null
      savings_estimate: string             # e.g., "12 point risk reduction"

Example Use Case:
  - Compare 3 different carriers for the same lane
  - Compare direct ocean vs. intermodal routing
  - Test impact of different departure dates
```

### 8.3 Model Health Endpoint

```yaml
# GET /api/v1/risk/health

Response:
  status: "healthy" | "degraded" | "unhealthy"
  model_version: string
  last_trained: datetime
  feature_coverage:
    available: integer
    total: integer
  recent_predictions:
    count_24h: integer
    avg_latency_ms: float
    error_rate: float
```

### 8.4 Cody Integration Notes

**For Cody (Backend):**

1. **DTO Mapping**: Mirror `ShipmentRiskContext` and `ShipmentRiskAssessment` as TypeScript interfaces or Python dataclasses in the API layer.

2. **Async Pattern**: Consider async scoring for batches >10 shipments:
   ```python
   # For large batches, return job ID and poll for results
   POST /api/v1/risk/score/batch → { "job_id": "..." }
   GET /api/v1/risk/score/batch/{job_id} → { "status": "...", "assessments": [...] }
   ```

3. **Caching**: Cache assessments by `(shipment_id, model_version, context_hash)` for 15 minutes. Invalidate on new events.

4. **DecisionRecord Integration**:
   ```python
   # When creating a DecisionRecord from ChainIQ assessment:
   decision_record = DecisionRecord(
       shipment_id=assessment.shipment_id,
       decision_type="RISK_ASSESSMENT",
       decision=assessment.decision,
       confidence=assessment.decision_confidence,
       factors=assessment.top_factors,
       model_version=assessment.model_version,
       assessed_at=assessment.assessed_at,
   )
   ```

---

## 9. Evaluation Plan (Retrospective Pilot)

### 9.1 Pilot Data Requirements

```yaml
Customer provides (CSV or API):
  - shipment_id: unique identifier
  - origin/destination: country codes minimum, regions preferred
  - mode: OCEAN/TRUCK/AIR/RAIL
  - carrier: SCAC or name
  - planned_departure: datetime
  - planned_arrival: datetime
  - actual_arrival: datetime
  - late_days: integer (derived or provided)
  - had_claim: boolean
  - claim_amount_usd: float (if had_claim)

Minimum records: 500 shipments with outcomes
Preferred: 3-6 months of data, 2000+ shipments
```

### 9.2 Evaluation Metrics

```python
from sklearn.metrics import roc_auc_score, precision_recall_curve
import numpy as np

def evaluate_retrospective(
    predictions: list[float],  # predicted risk scores (0-100)
    actuals: list[bool],       # True if bad outcome
    values: list[float],       # shipment values in USD
) -> dict:
    """Compute business and ML metrics for retrospective pilot."""

    preds_normalized = np.array(predictions) / 100  # 0-1 scale
    actuals = np.array(actuals)
    values = np.array(values)

    metrics = {}

    # === ML METRICS ===
    metrics["auc_roc"] = roc_auc_score(actuals, preds_normalized)

    # Precision at top 10% risk
    top_10_threshold = np.percentile(predictions, 90)
    top_10_mask = predictions >= top_10_threshold
    if top_10_mask.sum() > 0:
        metrics["precision_at_top_10pct"] = actuals[top_10_mask].mean()

    # === BUSINESS METRICS ===

    # Lift: How much better than random at catching bad shipments?
    base_rate = actuals.mean()
    metrics["lift_at_top_10pct"] = (
        metrics.get("precision_at_top_10pct", 0) / base_rate
        if base_rate > 0 else 0
    )

    # Value at risk captured
    bad_shipment_value = values[actuals].sum()
    top_10_bad_value = values[top_10_mask & actuals].sum()
    metrics["pct_bad_value_in_top_10pct"] = (
        top_10_bad_value / bad_shipment_value
        if bad_shipment_value > 0 else 0
    )

    # Hypothetical savings: if we had HOLD'd top 10% risk
    # Assume 50% of bad outcomes avoidable with early intervention
    INTERVENTION_EFFECTIVENESS = 0.5
    metrics["hypothetical_savings_usd"] = (
        top_10_bad_value * INTERVENTION_EFFECTIVENESS
    )

    return metrics
```

### 9.3 Evaluation Script Flow

```python
def run_retrospective_pilot(customer_csv_path: str) -> dict:
    """
    Full retrospective pilot evaluation flow.

    1. Load customer historical data
    2. Map to ShipmentRiskContext
    3. Score with ChainIQ
    4. Compare to actual outcomes
    5. Generate metrics and visualizations
    """

    # 1. Load data
    df = pd.read_csv(customer_csv_path)

    # 2. Map to contexts
    contexts = [map_row_to_context(row) for _, row in df.iterrows()]

    # 3. Score (offline, batch mode)
    model = load_trained_model("chainiq-v0.1")
    assessments = [score_shipment(model, ctx) for ctx in contexts]

    # 4. Extract actuals
    actuals = df["had_bad_outcome"].tolist()  # or derive from late_days
    values = df["value_usd"].fillna(10000).tolist()

    # 5. Evaluate
    predictions = [a.risk_score for a in assessments]
    metrics = evaluate_retrospective(predictions, actuals, values)

    # 6. Generate report
    report = {
        "pilot_summary": {
            "shipments_analyzed": len(df),
            "date_range": f"{df['planned_departure'].min()} to {df['planned_departure'].max()}",
            "bad_outcome_rate": np.mean(actuals),
        },
        "metrics": metrics,
        "sample_high_risk": [
            a.model_dump() for a in sorted(assessments, key=lambda x: -x.risk_score)[:10]
        ],
    }

    return report
```

### 9.4 Success Criteria for Pilot

| Metric | Minimum | Target | Excellent |
|--------|---------|--------|-----------|
| AUC-ROC | 0.65 | 0.75 | 0.85+ |
| Lift at top 10% | 1.5x | 2.5x | 4x+ |
| % bad value in top 10% | 25% | 40% | 60%+ |
| Hypothetical savings | $50K | $200K | $500K+ |

---

## 10. Integration Notes

### 10.1 For Sonny (UI/Operator Console)

**Risk Score Display:**
```
┌─────────────────────────────────────────────────────┐
│  Shipment SHP-2024-001234                           │
│  ═══════════════════════════════════════════════    │
│                                                     │
│  Risk Score: ████████████░░░░░░░░  67/100          │
│              [ELEVATED RISK]                        │
│                                                     │
│  Decision: TIGHTEN_TERMS (82% confidence)           │
│                                                     │
│  Top Factors:                                       │
│  ▲ Lane historically experiences 18% delays (33%)  │
│  ▲ Peak shipping season (21%)                      │
│  ▼ Carrier has 5% historical delay rate (16%)      │
│                                                     │
│  Tags: [LANE_VOLATILE] [PEAK_SEASON] [HIGH_VALUE]  │
│                                                     │
│  Summary: Elevated risk driven by volatile lane    │
│  during peak season. Recommend tightened terms.    │
└─────────────────────────────────────────────────────┘
```

**Color Coding:**
- 0-30: Green (✅ Low Risk)
- 30-60: Yellow (⚠️ Medium Risk)
- 60-80: Orange (🔶 Elevated Risk)
- 80-100: Red (🔴 High/Critical Risk)

**Factor Direction Icons:**
- ▲ INCREASES_RISK (red)
- ▼ DECREASES_RISK (green)

### 10.2 For ChainPay Integration

ChainIQ assessments feed directly into settlement policy decisions:

```python
# ChainPay uses ChainIQ decision to adjust payment flow

if assessment.decision == "APPROVE":
    # Standard milestone-based payment
    payment_policy = "STANDARD"

elif assessment.decision == "TIGHTEN_TERMS":
    # Hold final 20% until delivery confirmed
    payment_policy = "MILESTONE_HOLD_20"

elif assessment.decision == "HOLD":
    # Hold all payments pending manual review
    payment_policy = "FULL_HOLD"

elif assessment.decision == "ESCALATE":
    # Route to senior review, no auto-payments
    payment_policy = "ESCALATION_QUEUE"
```

### 10.3 Data Flow Architecture

```
                     ┌──────────────┐
                     │   ChainPay   │
                     │ Settlement   │
                     └──────┬───────┘
                            │ queries risk
                            ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│  ChainBoard │───▶│     ChainIQ      │◀───│   Events    │
│   (OC UI)   │    │   Risk Brain     │    │  (telemetry)│
└─────────────┘    └────────┬─────────┘    └─────────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │  DecisionRecord  │
                   │    (audit log)   │
                   └──────────────────┘
```

---

## Appendix A: Risk Component Formulas

```python
def compute_risk_components(
    base_risk_prob: float,  # Model P(bad outcome)
    features: dict,
    context: ShipmentRiskContext
) -> dict:
    """
    Break down overall risk into component scores.

    Note: v0.1 uses heuristic weighting. v1.0 will have
    separate sub-models for each component.
    """

    # Base transformation: probability → 0-100 score
    risk_score = base_risk_prob * 100

    # Operational risk: delays, routing, capacity
    operational_risk = risk_score * 0.85  # Primary driver in v0
    if features.get("has_port_congestion"):
        operational_risk = min(100, operational_risk + 10)

    # Financial risk: cost overruns, claims
    financial_risk = risk_score * 0.6
    if (context.value_usd or 0) > 100_000:
        financial_risk = min(100, financial_risk * 1.2)

    # Fraud risk: placeholder, minimal signal in v0
    fraud_risk = max(0, risk_score * 0.1 - 5)
    if features.get("data_completeness_score", 1) < 0.5:
        fraud_risk = min(100, fraud_risk + 15)

    # ESG risk: placeholder for v0
    esg_risk = 0.0

    # Resilience: inverse of risk with buffer considerations
    resilience_score = max(0, 100 - risk_score * 1.1)
    if features.get("lane_historical_delay_rate", 0) < 0.05:
        resilience_score = min(100, resilience_score + 10)

    return {
        "risk_score": round(risk_score, 1),
        "operational_risk": round(operational_risk, 1),
        "financial_risk": round(financial_risk, 1),
        "fraud_risk": round(fraud_risk, 1),
        "esg_risk": round(esg_risk, 1),
        "resilience_score": round(resilience_score, 1),
    }
```

---

## Appendix B: Open Questions & Next PACs

1. **PAC: Public Data Acquisition** - Source and integrate actual public logistics datasets (Brazilian trade data, US BTS freight data, etc.)

2. **PAC: AIS Integration** - Add real-time vessel position and port congestion features from AIS data providers

3. **PAC: Tenant Fine-Tuning Pipeline** - Implement secure per-tenant model overlay training

4. **PAC: Model Monitoring** - Set up drift detection and automated retraining triggers

5. **PAC: ESG Scoring Module** - Expand ESG risk from placeholder to functional sub-model

---

*Document authored by Maggie (GID-10) for ChainBridge ML Architecture*
*Version: 0.1 | Status: DRAFT*
