# Model Ingestion Governance v1.0
**Governance ID: GID-08-INGEST | Classification: CRITICAL | Owner: Cody (GID-01) + ALEX (GID-08)**

## Executive Summary

This document defines comprehensive governance for the **Model Ingestion Pipeline** in ChainBridge. The ingestion layer transforms raw shipment data into ML-ready features and must operate with strict integrity controls to prevent data leakage, schema drift, and model failure.

**Core Principle:**
> "Data integrity upstream guarantees model reliability downstream. Garbage in = Garbage predictions out."

---

## 1. INGESTION PIPELINE ARCHITECTURE

### 1.1 Pipeline Stages

```
Raw Data → Schema Validation → Null Handling → Feature Engineering → ML-Ready Features
    ↓           ↓                    ↓                   ↓                    ↓
  ALEX       ALEX                 ALEX                ALEX                ALEX
  Check      Check                Check               Check               Check
```

**Governance Gates:**
- **Stage 1:** Schema validation (type, range, required fields)
- **Stage 2:** Null handling (imputation strategy validation)
- **Stage 3:** Feature engineering (prevent leakage, validate transformations)
- **Stage 4:** Timezone handling (UTC enforcement)
- **Stage 5:** Final validation (distribution checks, outlier detection)

---

## 2. FEATURE CATALOG GOVERNANCE (RULE #13)

### 2.1 Required Feature Catalog

**All features must be registered in the canonical feature catalog:**

```yaml
# chainiq-service/config/feature_catalog.yaml
features:
  - name: prior_losses_flag
    type: binary
    dtype: int64
    description: "Whether shipper/carrier had prior losses in last 180 days"
    monotonicity: increasing  # Higher losses → higher risk
    null_handling: fill_zero
    default_value: 0
    validation:
      allowed_values: [0, 1]
    source: shipment_history
    created: "2025-06-01"
    last_modified: "2025-11-15"
    owner: "Maggie (GID-02)"

  - name: shipper_on_time_pct_90d
    type: continuous
    dtype: float64
    description: "Shipper's on-time delivery rate (90-day rolling window)"
    monotonicity: decreasing  # Better on-time → lower risk
    null_handling: fill_median
    default_value: 0.75
    validation:
      min_value: 0.0
      max_value: 1.0
    source: shipment_history
    created: "2025-06-01"
    last_modified: "2025-11-15"
    owner: "Maggie (GID-02)"

  - name: eta_deviation_hours
    type: continuous
    dtype: float64
    description: "Hours shipment is ahead/behind schedule (positive = late)"
    monotonicity: increasing  # More delay → higher risk
    null_handling: fill_zero
    default_value: 0.0
    validation:
      min_value: -168.0  # Max 1 week early
      max_value: 168.0   # Max 1 week late
    source: shipment_events
    created: "2025-06-01"
    last_modified: "2025-11-20"
    owner: "Maggie (GID-02)"

  - name: collateral_value
    type: continuous
    dtype: float64
    description: "Total collateral value (USD)"
    monotonicity: null  # No direct monotonic relationship
    null_handling: fill_zero
    default_value: 0.0
    validation:
      min_value: 0.0
      max_value: 10000000.0  # $10M max
    source: financing_terms
    created: "2025-06-01"
    last_modified: "2025-11-15"
    owner: "Maggie (GID-02)"
```

### 2.2 Catalog Validation

**ALEX enforces catalog consistency:**

```python
# chainiq-service/app/services/ingestion/catalog_validator.py
from typing import Dict, List
import yaml

class FeatureCatalogValidator:
    """ALEX-enforced feature catalog validation"""

    def __init__(self, catalog_path: str = "config/feature_catalog.yaml"):
        with open(catalog_path) as f:
            self.catalog = yaml.safe_load(f)
        self.feature_index = {f['name']: f for f in self.catalog['features']}

    def validate_feature_exists(self, feature_name: str) -> bool:
        """Validate feature is in catalog"""
        if feature_name not in self.feature_index:
            raise GovernanceViolation(
                f"Feature '{feature_name}' not in catalog. "
                f"All features must be registered before use."
            )
        return True

    def validate_dtype(self, feature_name: str, actual_dtype: str) -> bool:
        """Validate data type matches catalog"""
        expected = self.feature_index[feature_name]['dtype']
        if actual_dtype != expected:
            raise GovernanceViolation(
                f"Feature '{feature_name}' has dtype '{actual_dtype}' "
                f"but catalog specifies '{expected}'"
            )
        return True

    def validate_value_range(self, feature_name: str, values: pd.Series) -> bool:
        """Validate values are within allowed range"""
        spec = self.feature_index[feature_name]
        validation = spec.get('validation', {})

        if 'min_value' in validation:
            if (values < validation['min_value']).any():
                raise GovernanceViolation(
                    f"Feature '{feature_name}' has values below min: "
                    f"{validation['min_value']}"
                )

        if 'max_value' in validation:
            if (values > validation['max_value']).any():
                raise GovernanceViolation(
                    f"Feature '{feature_name}' has values above max: "
                    f"{validation['max_value']}"
                )

        if 'allowed_values' in validation:
            invalid = ~values.isin(validation['allowed_values'])
            if invalid.any():
                raise GovernanceViolation(
                    f"Feature '{feature_name}' has invalid values. "
                    f"Allowed: {validation['allowed_values']}"
                )

        return True
```

### 2.3 Catalog Change Management

**ALEX requires governance tag for catalog changes:**

```bash
# All catalog changes require ALEX approval
git commit -m "[ALEX-APPROVAL] Add new feature: sentiment_score_7d"

# PR must include:
# 1. Feature definition in catalog
# 2. Null handling strategy
# 3. Validation rules
# 4. Impact analysis on existing models
# 5. Migration plan
```

**Prohibited changes without ALEX tag:**
- ❌ Adding features not in catalog
- ❌ Changing dtype of existing feature
- ❌ Removing features still used by models
- ❌ Changing monotonicity constraints

---

## 3. NULL HANDLING GOVERNANCE

### 3.1 Required Null Handling Strategy

**Every feature must declare null handling:**

| Strategy | Use Case | ALEX Approval |
|----------|----------|---------------|
| **fill_zero** | Binary flags, counts | ✅ Approved |
| **fill_median** | Continuous metrics with normal distribution | ✅ Approved |
| **fill_mean** | Continuous metrics (use sparingly) | ⚠️ Conditional |
| **fill_mode** | Categorical variables | ✅ Approved |
| **forward_fill** | Time-series data only | ⚠️ Conditional |
| **drop_row** | When missing is informative | ⚠️ Conditional |
| **fill_sentinel** | Explicit "unknown" category | ✅ Approved |

**Prohibited strategies:**
- ❌ `fill_future_value` (data leakage!)
- ❌ `fill_label_correlated` (data leakage!)
- ❌ Random imputation without seed
- ❌ Dropping nulls without documenting bias

### 3.2 Null Handling Validation

```python
def validate_null_handling(df: pd.DataFrame, catalog: Dict) -> bool:
    """ALEX validation for null handling compliance"""

    for feature_name in df.columns:
        # Check for remaining nulls
        null_count = df[feature_name].isnull().sum()

        if null_count > 0:
            spec = catalog[feature_name]
            strategy = spec.get('null_handling')

            if strategy == 'drop_row':
                # Acceptable if documented
                log_warning(f"Feature '{feature_name}' has {null_count} nulls (drop_row)")
            else:
                raise GovernanceViolation(
                    f"Feature '{feature_name}' has {null_count} nulls after "
                    f"'{strategy}' strategy. Null handling failed."
                )

    return True
```

---

## 4. TIMEZONE HANDLING GOVERNANCE

### 4.1 UTC Enforcement

**ALEX requires all timestamps in UTC:**

```python
def enforce_utc_timezone(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all datetime columns to UTC"""

    for col in df.select_dtypes(include=['datetime64']).columns:
        if df[col].dt.tz is None:
            # Assume UTC if no timezone
            df[col] = df[col].dt.tz_localize('UTC')
        else:
            # Convert to UTC
            df[col] = df[col].dt.tz_convert('UTC')

    return df

# ❌ BLOCKED: Local timezones
df['created_at'] = pd.to_datetime(df['created_at'], tz='America/New_York')

# ✅ ALLOWED: UTC only
df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
```

### 4.2 Timezone Validation

```python
def validate_timezone_compliance(df: pd.DataFrame) -> bool:
    """Ensure all timestamps are UTC"""

    for col in df.select_dtypes(include=['datetime64']).columns:
        if df[col].dt.tz is None:
            raise GovernanceViolation(
                f"Column '{col}' has no timezone. All timestamps must be UTC."
            )

        if str(df[col].dt.tz) != 'UTC':
            raise GovernanceViolation(
                f"Column '{col}' has timezone '{df[col].dt.tz}'. "
                f"Only UTC is allowed."
            )

    return True
```

---

## 5. ALLOWED TRANSFORMATIONS

### 5.1 Safe Transformations

**ALEX approves these transformations:**

```python
# ✅ Aggregations (historical data only)
shipper_on_time_pct_90d = (
    shipments_last_90_days
    .groupby('shipper_id')
    .agg({'on_time': 'mean'})
)

# ✅ Mathematical transformations
log_collateral_value = np.log1p(collateral_value)
sqrt_transit_hours = np.sqrt(transit_hours)

# ✅ Date/time features (no future leakage)
day_of_week = shipment_date.dt.dayofweek
month = shipment_date.dt.month
hour_of_day = shipment_date.dt.hour

# ✅ Binning (documented thresholds)
collateral_value_bucket = pd.cut(
    collateral_value,
    bins=[0, 50000, 250000, np.inf],
    labels=['low', 'medium', 'high']
)

# ✅ Rolling windows (historical only)
corridor_disruption_index_90d = (
    disruptions
    .rolling(window='90D', on='date')
    .mean()
)
```

---

## 6. FORBIDDEN TRANSFORMATIONS (DATA LEAKAGE)

### 6.1 Prohibited Patterns

**ALEX blocks these transformations:**

```python
# ❌ BLOCKED: Future data leakage
# Using post-shipment data to predict shipment outcome
actual_transit_hours = shipment['delivered_at'] - shipment['initiated_at']
# This is the OUTCOME! Cannot use for prediction!

# ❌ BLOCKED: Label-correlated imputation
# Filling nulls based on target variable
missing_mask = features['sensor_uptime_pct'].isnull()
features.loc[missing_mask, 'sensor_uptime_pct'] = (
    features.loc[missing_mask, 'target'].map({0: 0.95, 1: 0.65})
)
# This leaks label information!

# ❌ BLOCKED: Global statistics from test set
# Using mean/median from entire dataset (including future data)
mean_collateral = features['collateral_value'].mean()  # Includes test data!
features['collateral_value_normalized'] = features['collateral_value'] / mean_collateral

# ❌ BLOCKED: Forward-looking rolling windows
features['future_disruption_7d'] = (
    disruptions
    .rolling(window='7D', on='date')
    .mean()
    .shift(-7)  # Looking 7 days into the future!
)

# ❌ BLOCKED: Target encoding without proper cross-validation
# Encoding categorical based on target mean (naive approach)
shipper_risk_map = train_df.groupby('shipper_id')['target'].mean()
features['shipper_encoded'] = features['shipper_id'].map(shipper_risk_map)
# Must use proper CV or Bayesian encoding!
```

### 6.2 Leakage Detection

```python
def detect_data_leakage(
    features: pd.DataFrame,
    training_cutoff_date: pd.Timestamp
) -> List[str]:
    """
    ALEX leakage detection for ingestion pipeline
    """
    violations = []

    # Check 1: Features using post-cutoff data
    for col in features.columns:
        if 'actual_' in col or 'final_' in col or 'delivered_' in col:
            violations.append(
                f"Feature '{col}' appears to use post-shipment data. "
                f"This is likely data leakage."
            )

    # Check 2: Perfect correlations with target
    if 'target' in features.columns:
        for col in features.columns:
            if col == 'target':
                continue
            corr = features[[col, 'target']].corr().iloc[0, 1]
            if abs(corr) > 0.95:
                violations.append(
                    f"Feature '{col}' has suspiciously high correlation "
                    f"with target ({corr:.3f}). Possible leakage."
                )

    # Check 3: Features with future timestamps
    for col in features.select_dtypes(include=['datetime64']).columns:
        future_count = (features[col] > training_cutoff_date).sum()
        if future_count > 0:
            violations.append(
                f"Feature '{col}' has {future_count} future timestamps "
                f"(after {training_cutoff_date}). Data leakage detected."
            )

    return violations
```

---

## 7. LOSS AMOUNT MULTI-CLAIM LOGIC

### 7.1 Multi-Claim Aggregation Rules

**For shipments with multiple claims (loss events):**

```python
def aggregate_loss_amounts(claims: pd.DataFrame) -> pd.Series:
    """
    ALEX-governed multi-claim aggregation

    Rules:
    1. Sum all loss amounts per shipment
    2. Cap at collateral_value (cannot exceed collateral)
    3. Document partial vs total loss
    """

    aggregated = claims.groupby('shipment_id').agg({
        'loss_amount': 'sum',
        'claim_count': 'count',
        'collateral_value': 'first'  # Same for all claims
    })

    # Rule: Total loss cannot exceed collateral
    aggregated['total_loss_capped'] = np.minimum(
        aggregated['loss_amount'],
        aggregated['collateral_value']
    )

    # Document loss type
    aggregated['loss_type'] = np.where(
        aggregated['total_loss_capped'] >= aggregated['collateral_value'] * 0.95,
        'total_loss',
        'partial_loss'
    )

    return aggregated
```

### 7.2 Loss Amount Validation

```python
def validate_loss_amounts(df: pd.DataFrame) -> bool:
    """Validate loss amount logic"""

    # Check 1: No negative losses
    if (df['loss_amount'] < 0).any():
        raise GovernanceViolation("Negative loss amounts detected")

    # Check 2: Loss does not exceed collateral (capped)
    if (df['total_loss_capped'] > df['collateral_value'] * 1.01).any():
        raise GovernanceViolation(
            "Loss amount exceeds collateral (even with 1% tolerance)"
        )

    # Check 3: Multi-claim shipments have claim_count > 1
    multi_claim = df['claim_count'] > 1
    if multi_claim.any():
        log_info(f"{multi_claim.sum()} shipments have multiple claims")

    return True
```

---

## 8. UNIT TEST COVERAGE REQUIREMENTS

### 8.1 Required Test Coverage

**ALEX enforces minimum test coverage for ingestion:**

| Component | Coverage Target | Enforcement |
|-----------|----------------|-------------|
| **Schema Validation** | 100% | CI blocks < 100% |
| **Null Handling** | 100% | CI blocks < 100% |
| **Timezone Handling** | 100% | CI blocks < 100% |
| **Feature Engineering** | > 90% | CI blocks < 90% |
| **Leakage Detection** | > 90% | CI blocks < 90% |

### 8.2 Required Test Cases

```python
# tests/test_ingestion_governance.py
import pytest
from app.services.ingestion import IngestorV02

class TestIngestionGovernance:
    """ALEX-enforced ingestion governance tests"""

    def test_feature_catalog_validation(self):
        """All features must be in catalog"""
        ingestor = IngestorV02()

        # Valid features pass
        valid_df = pd.DataFrame({
            'prior_losses_flag': [0, 1, 0],
            'shipper_on_time_pct_90d': [0.85, 0.92, 0.78]
        })
        assert ingestor.validate_catalog(valid_df)

        # Invalid feature fails
        invalid_df = pd.DataFrame({
            'unknown_feature': [1, 2, 3]
        })
        with pytest.raises(GovernanceViolation):
            ingestor.validate_catalog(invalid_df)

    def test_null_handling_compliance(self):
        """Nulls must be handled per catalog spec"""
        ingestor = IngestorV02()

        df = pd.DataFrame({
            'prior_losses_flag': [0, np.nan, 1],
            'shipper_on_time_pct_90d': [0.85, np.nan, 0.78]
        })

        # After ingestion, no nulls remain
        result = ingestor.process(df)
        assert result.isnull().sum().sum() == 0

    def test_timezone_enforcement(self):
        """All timestamps must be UTC"""
        ingestor = IngestorV02()

        # Non-UTC timestamp rejected
        df = pd.DataFrame({
            'created_at': pd.to_datetime(['2025-01-01'], tz='America/New_York')
        })

        with pytest.raises(GovernanceViolation):
            ingestor.validate_timezones(df)

        # UTC timestamp accepted
        df_utc = pd.DataFrame({
            'created_at': pd.to_datetime(['2025-01-01'], utc=True)
        })
        assert ingestor.validate_timezones(df_utc)

    def test_data_leakage_detection(self):
        """Leakage patterns must be detected"""
        ingestor = IngestorV02()

        # Feature with "actual_" prefix (post-shipment data)
        df = pd.DataFrame({
            'actual_transit_hours': [48.5, 52.3, 45.8],
            'target': [0, 1, 0]
        })

        violations = ingestor.detect_leakage(df, training_cutoff='2025-06-01')
        assert len(violations) > 0
        assert any('actual_' in v for v in violations)

    def test_loss_amount_aggregation(self):
        """Multi-claim loss amounts must aggregate correctly"""
        claims = pd.DataFrame({
            'shipment_id': ['ship_1', 'ship_1', 'ship_2'],
            'loss_amount': [10000, 5000, 20000],
            'collateral_value': [50000, 50000, 30000]
        })

        result = aggregate_loss_amounts(claims)

        # ship_1: Two claims totaling $15,000 (within $50k collateral)
        assert result.loc['ship_1', 'total_loss_capped'] == 15000

        # ship_2: One claim of $20,000 (within $30k collateral)
        assert result.loc['ship_2', 'total_loss_capped'] == 20000

    def test_value_range_validation(self):
        """Features must be within catalog-defined ranges"""
        ingestor = IngestorV02()

        # shipper_on_time_pct_90d: Valid range [0.0, 1.0]
        df = pd.DataFrame({
            'shipper_on_time_pct_90d': [0.85, 1.5, 0.78]  # 1.5 out of range!
        })

        with pytest.raises(GovernanceViolation):
            ingestor.validate_ranges(df)
```

---

## 9. SCHEMA CHANGE GOVERNANCE

### 9.1 Schema Change Approval Process

**All schema changes require ALEX approval:**

```
1. Developer proposes schema change
   ↓
2. Create schema diff report (tools/ingestion_schema_diff.py)
   ↓
3. Submit PR with [ALEX-APPROVAL] tag
   ↓
4. ALEX CI check validates:
   - New fields in catalog
   - Null handling strategy defined
   - Validation rules specified
   - Backward compatibility verified
   ↓
5. ALEX approves or blocks
   ↓
6. If approved, merge and deploy
```

### 9.2 Schema Diff Report

```python
# Generated by tools/ingestion_schema_diff.py
{
  "schema_version": "v0.3.0",
  "previous_version": "v0.2.0",
  "date": "2025-12-11",
  "changes": {
    "added_fields": [
      {
        "name": "sentiment_score_7d",
        "dtype": "float64",
        "null_handling": "fill_zero",
        "validation": {"min_value": -1.0, "max_value": 1.0},
        "impact": "LOW (new optional feature)"
      }
    ],
    "removed_fields": [],
    "modified_fields": [
      {
        "name": "corridor_disruption_index_90d",
        "change": "dtype: float32 → float64",
        "reason": "Precision improvement",
        "impact": "LOW (type widening, no data loss)",
        "migration": "Automatic cast"
      }
    ]
  },
  "backward_compatible": true,
  "alex_approval": "PENDING",
  "migration_plan": "Deploy to staging, run validation, deploy to production"
}
```

---

## 10. INGESTION PERFORMANCE BUDGETS

### 10.1 Performance Thresholds

**ALEX enforces performance budgets:**

| Metric | Threshold | Action on Violation |
|--------|-----------|---------------------|
| **Ingestion Latency (p95)** | < 500ms | Alert ML team |
| **Ingestion Latency (p99)** | < 1000ms | Alert + escalate |
| **Memory Usage** | < 2GB per batch | Alert DevOps |
| **Null Rate** | < 5% | Warning (check data quality) |
| **Schema Validation Failures** | 0% | Block deployment |

### 10.2 Performance Monitoring

```python
# Ingestion metrics (Prometheus format)
ingestion_latency_seconds = Histogram(
    'chainiq_ingestion_latency_seconds',
    'Ingestion pipeline latency',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

ingestion_null_rate = Gauge(
    'chainiq_ingestion_null_rate',
    'Percentage of null values after handling'
)

ingestion_validation_failures = Counter(
    'chainiq_ingestion_validation_failures_total',
    'Count of validation failures by type',
    ['failure_type']
)
```

---

## 11. ACCEPTANCE CRITERIA

**Ingestion pipeline is governance-compliant when:**

1. ✅ All features registered in catalog
2. ✅ Null handling strategy defined for every feature
3. ✅ Timezone enforcement active (UTC only)
4. ✅ Data leakage detection passing
5. ✅ Unit test coverage > 90%
6. ✅ Schema change governance enforced
7. ✅ Performance budgets monitored
8. ✅ Multi-claim loss logic validated

---

## 12. AGENT OBLIGATIONS

### Cody (GID-01) - Backend Engineering

**Must:**
- Implement `FeatureCatalogValidator`
- Enforce UTC timezone handling
- Add leakage detection to ingestion pipeline
- Create schema diff tooling
- Achieve 100% test coverage for schema/null/timezone handling

**Cannot:**
- Modify ingestion schema without [ALEX-APPROVAL] tag
- Add features not in catalog
- Use non-UTC timestamps
- Deploy ingestion changes without unit tests

### Maggie (GID-02) - ML Engineering

**Must:**
- Maintain feature catalog completeness
- Define null handling strategy for new features
- Document monotonicity constraints
- Validate no data leakage in feature engineering
- Review schema diffs for ML impact

**Cannot:**
- Use features not in catalog
- Train models with leaked data
- Ignore null handling requirements

---

## 13. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-11 | Initial Model Ingestion Governance (ALEX Protection Mode v2.1) |

---

## 14. REFERENCES

- [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)
- [ML Lifecycle Governance](./ML_LIFECYCLE_GOVERNANCE.md)
- [Shadow Mode Governance](./SHADOW_MODE_GOVERNANCE.md)
- [Feature Catalog](../../chainiq-service/config/feature_catalog.yaml)

---

**ALEX (GID-08) - Data Integrity Upstream • Model Reliability Downstream • No Leakage Tolerated**
