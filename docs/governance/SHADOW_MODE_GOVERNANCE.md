# Shadow Mode Governance v1.0
**Governance ID: GID-08-SHADOW | Classification: CRITICAL | Owner: Cody (GID-01) + ALEX (GID-08)**

## Executive Summary

This document defines comprehensive governance for **Shadow Mode Execution** in ChainBridge. Shadow Mode runs new ML models alongside production models to detect drift, validate improvements, and ensure safe deployment. ALEX enforces strict integrity controls for shadow scoring, drift detection, and version synchronization.

**Core Principle:**
> "Shadow Mode is not a formality—it's the final safety gate. High drift = blocked deployment."

---

## 1. SHADOW MODE ARCHITECTURE

### 1.1 Shadow Execution Flow

```
Incoming Request
      ↓
   [Production Model v0.2.0] ──→ Production Score (returned to client)
      ↓
   [Shadow Model v0.3.0] ──→ Shadow Score (logged only)
      ↓
   [Drift Calculator] ──→ Delta, Percentage Diff, Statistical Signals
      ↓
   [Shadow Event Logger] ──→ shadow_events table
      ↓
   [DriftProbe] ──→ Real-time monitoring + alerts
```

**Governance Gates:**
- **Stage 1:** Version matching validation
- **Stage 2:** Required fields validation
- **Stage 3:** Delta calculation integrity
- **Stage 4:** Statistical drift detection
- **Stage 5:** Escalation on high drift

---

## 2. REQUIRED SHADOW EVENT FIELDS (RULE #14)

### 2.1 Mandatory Fields

**Every shadow event must contain:**

```python
# chainiq-service/app/models/shadow_event.py
from sqlalchemy import Column, String, Float, DateTime, Integer, JSON
from app.models.base import CanonicalBaseModel

class ShadowEvent(CanonicalBaseModel):
    """
    Shadow mode scoring event (ALEX-governed)
    """
    __tablename__ = 'shadow_events'

    # Canonical fields (inherited)
    # canonical_id, created_at, updated_at, version, source

    # Required: Request identification
    request_id = Column(String, nullable=False, index=True)
    shipment_id = Column(String, nullable=False, index=True)

    # Required: Model versions
    production_model_version = Column(String, nullable=False)
    shadow_model_version = Column(String, nullable=False)

    # Required: Scores
    production_score = Column(Float, nullable=False)
    shadow_score = Column(Float, nullable=False)

    # Required: Delta metrics
    score_delta = Column(Float, nullable=False)  # shadow - production
    score_delta_pct = Column(Float, nullable=False)  # (shadow - production) / production
    abs_score_delta = Column(Float, nullable=False)  # |shadow - production|

    # Required: Performance metrics
    production_latency_ms = Column(Float, nullable=False)
    shadow_latency_ms = Column(Float, nullable=False)

    # Required: Integrity flags
    integrity_flags = Column(JSON, nullable=False)  # See section 2.3

    # Optional: Feature contributions (explainability)
    production_top_features = Column(JSON, nullable=True)
    shadow_top_features = Column(JSON, nullable=True)

    # Required: Metadata
    environment = Column(String, nullable=False)  # staging, production
    api_endpoint = Column(String, nullable=False)

    # Required: Timestamp
    scored_at = Column(DateTime, nullable=False, index=True)
```

### 2.2 Field Validation

```python
def validate_shadow_event_fields(event: Dict) -> bool:
    """
    ALEX validation for shadow event completeness
    """
    required_fields = [
        'request_id',
        'shipment_id',
        'production_model_version',
        'shadow_model_version',
        'production_score',
        'shadow_score',
        'score_delta',
        'score_delta_pct',
        'abs_score_delta',
        'production_latency_ms',
        'shadow_latency_ms',
        'integrity_flags',
        'environment',
        'api_endpoint',
        'scored_at'
    ]

    missing_fields = [f for f in required_fields if f not in event]

    if missing_fields:
        raise GovernanceViolation(
            f"Shadow event missing required fields: {missing_fields}"
        )

    # Validate score ranges
    if not (0.0 <= event['production_score'] <= 1.0):
        raise GovernanceViolation(
            f"Production score out of range: {event['production_score']}"
        )

    if not (0.0 <= event['shadow_score'] <= 1.0):
        raise GovernanceViolation(
            f"Shadow score out of range: {event['shadow_score']}"
        )

    # Validate delta consistency
    expected_delta = event['shadow_score'] - event['production_score']
    if abs(event['score_delta'] - expected_delta) > 1e-6:
        raise GovernanceViolation(
            f"Score delta mismatch: {event['score_delta']} != {expected_delta}"
        )

    return True
```

### 2.3 Integrity Flags

**Required integrity flags in every shadow event:**

```python
integrity_flags = {
    # Data quality flags
    "has_missing_features": False,  # Were any features null/missing?
    "has_out_of_range_features": False,  # Were any features outside catalog range?
    "has_schema_mismatch": False,  # Did schema differ from expected?

    # Calculation flags
    "negative_delta": False,  # Is shadow score < production score?
    "large_delta": False,  # Is |delta| > 0.15?
    "extreme_delta": False,  # Is |delta| > 0.30?

    # Performance flags
    "slow_production": False,  # production_latency > 200ms?
    "slow_shadow": False,  # shadow_latency > 200ms?

    # Model flags
    "version_mismatch_warning": False,  # Unexpected version combo?
    "explainability_divergence": False,  # Top features differ significantly?
}
```

**Integrity flag calculation:**

```python
def calculate_integrity_flags(
    production_score: float,
    shadow_score: float,
    production_latency_ms: float,
    shadow_latency_ms: float,
    features: Dict,
    catalog: Dict
) -> Dict:
    """
    ALEX-governed integrity flag generation
    """
    flags = {}

    # Data quality
    flags['has_missing_features'] = any(v is None for v in features.values())
    flags['has_out_of_range_features'] = check_feature_ranges(features, catalog)
    flags['has_schema_mismatch'] = check_schema_match(features, catalog)

    # Delta severity
    delta = shadow_score - production_score
    abs_delta = abs(delta)
    flags['negative_delta'] = delta < 0
    flags['large_delta'] = abs_delta > 0.15
    flags['extreme_delta'] = abs_delta > 0.30

    # Performance
    flags['slow_production'] = production_latency_ms > 200
    flags['slow_shadow'] = shadow_latency_ms > 200

    return flags
```

---

## 3. VERSION MATCHING RULES (RULE #18)

### 3.1 Version Synchronization

**ALEX enforces version matching between dummy and real endpoints:**

```python
# Configuration
SHADOW_MODE_CONFIG = {
    "production_model_version": "v0.2.0",
    "shadow_model_version": "v0.3.0",
    "shadow_mode_enabled": True,
    "shadow_percentage": 100,  # 100% of requests scored by both
}

# Version validation
def validate_version_synchronization() -> bool:
    """
    Ensure dummy endpoint uses same shadow model as real endpoint
    """
    # Dummy endpoint config
    dummy_shadow_version = get_dummy_endpoint_shadow_version()

    # Real endpoint config
    real_shadow_version = get_real_endpoint_shadow_version()

    if dummy_shadow_version != real_shadow_version:
        raise GovernanceViolation(
            f"Version mismatch: "
            f"Dummy endpoint shadow={dummy_shadow_version}, "
            f"Real endpoint shadow={real_shadow_version}. "
            f"Shadow models must match across all endpoints."
        )

    return True
```

### 3.2 Version Change Protocol

**All shadow model version changes require:**

```yaml
# 1. Update configuration
shadow_model_version: "v0.3.0"

# 2. Deploy to dummy endpoint first
deployment_sequence:
  - target: dummy_endpoint
    validate: true
    rollback_on_error: true

  # 3. After 1 hour validation, deploy to real endpoint
  - target: real_endpoint
    validate: true
    rollback_on_error: true

# 4. Monitor for version consistency
monitoring:
  version_match_check_interval_seconds: 60
  alert_on_mismatch: true
```

---

## 4. DRIFT SIGNALS & STATISTICAL TESTS

### 4.1 Primary Drift Metrics

**ALEX tracks these drift signals:**

| Metric | Calculation | Threshold | Severity |
|--------|-------------|-----------|----------|
| **Mean Absolute Delta** | mean(\|shadow - prod\|) | > 0.10 | MEDIUM |
| **P95 Absolute Delta** | p95(\|shadow - prod\|) | > 0.20 | HIGH |
| **P99 Absolute Delta** | p99(\|shadow - prod\|) | > 0.30 | CRITICAL |
| **Large Delta Rate** | % with \|delta\| > 0.15 | > 20% | MEDIUM |
| **Extreme Delta Rate** | % with \|delta\| > 0.30 | > 5% | HIGH |
| **Score Distribution KL Divergence** | KL(shadow \|\| prod) | > 0.15 | MEDIUM |
| **Sign Flip Rate** | % where sign(shadow - prod) alternates | > 30% | HIGH |

### 4.2 Statistical Significance Tests

```python
from scipy import stats
import numpy as np

def run_drift_significance_tests(
    production_scores: np.ndarray,
    shadow_scores: np.ndarray
) -> Dict:
    """
    ALEX-governed statistical drift tests
    """
    results = {}

    # Test 1: Paired t-test (are means different?)
    t_stat, p_value = stats.ttest_rel(shadow_scores, production_scores)
    results['paired_ttest'] = {
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'interpretation': 'Shadow model scores significantly different' if p_value < 0.05 else 'No significant difference'
    }

    # Test 2: Kolmogorov-Smirnov test (are distributions different?)
    ks_stat, ks_p_value = stats.ks_2samp(production_scores, shadow_scores)
    results['ks_test'] = {
        'ks_statistic': ks_stat,
        'p_value': ks_p_value,
        'significant': ks_p_value < 0.05,
        'interpretation': 'Distributions differ significantly' if ks_p_value < 0.05 else 'Distributions similar'
    }

    # Test 3: Correlation (how similar are the rankings?)
    correlation = np.corrcoef(production_scores, shadow_scores)[0, 1]
    results['correlation'] = {
        'pearson_r': correlation,
        'interpretation': 'High agreement' if correlation > 0.90 else 'Low agreement'
    }

    # Test 4: KL Divergence (distribution distance)
    # Bin scores into 10 bins
    prod_hist, bins = np.histogram(production_scores, bins=10, range=(0, 1), density=True)
    shadow_hist, _ = np.histogram(shadow_scores, bins=bins, density=True)

    # Add small constant to avoid log(0)
    prod_hist += 1e-10
    shadow_hist += 1e-10

    # Normalize
    prod_hist /= prod_hist.sum()
    shadow_hist /= shadow_hist.sum()

    kl_div = np.sum(shadow_hist * np.log(shadow_hist / prod_hist))
    results['kl_divergence'] = {
        'value': kl_div,
        'significant': kl_div > 0.15,
        'interpretation': 'High divergence' if kl_div > 0.15 else 'Low divergence'
    }

    return results
```

### 4.3 Drift Severity Classification

```python
def classify_drift_severity(drift_metrics: Dict) -> str:
    """
    ALEX drift severity classification

    Returns: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
    """
    severity_points = 0

    # Mean absolute delta
    if drift_metrics['mean_abs_delta'] > 0.10:
        severity_points += 1
    if drift_metrics['mean_abs_delta'] > 0.15:
        severity_points += 1

    # P95 delta
    if drift_metrics['p95_abs_delta'] > 0.20:
        severity_points += 2

    # P99 delta
    if drift_metrics['p99_abs_delta'] > 0.30:
        severity_points += 3

    # Extreme delta rate
    if drift_metrics['extreme_delta_rate'] > 0.05:
        severity_points += 2

    # KL divergence
    if drift_metrics['kl_divergence'] > 0.15:
        severity_points += 1

    # Classify
    if severity_points == 0:
        return 'LOW'
    elif severity_points <= 2:
        return 'MEDIUM'
    elif severity_points <= 5:
        return 'HIGH'
    else:
        return 'CRITICAL'
```

---

## 5. PERFORMANCE BUDGETS (P95/P99)

### 5.1 Latency Thresholds

**ALEX enforces strict performance budgets:**

| Metric | Production | Shadow | Action on Violation |
|--------|-----------|--------|---------------------|
| **P50 Latency** | < 100ms | < 150ms | Warning |
| **P95 Latency** | < 200ms | < 300ms | Alert |
| **P99 Latency** | < 500ms | < 750ms | Escalate |
| **Memory Usage** | < 512MB | < 768MB | Alert DevOps |

### 5.2 Performance Monitoring

```python
# Prometheus metrics
shadow_latency_seconds = Histogram(
    'chainiq_shadow_latency_seconds',
    'Shadow mode scoring latency',
    labelnames=['model_version', 'endpoint'],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

shadow_drift_gauge = Gauge(
    'chainiq_shadow_drift_mean_abs_delta',
    'Mean absolute delta between shadow and production'
)

shadow_integrity_violations = Counter(
    'chainiq_shadow_integrity_violations_total',
    'Shadow integrity flag violations',
    labelnames=['flag_type']
)
```

### 5.3 Performance Alerts

```yaml
# Alert rules
alerts:
  - name: "Shadow Mode P99 Latency High"
    condition: "chainiq_shadow_latency_seconds_p99 > 0.75"
    action: "Page ML team + DevOps"
    severity: "HIGH"

  - name: "Shadow Mode High Drift"
    condition: "chainiq_shadow_drift_mean_abs_delta > 0.15"
    action: "Alert ML team + block deployment"
    severity: "CRITICAL"

  - name: "Shadow Mode Integrity Violations"
    condition: "rate(chainiq_shadow_integrity_violations_total[5m]) > 10"
    action: "Alert ML team"
    severity: "MEDIUM"
```

---

## 6. ESCALATION LOGIC FOR HIGH DRIFT

### 6.1 Drift Escalation Thresholds

**ALEX automatically escalates based on drift severity:**

| Drift Severity | Threshold | Action | Timeline |
|----------------|-----------|--------|----------|
| **LOW** | mean_abs_delta < 0.10 | Continue monitoring | - |
| **MEDIUM** | mean_abs_delta 0.10-0.15 | Alert ML team | - |
| **HIGH** | mean_abs_delta 0.15-0.20 | Block deployment + investigate | 24 hours |
| **CRITICAL** | mean_abs_delta > 0.20 | Emergency rollback + root cause | Immediate |

### 6.2 Escalation Workflow

```python
def escalate_shadow_drift(
    drift_severity: str,
    drift_metrics: Dict,
    shadow_model_version: str
) -> None:
    """
    ALEX drift escalation workflow
    """

    if drift_severity == 'LOW':
        # No action needed
        log_info(f"Shadow model {shadow_model_version}: LOW drift, continuing")
        return

    elif drift_severity == 'MEDIUM':
        # Alert ML team
        alert_ml_team({
            "alert": "SHADOW_DRIFT_MEDIUM",
            "shadow_model_version": shadow_model_version,
            "mean_abs_delta": drift_metrics['mean_abs_delta'],
            "action": "Review drift metrics, consider model adjustments"
        })

    elif drift_severity == 'HIGH':
        # Block deployment
        block_model_deployment(shadow_model_version)

        # Alert with urgency
        alert_ml_team({
            "alert": "SHADOW_DRIFT_HIGH",
            "shadow_model_version": shadow_model_version,
            "mean_abs_delta": drift_metrics['mean_abs_delta'],
            "p95_abs_delta": drift_metrics['p95_abs_delta'],
            "action": "DEPLOYMENT BLOCKED - Investigate root cause within 24 hours",
            "urgency": "HIGH"
        })

        # Log governance event
        log_governance_event({
            "event": "SHADOW_DRIFT_DEPLOYMENT_BLOCKED",
            "model_version": shadow_model_version,
            "drift_severity": "HIGH",
            "drift_metrics": drift_metrics
        })

    elif drift_severity == 'CRITICAL':
        # Emergency rollback
        emergency_rollback_shadow_model(shadow_model_version)

        # Page on-call
        page_on_call({
            "alert": "SHADOW_DRIFT_CRITICAL",
            "shadow_model_version": shadow_model_version,
            "mean_abs_delta": drift_metrics['mean_abs_delta'],
            "p99_abs_delta": drift_metrics['p99_abs_delta'],
            "action": "EMERGENCY ROLLBACK INITIATED - Immediate root cause analysis required",
            "urgency": "CRITICAL"
        })

        # Create incident
        create_incident({
            "title": f"Shadow Model {shadow_model_version} Critical Drift",
            "severity": "P0",
            "description": f"Mean absolute delta: {drift_metrics['mean_abs_delta']:.3f}",
            "assigned_to": "ML Team Lead"
        })
```

---

## 7. INTEGRATION WITH DRIFTPROBE

### 7.1 DriftProbe Configuration

**Shadow Mode data feeds into DriftProbe:**

```python
# chainiq-service/app/services/drift_probe.py
class DriftProbe:
    """
    Real-time drift monitoring (ALEX-governed)
    """

    def __init__(self):
        self.drift_window_hours = 24
        self.min_sample_size = 100
        self.alert_threshold = 0.15

    def calculate_rolling_drift(self) -> Dict:
        """
        Calculate drift metrics over rolling window
        """
        # Query shadow events from last 24 hours
        shadow_events = (
            db.query(ShadowEvent)
            .filter(ShadowEvent.scored_at > datetime.utcnow() - timedelta(hours=24))
            .all()
        )

        if len(shadow_events) < self.min_sample_size:
            return {'status': 'INSUFFICIENT_DATA'}

        # Extract scores
        production_scores = [e.production_score for e in shadow_events]
        shadow_scores = [e.shadow_score for e in shadow_events]

        # Calculate drift metrics
        deltas = [abs(s - p) for s, p in zip(shadow_scores, production_scores)]

        drift_metrics = {
            'mean_abs_delta': np.mean(deltas),
            'p50_abs_delta': np.percentile(deltas, 50),
            'p95_abs_delta': np.percentile(deltas, 95),
            'p99_abs_delta': np.percentile(deltas, 99),
            'large_delta_rate': sum(d > 0.15 for d in deltas) / len(deltas),
            'extreme_delta_rate': sum(d > 0.30 for d in deltas) / len(deltas),
            'sample_size': len(deltas)
        }

        # Run statistical tests
        sig_tests = run_drift_significance_tests(
            np.array(production_scores),
            np.array(shadow_scores)
        )

        drift_metrics['statistical_tests'] = sig_tests

        # Classify severity
        drift_metrics['severity'] = classify_drift_severity(drift_metrics)

        return drift_metrics

    def check_and_alert(self):
        """
        Check drift and alert if necessary
        """
        drift_metrics = self.calculate_rolling_drift()

        if drift_metrics.get('status') == 'INSUFFICIENT_DATA':
            return

        # Escalate based on severity
        escalate_shadow_drift(
            drift_metrics['severity'],
            drift_metrics,
            SHADOW_MODE_CONFIG['shadow_model_version']
        )
```

### 7.2 DriftProbe Dashboard

**Real-time drift dashboard shows:**

- Mean/P95/P99 absolute delta (24h rolling)
- Distribution comparison (production vs shadow)
- Large delta rate trend
- Statistical significance indicators
- Severity classification history
- Recent escalations

---

## 8. SHADOW MODE DURATION REQUIREMENTS

### 8.1 Minimum Shadow Duration

**ALEX requires minimum shadow observation period:**

| Deployment Stage | Min Shadow Duration | Min Sample Size | Drift Check |
|------------------|---------------------|-----------------|-------------|
| **Initial Shadow** | 7 days | 10,000 requests | Continuous |
| **Controlled Rollout** | 14 days | 25,000 requests | Continuous |
| **Pre-Production** | 30 days | 50,000 requests | Continuous |

### 8.2 Shadow Completion Criteria

**Shadow mode is complete when:**

1. ✅ Minimum duration met (7+ days)
2. ✅ Minimum sample size met (10,000+ requests)
3. ✅ Drift severity = LOW or MEDIUM (not HIGH or CRITICAL)
4. ✅ All integrity flags reviewed
5. ✅ Statistical tests pass (p-value interpretations documented)
6. ✅ Performance budgets met (p95/p99 within thresholds)
7. ✅ No emergency escalations in last 7 days

```python
def validate_shadow_completion(shadow_model_version: str) -> bool:
    """
    ALEX validation for shadow mode completion
    """
    # Query shadow data
    start_date = get_shadow_start_date(shadow_model_version)
    days_elapsed = (datetime.utcnow() - start_date).days

    shadow_events = (
        db.query(ShadowEvent)
        .filter(ShadowEvent.shadow_model_version == shadow_model_version)
        .all()
    )

    # Check 1: Duration
    if days_elapsed < 7:
        return False, f"Only {days_elapsed} days elapsed (min: 7)"

    # Check 2: Sample size
    if len(shadow_events) < 10000:
        return False, f"Only {len(shadow_events)} samples (min: 10,000)"

    # Check 3: Drift severity
    drift_metrics = calculate_rolling_drift()
    if drift_metrics['severity'] in ['HIGH', 'CRITICAL']:
        return False, f"Drift severity is {drift_metrics['severity']}"

    # Check 4: Recent escalations
    recent_escalations = check_recent_escalations(shadow_model_version, days=7)
    if recent_escalations:
        return False, f"Recent escalations detected: {recent_escalations}"

    # Check 5: Performance budgets
    latency_p99 = calculate_shadow_latency_p99(shadow_model_version)
    if latency_p99 > 0.75:
        return False, f"P99 latency too high: {latency_p99:.3f}s"

    return True, "Shadow mode completion criteria met"
```

---

## 9. MISSING EVENTS & NULL DELTA DETECTION

### 9.1 Missing Event Detection

**ALEX detects missing shadow events:**

```python
def detect_missing_shadow_events() -> List[str]:
    """
    Detect requests scored by production but not shadow
    """
    # Query production scoring logs
    production_requests = get_production_request_ids(last_hours=1)

    # Query shadow events
    shadow_request_ids = (
        db.query(ShadowEvent.request_id)
        .filter(ShadowEvent.scored_at > datetime.utcnow() - timedelta(hours=1))
        .all()
    )
    shadow_request_ids = {r[0] for r in shadow_request_ids}

    # Find missing
    missing_request_ids = [
        req_id for req_id in production_requests
        if req_id not in shadow_request_ids
    ]

    if missing_request_ids:
        alert_ml_team({
            "alert": "MISSING_SHADOW_EVENTS",
            "count": len(missing_request_ids),
            "sample_ids": missing_request_ids[:10],
            "action": "Investigate shadow scoring failures"
        })

    return missing_request_ids
```

### 9.2 Null Delta Detection

**ALEX detects null/invalid deltas:**

```python
def detect_invalid_deltas() -> List[str]:
    """
    Detect shadow events with invalid deltas
    """
    invalid_events = (
        db.query(ShadowEvent)
        .filter(
            (ShadowEvent.score_delta == None) |
            (ShadowEvent.score_delta_pct == None) |
            (ShadowEvent.abs_score_delta == None)
        )
        .filter(ShadowEvent.scored_at > datetime.utcnow() - timedelta(hours=24))
        .all()
    )

    if invalid_events:
        raise GovernanceViolation(
            f"Found {len(invalid_events)} shadow events with null deltas. "
            f"All deltas must be calculated and stored."
        )

    return [e.request_id for e in invalid_events]
```

### 9.3 Negative Delta Analysis

**Track and analyze negative deltas (shadow < production):**

```python
def analyze_negative_deltas() -> Dict:
    """
    Analyze cases where shadow scores lower than production
    """
    negative_delta_events = (
        db.query(ShadowEvent)
        .filter(ShadowEvent.score_delta < 0)
        .filter(ShadowEvent.scored_at > datetime.utcnow() - timedelta(hours=24))
        .all()
    )

    total_events = db.query(ShadowEvent).count()
    negative_rate = len(negative_delta_events) / total_events if total_events > 0 else 0

    analysis = {
        'negative_count': len(negative_delta_events),
        'total_count': total_events,
        'negative_rate': negative_rate,
        'mean_negative_delta': np.mean([e.score_delta for e in negative_delta_events]),
        'interpretation': (
            'Shadow model is generally more conservative (lower risk scores)'
            if negative_rate > 0.5
            else 'Shadow model is generally more aggressive (higher risk scores)'
        )
    }

    return analysis
```

---

## 10. UNIT TEST COVERAGE REQUIREMENTS

### 10.1 Required Test Coverage

**ALEX enforces minimum test coverage for shadow mode:**

| Component | Coverage Target | Enforcement |
|-----------|----------------|-------------|
| **Shadow Event Logging** | 100% | CI blocks < 100% |
| **Drift Calculation** | 100% | CI blocks < 100% |
| **Integrity Flags** | 100% | CI blocks < 100% |
| **Statistical Tests** | > 95% | CI blocks < 95% |
| **Escalation Logic** | > 90% | CI blocks < 90% |

### 10.2 Required Test Cases

```python
# tests/test_shadow_governance.py
import pytest
from app.services.shadow import ShadowScoringService, DriftProbe

class TestShadowGovernance:
    """ALEX-enforced shadow mode governance tests"""

    def test_required_fields_validation(self):
        """All required fields must be present"""
        shadow_service = ShadowScoringService()

        # Missing request_id
        incomplete_event = {
            'shipment_id': 'ship_001',
            'production_score': 0.25,
            'shadow_score': 0.30
        }

        with pytest.raises(GovernanceViolation, match="missing required fields"):
            shadow_service.log_shadow_event(incomplete_event)

    def test_version_synchronization(self):
        """Dummy and real endpoints must use same shadow version"""
        from app.config import validate_version_synchronization

        # Mock different versions
        with patch('app.config.get_dummy_endpoint_shadow_version', return_value='v0.3.0'):
            with patch('app.config.get_real_endpoint_shadow_version', return_value='v0.2.0'):
                with pytest.raises(GovernanceViolation, match="Version mismatch"):
                    validate_version_synchronization()

    def test_drift_severity_classification(self):
        """Drift severity must be classified correctly"""
        from app.services.shadow import classify_drift_severity

        # LOW drift
        low_metrics = {
            'mean_abs_delta': 0.05,
            'p95_abs_delta': 0.10,
            'p99_abs_delta': 0.15,
            'extreme_delta_rate': 0.01,
            'kl_divergence': 0.05
        }
        assert classify_drift_severity(low_metrics) == 'LOW'

        # CRITICAL drift
        critical_metrics = {
            'mean_abs_delta': 0.25,
            'p95_abs_delta': 0.40,
            'p99_abs_delta': 0.50,
            'extreme_delta_rate': 0.15,
            'kl_divergence': 0.30
        }
        assert classify_drift_severity(critical_metrics) == 'CRITICAL'

    def test_escalation_logic(self):
        """High drift must trigger escalation"""
        from app.services.shadow import escalate_shadow_drift

        with patch('app.services.shadow.alert_ml_team') as mock_alert:
            escalate_shadow_drift(
                drift_severity='HIGH',
                drift_metrics={'mean_abs_delta': 0.18},
                shadow_model_version='v0.3.0'
            )

            # Verify alert was sent
            mock_alert.assert_called_once()
            assert 'DEPLOYMENT BLOCKED' in mock_alert.call_args[0][0]['action']

    def test_integrity_flags_calculation(self):
        """Integrity flags must be calculated correctly"""
        from app.services.shadow import calculate_integrity_flags

        flags = calculate_integrity_flags(
            production_score=0.20,
            shadow_score=0.55,  # Large delta (0.35)
            production_latency_ms=150,
            shadow_latency_ms=250,  # Slow shadow
            features={'feature1': 0.5},
            catalog={'feature1': {'min_value': 0.0, 'max_value': 1.0}}
        )

        assert flags['large_delta'] == True
        assert flags['extreme_delta'] == True
        assert flags['slow_shadow'] == True

    def test_missing_event_detection(self):
        """Missing shadow events must be detected"""
        from app.services.shadow import detect_missing_shadow_events

        with patch('app.services.shadow.get_production_request_ids', return_value=['req_1', 'req_2', 'req_3']):
            with patch('app.services.shadow.db.query') as mock_query:
                # Mock: Only req_1 has shadow event
                mock_query.return_value.filter.return_value.all.return_value = [('req_1',)]

                missing = detect_missing_shadow_events()

                assert len(missing) == 2
                assert 'req_2' in missing
                assert 'req_3' in missing
```

---

## 11. ACCEPTANCE CRITERIA

**Shadow Mode is governance-compliant when:**

1. ✅ All required fields present in shadow events
2. ✅ Version synchronization enforced (dummy = real)
3. ✅ Drift metrics calculated for all events
4. ✅ Statistical significance tests implemented
5. ✅ Integrity flags generated for all events
6. ✅ Escalation logic operational
7. ✅ DriftProbe integrated and monitoring
8. ✅ Performance budgets monitored (p95/p99)
9. ✅ Missing event detection active
10. ✅ Shadow completion criteria enforced

---

## 12. AGENT OBLIGATIONS

### Cody (GID-01) - Backend Engineering

**Must:**
- Implement complete shadow event logging
- Ensure version synchronization across endpoints
- Add drift calculation to all shadow requests
- Implement integrity flag generation
- Achieve 100% test coverage for shadow logging/drift

**Cannot:**
- Deploy shadow changes without version sync validation
- Log shadow events missing required fields
- Skip integrity flag calculation

### Maggie (GID-02) - ML Engineering

**Must:**
- Review drift metrics before promoting models
- Document explanations for high drift
- Analyze negative delta patterns
- Validate shadow completion criteria

**Cannot:**
- Promote models with HIGH or CRITICAL drift
- Ignore escalation alerts
- Deploy without minimum shadow duration

---

## 13. CHANGELOG

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-11 | Initial Shadow Mode Governance (ALEX Protection Mode v2.1) |

---

## 14. REFERENCES

- [ALEX Protection Manual](./ALEX_PROTECTION_MANUAL.md)
- [Model Ingestion Governance](./MODEL_INGESTION_GOVERNANCE.md)
- [Model Lifecycle Policy v2](./MODEL_LIFECYCLE_POLICY_v2.md)
- [DriftProbe Documentation](../../chainiq-service/docs/drift_probe.md)

---

**ALEX (GID-08) - Shadow Mode Is Not a Formality • High Drift = Blocked Deployment • Safety First**
