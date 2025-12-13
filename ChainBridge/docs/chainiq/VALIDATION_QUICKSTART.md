# ChainIQ ML Model Validation - Quick Start Guide

This guide explains how to validate trained ML models against real ingestion-derived shipment data.

---

## Quick Start

### Run Full Validation

```bash
cd ChainBridge/chainiq-service
python -m app.ml.validation_real_data full-eval --limit 1000
```

**Output:**
- Production Readiness Score (0-100)
- Risk model AUC and precision metrics
- Anomaly model score distribution
- Feature drift analysis
- Two markdown evaluation reports

**Execution Time:** <3 seconds

---

## CLI Commands

### 1. Full Evaluation (Recommended)

```bash
python -m app.ml.validation_real_data full-eval [options]
```

**Options:**
- `--data PATH` - Path to JSONL training rows (omit to use synthetic demo)
- `--limit N` - Max rows to load (default: 5000)

**Output Files:**
- `docs/chainiq/REAL_DATA_EVAL_RISK.md` - Risk model evaluation
- `docs/chainiq/REAL_DATA_EVAL_ANOMALY.md` - Anomaly model evaluation

### 2. Risk Model Only

```bash
python -m app.ml.validation_real_data evaluate-risk --data path/to/rows.jsonl
```

**Output:** JSON with AUC, precision, recall, bad outcome rate

### 3. Anomaly Model Only

```bash
python -m app.ml.validation_real_data evaluate-anomaly --limit 5000
```

**Output:** JSON with score distribution, corridor analysis, outlier detection

---

## Key Metrics

### Production Readiness Score

**Formula:**
- Start: 100 points
- -20 if AUC < 0.75 (-10 if < 0.80)
- -20 if Precision@10% < 0.40 (-10 if < 0.45)
- -30 if >10 high-drift features (-15 if >5)

**Thresholds:**
- ≥75: **PRODUCTION READY** ✅
- 50-74: **REQUIRES FIXES** ⚠️
- <50: **NOT READY** 🛑

### Risk Model Metrics

| Metric | Target | Meaning |
|--------|--------|---------|
| **AUC** | ≥0.75 | Overall discrimination ability |
| **Precision@10%** | ≥0.40 | Accuracy on top 10% riskiest shipments |
| **Bad Outcome Rate** | 5-15% | Prevalence of claims/disputes/delays |

### Anomaly Model Metrics

| Metric | Target | Meaning |
|--------|--------|---------|
| **Score Mean** | -0.10 to +0.10 | Average anomaly score |
| **Outlier Corridors** | <3 | Number of problematic trade lanes |
| **Score Std Dev** | <0.15 | Prediction stability |

### Feature Drift

| Threshold | Status | Action |
|-----------|--------|--------|
| <30% | ✅ Acceptable | No action |
| 30-50% | ⚠️ Medium | Monitor weekly |
| >50% | 🛑 High | Consider retraining |

---

## Example Output

```
======================================================================
VALIDATION COMPLETE
======================================================================
Production Readiness Score: 80/100
Risk Model AUC: 0.750
Anomaly Score Mean: -0.050
High Drift Features: 0

✓ Full evaluation complete. See docs/chainiq/ for reports.
```

---

## Interpreting Results

### Risk Model Report (REAL_DATA_EVAL_RISK.md)

**Key Sections:**
1. **Executive Summary** - Readiness score, key metrics, pass/fail status
2. **Detailed Performance** - AUC, precision, recall, score distribution
3. **Feature Drift** - Top 10 drifted features with percentages
4. **Deployment Recommendations** - Approved actions, mitigations, blockers
5. **ALEX Governance** - Compliance checklist

**Decision Matrix:**

| AUC | Prec@10% | Drift | Decision |
|-----|----------|-------|----------|
| ≥0.75 | ≥0.40 | <5 | ✅ Deploy to staging |
| ≥0.70 | ≥0.35 | <10 | ⚠️ Deploy with monitoring |
| <0.70 | <0.35 | >10 | 🛑 Retrain required |

### Anomaly Model Report (REAL_DATA_EVAL_ANOMALY.md)

**Key Sections:**
1. **Executive Summary** - Score metrics, outlier corridors, health status
2. **Score Distribution** - Mean, std dev, range analysis
3. **Corridor-Level Analysis** - Per-corridor scores and counts
4. **Outlier Detection** - Corridors with unusually low scores
5. **Deployment Recommendations** - Informational mode, monitoring plan

**Outlier Corridor Threshold:** Score < -0.15 (unusually anomalous)

---

## Integration with Production

### Phase 1: Staging (Weeks 1-2)

```bash
# Run validation on staging data
python -m app.ml.validation_real_data full-eval --data staging/training_rows.jsonl --limit 10000
```

**Acceptance Criteria:**
- Readiness score ≥75
- AUC ≥0.73 (allows 2% degradation)
- High drift features <5

### Phase 2: Shadow Mode (Weeks 3-4)

```bash
# Daily validation on production data
python -m app.ml.validation_real_data full-eval --data prod/training_rows.jsonl --limit 5000

# Check for alerts
grep "HIGH DRIFT" docs/chainiq/REAL_DATA_EVAL_RISK.md
grep "OUTLIER" docs/chainiq/REAL_DATA_EVAL_ANOMALY.md
```

**Monitoring Alerts:**
- AUC drops below 0.70
- Precision@10% drops below 0.35
- Drift exceeds 40% on any feature
- >3 outlier corridors detected

### Phase 3: Production Rollout (Weeks 5+)

Enable auto-flagging for:
- Risk scores > 0.85 (top 5% riskiest)
- Anomaly scores < -0.20 (top 1% most anomalous)

**Weekly cadence:**
```bash
# Monday: Full evaluation
python -m app.ml.validation_real_data full-eval --data prod/last_week.jsonl

# Review reports
cat docs/chainiq/REAL_DATA_EVAL_RISK.md | grep "Production Readiness"
```

---

## Troubleshooting

### Issue: "Could not load risk model"

**Cause:** Model pickle file not found or corrupted

**Fix:**
```bash
# Check model exists
ls -lh ml_models/risk_v0.2.0.pkl

# If missing, retrain (see PAC-004)
python -m app.ml.training_v02 train-risk
```

### Issue: "High drift features: 10+"

**Cause:** Real data distribution differs significantly from synthetic training data

**Fix:**
1. Review drifted features in REAL_DATA_EVAL_RISK.md
2. If drift >50%, retrain on real production data
3. Otherwise, monitor weekly for continued drift

### Issue: "AUC < 0.70"

**Cause:** Model not performing well on real data

**Fix:**
1. Check bad outcome rate (should be 5-15%)
2. If rate is outside range, retrain with balanced sampling
3. If rate is correct, consider feature engineering improvements

### Issue: "Outlier corridors detected"

**Cause:** Certain trade lanes have unusual shipment patterns

**Fix:**
1. Investigate outlier corridors in REAL_DATA_EVAL_ANOMALY.md
2. Consider corridor-specific anomaly thresholds
3. Review for data quality issues in those lanes

---

## Testing

### Run Unit Tests

```bash
cd ChainBridge/chainiq-service
PYTHONPATH=$(pwd) python tests/test_validation_real_data.py
```

**Expected Output:**
```
======================================================================
ALL TESTS PASSED ✅
======================================================================
```

**Test Coverage:**
- ✅ Synthetic data generation
- ✅ Feature range validation
- ✅ Risk model evaluation
- ✅ Anomaly model evaluation
- ✅ Drift detection
- ✅ End-to-end pipeline

---

## File Locations

```
ChainBridge/chainiq-service/
├── app/ml/
│   ├── validation_real_data.py      # Main validation module
│   ├── training_v02.py               # Training pipeline (PAC-004)
│   ├── datasets.py                   # Data structures
│   └── ingestion.py                  # Event parsing (PAC-005)
├── tests/
│   └── test_validation_real_data.py  # Unit tests
├── ml_models/
│   ├── risk_v0.2.0.pkl              # Trained risk model
│   ├── anomaly_v0.2.0.pkl           # Trained anomaly model
│   ├── risk_v0.2.0_metrics.json     # Training metrics
│   └── anomaly_v0.2.0_metrics.json  # Training metrics
└── docs/chainiq/
    ├── REAL_DATA_EVAL_RISK.md       # Risk evaluation report
    ├── REAL_DATA_EVAL_ANOMALY.md    # Anomaly evaluation report
    └── MAGGIE_PAC005_WRAP.md        # PAC completion summary
```

---

## API Reference

### load_ingested_training_rows()

```python
def load_ingested_training_rows(
    input_path: str | None = None,
    limit: int = 5000,
) -> list[dict[str, Any]]
```

Load training rows from JSONL file or generate synthetic demo data.

**Returns:** List of training row dicts with keys:
- `features` - ShipmentFeaturesV0 dict
- `had_claim` - bool
- `had_dispute` - bool
- `severe_delay` - bool
- `loss_amount` - float | None
- `is_known_anomaly` - bool
- `recorded_at` - ISO timestamp
- `data_source` - str

### validate_feature_ranges()

```python
def validate_feature_ranges(
    real_rows: list[dict[str, Any]],
    synthetic_stats: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Compare real data feature ranges to synthetic training baseline.

**Returns:** Dict with keys:
- `real_stats` - Per-feature (min, max, mean, std)
- `drift_results` - Per-feature drift percentages
- `high_drift_features` - List of (feature, drift_pct) tuples

### evaluate_risk_model_on_real_data()

```python
def evaluate_risk_model_on_real_data(
    real_rows: list[dict[str, Any]],
    model_path: str | None = None,
) -> dict[str, Any]
```

Evaluate risk model performance on real data.

**Returns:** Dict with keys:
- `auc` - float (0-1)
- `precision_at_10pct` - float
- `precision_at_50pct` - float
- `recall_at_50pct` - float
- `bad_outcome_rate` - float
- `score_mean` - float
- `score_std` - float

### evaluate_anomaly_model_on_real_data()

```python
def evaluate_anomaly_model_on_real_data(
    real_rows: list[dict[str, Any]],
    model_path: str | None = None,
) -> dict[str, Any]
```

Evaluate anomaly model on real data.

**Returns:** Dict with keys:
- `score_mean` - float
- `score_std` - float
- `score_min` - float
- `score_max` - float
- `corridor_stats` - Dict[str, Dict]
- `outlier_corridors` - List[(corridor, score)]

### full_evaluation()

```python
def full_evaluation(
    data_path: str | None = None,
    limit: int = 5000,
) -> dict[str, Any]
```

Run complete validation pipeline.

**Returns:** Dict with keys:
- `risk_results` - Risk model metrics
- `anomaly_results` - Anomaly model metrics
- `drift_results` - Drift analysis
- `range_results` - Feature range validation
- `readiness_score` - int (0-100)

---

## Next Steps

1. **Review evaluation reports:**
   - [Risk Model Report](./REAL_DATA_EVAL_RISK.md)
   - [Anomaly Model Report](./REAL_DATA_EVAL_ANOMALY.md)
   - [PAC-005 WRAP](./MAGGIE_PAC005_WRAP.md)

2. **Run validation on your data:**
   ```bash
   python -m app.ml.validation_real_data full-eval --data your_data.jsonl
   ```

3. **Set up monitoring:**
   - Weekly validation runs
   - Alert on readiness score <75
   - Track drift over time

4. **Plan retraining (PAC-006):**
   - Collect 10K+ real production shipments
   - Retrain on real data
   - Compare v0.2.0 (synthetic) vs v0.3.0 (real)

---

**Created by:** Maggie (GID-10) 🩷
**PAC:** MAGGIE-PAC-005
**Date:** 2025-12-11
**Status:** Production Ready (Staging + Shadow Mode)
