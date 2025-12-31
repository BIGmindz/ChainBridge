# ChainIQ Feature Specification v1

**PAC Reference:** PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008  
**Author:** Maggie (GID-10) — ML & Applied AI Lead  
**Status:** CANONICAL  
**Version:** v1.0.0  
**Applies To:** ChainIQ Risk Model v1  

---

## 1. Overview

This document defines the **deterministic feature set** for ChainIQ Risk Model v1. All features are pre-computed upstream by `FeatureBuilder` and delivered as a frozen vector for inference.

**Design Principles:**
- All features are deterministic and reproducible
- No feature computation at inference time
- All values are bounded with explicit null handling
- Feature semantics are stable across model versions

---

## 2. Feature Vector Schema

### 2.1 ShipmentFeaturesV1 Definition

```python
@dataclass
class ShipmentFeaturesV1:
    """
    Canonical feature vector for ChainIQ Risk Model v1.
    All fields are required unless marked Optional.
    """
    
    # === IDENTIFIERS (not used in scoring, for traceability) ===
    shipment_id: str
    corridor_id: str
    feature_version: str = "v1.0.0"
    computed_at: datetime
    
    # === TRANSIT & OPERATIONAL FEATURES ===
    eta_deviation_hours: float
    transit_time_ratio: float
    route_deviation_km: float
    dwell_time_hours: float
    handoff_count: int
    delay_flag: bool
    mode_of_transport: str
    
    # === TEMPERATURE & IOT FEATURES ===
    temperature_violations_count: int
    max_excursion_severity: float
    monitoring_gap_hours: float
    sensor_coverage_ratio: float
    
    # === DOCUMENTATION FEATURES ===
    missing_docs_count: int
    incomplete_docs_count: int
    doc_discrepancy_severity: float
    
    # === COLLATERAL & FINANCIAL FEATURES ===
    collateral_coverage_ratio: float
    financing_type: str
    financing_amount_usd: float
    
    # === COUNTERPARTY & HISTORICAL FEATURES ===
    counterparty_risk_tier: int
    shipper_historical_success_rate: float
    shipper_prior_loss_count: int
    corridor_default_rate: float
    recent_exception_count: int
    
    # === SENTIMENT & MACRO FEATURES ===
    macro_sentiment_score: float
    corridor_sentiment_score: float
    counterparty_sentiment_score: float
    trade_friction_index: float
```

---

## 3. Feature Definitions

### 3.1 Transit & Operational Features

| Feature | Type | Range | Unit | Description | Monotonicity |
|---------|------|-------|------|-------------|--------------|
| `eta_deviation_hours` | float | [-168, 720] | hours | Difference between actual and planned arrival time. Positive = late, Negative = early | ↑ risk |
| `transit_time_ratio` | float | [0.1, 10.0] | ratio | Actual transit time / Expected transit time | ↑ risk (>1.0) |
| `route_deviation_km` | float | [0, 5000] | km | Distance from planned route | ↑ risk |
| `dwell_time_hours` | float | [0, 720] | hours | Time spent stationary at intermediate points | ↑ risk |
| `handoff_count` | int | [0, 50] | count | Number of custody transfers | ↑ risk |
| `delay_flag` | bool | {0, 1} | binary | Whether shipment is currently flagged as delayed | ↑ risk |
| `mode_of_transport` | str | enum | category | AIR, SEA, RAIL, ROAD, MULTIMODAL | N/A |

### 3.2 Temperature & IoT Features

| Feature | Type | Range | Unit | Description | Monotonicity |
|---------|------|-------|------|-------------|--------------|
| `temperature_violations_count` | int | [0, 100] | count | Number of temperature excursion events | ↑ risk |
| `max_excursion_severity` | float | [0, 10] | normalized | Worst excursion severity (0=none, 10=critical) | ↑ risk |
| `monitoring_gap_hours` | float | [0, 168] | hours | Total time without sensor data | ↑ risk |
| `sensor_coverage_ratio` | float | [0, 1] | ratio | % of transit time with active monitoring | ↓ risk |

### 3.3 Documentation Features

| Feature | Type | Range | Unit | Description | Monotonicity |
|---------|------|-------|------|-------------|--------------|
| `missing_docs_count` | int | [0, 20] | count | Number of required documents not provided | ↑ risk |
| `incomplete_docs_count` | int | [0, 20] | count | Number of documents with missing fields | ↑ risk |
| `doc_discrepancy_severity` | float | [0, 10] | normalized | Severity of discrepancies between documents | ↑ risk |

### 3.4 Collateral & Financial Features

| Feature | Type | Range | Unit | Description | Monotonicity |
|---------|------|-------|------|-------------|--------------|
| `collateral_coverage_ratio` | float | [0, 5] | ratio | Collateral value / Financing amount | ↓ risk |
| `financing_type` | str | enum | category | LETTER_OF_CREDIT, OPEN_ACCOUNT, DOCUMENTARY_COLLECTION, CASH_IN_ADVANCE | N/A |
| `financing_amount_usd` | float | [0, 100M] | USD | Total financing exposure | N/A (context) |

### 3.5 Counterparty & Historical Features

| Feature | Type | Range | Unit | Description | Monotonicity |
|---------|------|-------|------|-------------|--------------|
| `counterparty_risk_tier` | int | [1, 5] | tier | Counterparty risk rating (1=low, 5=high) | ↑ risk |
| `shipper_historical_success_rate` | float | [0, 1] | ratio | % of shipper's past shipments without issues | ↓ risk |
| `shipper_prior_loss_count` | int | [0, 100] | count | Number of prior losses from this shipper | ↑ risk |
| `corridor_default_rate` | float | [0, 1] | ratio | Historical default rate for this corridor | ↑ risk |
| `recent_exception_count` | int | [0, 50] | count | Exceptions in last 90 days for this shipper | ↑ risk |

### 3.6 Sentiment & Macro Features

| Feature | Type | Range | Unit | Description | Monotonicity |
|---------|------|-------|------|-------------|--------------|
| `macro_sentiment_score` | float | [-1, 1] | normalized | Global macro-economic sentiment | ↓ risk |
| `corridor_sentiment_score` | float | [-1, 1] | normalized | Corridor-specific trade sentiment | ↓ risk |
| `counterparty_sentiment_score` | float | [-1, 1] | normalized | Counterparty-specific sentiment | ↓ risk |
| `trade_friction_index` | float | [0, 10] | normalized | Trade barrier/friction intensity | ↑ risk |

---

## 4. Feature Engineering Rules

### 4.1 Normalization

All features are delivered **pre-normalized** to the model:

```python
# Numeric features: min-max scaling to [0, 1]
normalized = (value - min_bound) / (max_bound - min_bound)
normalized = clip(normalized, 0, 1)

# Categorical features: one-hot encoded
# mode_of_transport → [is_air, is_sea, is_rail, is_road, is_multimodal]
# financing_type → [is_loc, is_open_account, is_doc_collection, is_cash_advance]
```

### 4.2 Null Handling (FAIL-CLOSED)

| Null Policy | Action |
|-------------|--------|
| Required feature is null | **REJECT** — emit `FailedValidationPDO` |
| Optional feature is null | Use explicit default (documented below) |

**Explicit Defaults for Optional Features:**

```python
optional_defaults = {
    "macro_sentiment_score": 0.0,      # Neutral
    "corridor_sentiment_score": 0.0,   # Neutral
    "counterparty_sentiment_score": 0.0,  # Neutral
}
```

**No silent imputation.** All defaults must be logged in the PDO.

### 4.3 Bounds Validation

```python
def validate_feature(name: str, value: Any, bounds: Tuple) -> bool:
    """
    FAIL-CLOSED validation. Returns False if out of bounds.
    """
    min_val, max_val = bounds
    if value is None:
        return False  # Null check
    if not (min_val <= value <= max_val):
        return False  # Bounds check
    return True
```

---

## 5. Feature Versioning

### 5.1 Version Contract

```yaml
feature_schema:
  version: v1.0.0
  checksum: SHA256:<computed>
  
  compatibility:
    models: ["chainiq_risk_glassbox_v1.x.x"]
    breaking_change_policy: MAJOR_VERSION_BUMP
    
  changelog:
    v1.0.0: Initial feature set (24 features)
```

### 5.2 Feature Evolution Rules

| Change Type | Version Impact | Migration |
|-------------|----------------|-----------|
| Add optional feature | MINOR | Backward compatible |
| Remove feature | MAJOR | Breaking change |
| Change feature semantics | MAJOR | Breaking change |
| Change feature bounds | MINOR | Revalidation required |

---

## 6. Feature Store Integration

### 6.1 Data Sources

| Feature Category | Source System | Freshness SLA |
|------------------|---------------|---------------|
| Transit & Operational | TMS / Tracking Platform | Real-time |
| Temperature & IoT | IoT Gateway | Real-time |
| Documentation | Document Management | 15 minutes |
| Collateral & Financial | Treasury / ERP | Daily |
| Counterparty | Credit System | Daily |
| Sentiment | Market Data Feed | Hourly |

### 6.2 Feature Lineage

Every feature vector includes lineage metadata:

```python
@dataclass
class FeatureLineage:
    feature_name: str
    source_system: str
    source_version: str
    acquired_at: datetime
    freshness_seconds: int
    quality_flag: str  # "FRESH" | "STALE" | "IMPUTED"
```

---

## 7. Feature Quality Flags

| Flag | Meaning | Model Behavior |
|------|---------|----------------|
| `FRESH` | Data within SLA | Normal inference |
| `STALE` | Data beyond SLA | Log warning, continue |
| `IMPUTED` | Value was defaulted | Log in PDO |
| `MISSING` | Required value absent | **REJECT** |

---

## 8. Feature Importance (Expected)

Based on domain knowledge and preliminary analysis:

| Rank | Feature | Expected Importance |
|------|---------|---------------------|
| 1 | `counterparty_risk_tier` | High |
| 2 | `corridor_default_rate` | High |
| 3 | `eta_deviation_hours` | High |
| 4 | `collateral_coverage_ratio` | High |
| 5 | `temperature_violations_count` | Medium-High |
| 6 | `missing_docs_count` | Medium |
| 7 | `shipper_historical_success_rate` | Medium |
| 8 | `doc_discrepancy_severity` | Medium |
| 9 | `monitoring_gap_hours` | Medium |
| 10 | `trade_friction_index` | Low-Medium |

*Note: Actual importance determined post-training via shape function analysis.*

---

## 9. Testing Requirements

### 9.1 Unit Tests

```python
# All features must have:
- test_bounds_validation()
- test_null_rejection()
- test_normalization()
- test_encoding()
```

### 9.2 Integration Tests

```python
# Feature pipeline must pass:
- test_end_to_end_feature_extraction()
- test_feature_schema_compliance()
- test_feature_lineage_tracking()
- test_quality_flag_propagation()
```

---

## 10. Attestation

```yaml
attestation:
  pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
  author: Maggie (GID-10)
  role: ML & Applied AI Lead
  document: feature_spec_v1.md
  feature_count: 24
  created_at: 2025-12-26T00:00:00Z
  status: CANONICAL
```

---

**END OF DOCUMENT — feature_spec_v1.md**
