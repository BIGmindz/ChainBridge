# ChainIQ ML v0.2 Architecture & Training Plan

**Status**: Design & Scaffold Phase
**Owner**: Maggie (GID-10) – ML & Applied AI Lead
**Date**: December 11, 2025
**Related**: `CHAINIQ_LAB_CHARTER.md`, `CHAINIQ_ML_CONTRACT_V0.md`

---

## Executive Summary

**Purpose**: v0.2 establishes the **offline training architecture** for ChainIQ risk and anomaly models WITHOUT changing production behavior. This PAC scaffolds the pipeline for training real glass-box ML models that will eventually replace DummyRiskModel and DummyAnomalyModel.

**Key Principle**: **Code = Cash**. Every ML model must demonstrably improve:
- Straight-through processing (STP) rates
- Risk prediction accuracy (fewer false positives/negatives)
- Margin protection (early detection of high-risk shipments)

**Non-Goal**: v0.2 does NOT deploy trained models to production. That's v0.3 (shadow mode + A/B testing).

---

## v0.1 → v0.2 → v0.3 Progression

| Version | Status | Behavior | Purpose |
|---------|--------|----------|---------|
| **v0.1** | ✅ Deployed | DummyRiskModel / DummyAnomalyModel return deterministic scores based on 2-3 features | Establish API contracts, observability, and test baselines |
| **v0.2** | 🔨 This PAC | Training pipeline + real models in **offline mode** only | Build, train, and validate glass-box models on historical data |
| **v0.3** | 🔮 Future | Shadow mode: Dummy + Real models run in parallel, log discrepancies | A/B test, calibrate, promote real models to primary |

---

## Data Schema & Training Rows

### ShipmentFeaturesV0 → Training Row Mapping

**Input**: `app/models/features.py::ShipmentFeaturesV0` (50+ features covering operational, financial, IoT, and sentiment data)

**Training Row Structure** (`app/ml/datasets.py::ShipmentTrainingRow`):
```python
class ShipmentTrainingRow:
    # Features (from ShipmentFeaturesV0)
    features: ShipmentFeaturesV0

    # Labels (ground truth outcomes)
    ## Risk Model Labels
    had_claim: bool                    # Did this shipment result in an insurance claim?
    had_dispute: bool                  # Did customer dispute charges?
    severe_delay: bool                 # Was shipment >48h late?
    loss_amount: float | None          # $ value of loss (if any)

    ## Anomaly Model Labels (optional - may use unsupervised)
    is_known_anomaly: bool            # Manual flag for known unusual shipments
    anomaly_type: str | None          # "route_deviation" | "custody_gap" | "temp_excursion" | None

    # Metadata
    recorded_at: datetime              # When this outcome was recorded
    data_source: str                   # "production" | "synthetic" | "backfill"
    model_version_at_scoring: str      # What model version scored this originally
```

### Label Design Philosophy

**Risk Models**: Supervised binary classification
- **Target**: `bad_outcome = had_claim OR had_dispute OR severe_delay`
- **Rationale**: Glass-box models need clear binary targets. Multi-outcome models come later.
- **Class balance**: Expect ~5-15% positive class in production data (most shipments are clean)

**Anomaly Models**: Semi-supervised / unsupervised
- **Approach 1 (Unsupervised)**: Isolation Forest on all features, flag top 5% as anomalies
- **Approach 2 (Weak supervision)**: Train on known clean shipments, flag deviations
- **Rationale**: True anomalies are rare and expensive to label; start unsupervised, refine with feedback

---

## Model Families & Selection Criteria

### Risk Models (Supervised)

**Candidates** (in priority order):
1. **Logistic Regression with Monotone Constraints**
   - Why: Fully interpretable, fast, enforces business logic (e.g., delay → higher risk)
   - Baseline: Simple feature set (delay, prior losses, lane sentiment)
   - Extended: All 50+ features with L1 regularization for feature selection

2. **Explainable Boosting Machines (EBM) / GA²Ms**
   - Why: Glass-box by design, handles non-linearities, built-in feature importance
   - Library: `interpret-ml` (Microsoft Research)
   - Trade-off: Slower training than logistic, but still fast inference

3. **Monotone Gradient Boosted Trees (XGBoost/LightGBM with constraints)**
   - Why: SOTA accuracy with monotonicity constraints on key features
   - Constraints: `delay_flag → +risk`, `prior_losses → +risk`, `on_time_pct → -risk`
   - Trade-off: Harder to explain individual splits vs EBM

**Disqualified**:
- ❌ Deep neural networks (opaque for financial decisions)
- ❌ Random forests without constraints (loses monotonicity guarantees)

### Anomaly Models (Unsupervised)

**Candidates**:
1. **Isolation Forest**
   - Why: Fast, interpretable via feature importance, handles mixed feature types
   - Baseline: Detect unusual combinations of dwell times, route deviations, ETA misses

2. **One-Class SVM**
   - Why: Robust to outliers, works well with normalized features
   - Trade-off: Slower than IsoForest, requires careful kernel selection

3. **Simple Statistical Rules (Fallback)**
   - Why: 100% interpretable, fast, no training needed
   - Example: Flag if `max_dwell > corridor_p95 * 2.5`

**Disqualified**:
- ❌ Autoencoders (opaque reconstruction errors, overkill for tabular data)

---

## Feature Engineering & Preprocessing

### Feature Groups (from ShipmentFeaturesV0)

1. **Core Numeric Features** (continuous)
   - `planned_transit_hours`, `actual_transit_hours`, `eta_deviation_hours`
   - `max_single_dwell_hours`, `total_dwell_hours`, `max_custody_gap_hours`
   - Preprocessing: StandardScaler or RobustScaler (resist outliers)

2. **Monotone Features** (business-logic constrained)
   - `delay_flag` → MUST increase risk
   - `prior_losses_flag` → MUST increase risk
   - `shipper_on_time_pct_90d` → MUST decrease risk (inverse)
   - Preprocessing: No scaling (keep as-is for monotone models)

3. **Categorical Features**
   - `mode`, `commodity_category`, `financing_type`, `counterparty_risk_bucket`
   - Preprocessing: Target encoding or one-hot (< 10 categories)

4. **Sentiment Features**
   - `lane_sentiment_score`, `macro_logistics_sentiment_score`, `sentiment_trend_7d`
   - Preprocessing: Clip to [0, 1], then scale if needed

5. **IoT Features** (optional, only if `has_iot_telemetry == 1`)
   - `temp_mean`, `temp_std`, `temp_out_of_range_pct`, `sensor_uptime_pct`
   - Preprocessing: Handle missingness (fill with corridor median or separate indicator)

### Preprocessing Pipeline (sklearn-compatible)

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.compose import ColumnTransformer

# Example (implemented in app/ml/preprocessing.py)
risk_preprocessor = ColumnTransformer(
    transformers=[
        ('numeric', RobustScaler(), ['actual_transit_hours', 'max_single_dwell_hours', ...]),
        ('monotone', 'passthrough', ['delay_flag', 'prior_losses_flag', ...]),
        ('sentiment', StandardScaler(), ['lane_sentiment_score', ...]),
        # Target encoding for categoricals happens in a separate step
    ],
    remainder='drop'
)
```

---

## Evaluation Metrics & Success Criteria

### Risk Model Evaluation

**Primary Metrics**:
1. **AUC-ROC**: Must exceed 0.75 (better than random + some signal)
   - Target: 0.80+ (strong discrimination)
   - Benchmark: DummyRiskModel effective AUC ~0.55 (barely better than coin flip)

2. **Precision @ Top 10%**: Of shipments flagged as highest risk, what % actually had bad outcomes?
   - Target: 30%+ precision (3x better than base rate if base rate is 10%)

3. **Calibration (Brier Score)**: Predicted probabilities match observed frequencies
   - Target: Brier < 0.15 (well-calibrated)
   - Tool: Reliability diagrams, Platt scaling if needed

**Secondary Metrics**:
- **Recall @ 80% Precision**: Can we catch most bad shipments without too many false alarms?
- **Feature Importance Stability**: Do top 10 features stay consistent across train/test splits?

### Anomaly Model Evaluation

**Primary Metrics** (harder without labels):
1. **True Positive Rate on Known Bad Shipments**: Of shipments that led to claims/disputes, what % were flagged as anomalous?
   - Target: 60%+ (catch most truly bad shipments)

2. **Alert Volume**: What % of total shipments are flagged?
   - Constraint: Must stay < 10% (else alert fatigue)

**Secondary Metrics**:
- **Feature Contribution Diversity**: Anomalies should be flagged for diverse reasons (not just one feature)
- **Corridor Consistency**: Anomaly rates should be similar across high-volume corridors (US-MX, CN-NL)

---

## Training Data Requirements

### Minimum Viable Dataset

- **Size**: 10,000+ shipments (historical)
- **Time Range**: Last 6-12 months (captures seasonal patterns)
- **Label Coverage**:
  - Risk: 500+ positive examples (bad outcomes)
  - Anomaly: 200+ known anomalies (if using semi-supervised)
- **Corridor Balance**: At least 1,000 shipments from each major corridor (US-MX, CN-NL, US-CA)

### Data Sources (Current Reality)

**⚠️ REALITY CHECK**: As of v0.2, we do NOT have production training data yet.

**Placeholder Strategy**:
1. **Synthetic Data** (`app/ml/datasets.py::generate_synthetic_training_data`)
   - Use ShipmentFeaturesV0 schema
   - Apply probabilistic rules: high delay → higher chance of bad_outcome
   - Generate 1,000 rows for smoke testing

2. **Backfill from Production Logs** (PAC-004 or later)
   - Parse `risk_score_log_events` and `anomaly_score_log_events`
   - Join with shipment outcomes (if available from ERP/TMS)

3. **Manual Labeling** (if needed)
   - Have operations team flag known problem shipments
   - Start with 100-200 hand-labeled examples

---

## Deployment Stages

### Stage 1: Offline Training & Validation (v0.2 - THIS PAC)

**What**:
- Train models on synthetic/historical data
- Save models to `ml_models/risk_v0.2.0.pkl` and `ml_models/anomaly_v0.2.0.pkl`
- Run offline evaluation (AUC, precision, calibration)

**Gatekeeper**: Models must beat dummy baselines on held-out test set

**Artifacts**:
- Trained model files (pickle or joblib)
- Evaluation report (markdown with metrics + charts)
- Feature importance summary

### Stage 2: Shadow Mode (v0.3 - Future)

**What**:
- Load both DummyRiskModel AND RealRiskModel_v0.2.0
- Run BOTH on every request
- Log predictions + discrepancies
- No change to API responses (still return dummy scores)

**Monitoring**:
- Track score distributions (dummy vs real)
- Alert if real model crashes or times out
- Measure latency impact (must stay < 50ms p95)

### Stage 3: A/B Testing (v0.3 - Future)

**What**:
- Route 10% of traffic to real models
- Compare downstream metrics:
  - STP rate (did we reduce manual reviews?)
  - False positive rate (did we over-flag clean shipments?)
  - Customer satisfaction (did risk alerts improve experience?)

**Rollout Plan**:
- Week 1: 10% traffic
- Week 2: 25% traffic (if metrics hold)
- Week 4: 50% traffic
- Week 6: 100% traffic + retire dummy models

### Stage 4: Promotion (v1.0 - Future)

**What**:
- `get_risk_model()` returns `RealRiskModel_v1.0.0` by default
- DummyModels archived as fallback
- Set up model retraining pipeline (monthly or quarterly)

---

## Code Structure (v0.2)

```
ChainBridge/chainiq-service/app/ml/
├── __init__.py              # Model registry (unchanged - still returns dummies)
├── base.py                  # BaseRiskModel, BaseAnomalyModel (unchanged)
├── dummy_models.py          # DummyRiskModel, DummyAnomalyModel (unchanged)
├── datasets.py              # NEW: ShipmentTrainingRow, data loaders
├── preprocessing.py         # NEW: Feature engineering, sklearn pipelines
├── training_v02.py          # NEW: Training interfaces (fit_risk_model_v02, etc.)
└── (future) real_models.py  # v0.3: RealRiskModel, RealAnomalyModel

ChainBridge/chainiq-service/tests/
├── test_ml_interfaces.py    # Existing dummy model tests (unchanged)
├── test_ml_training_v02.py  # NEW: Training pipeline tests

ChainBridge/ml_models/        # NEW directory for trained model artifacts
├── risk_v0.2.0.pkl
├── anomaly_v0.2.0.pkl
└── metadata_v0.2.0.json     # Feature names, training date, metrics
```

---

## Dependencies & Versioning

### Required (v0.2)

- **Python**: 3.11+ (for better type hints)
- **pydantic**: 2.x (already in use for ShipmentFeaturesV0)
- **pytest**: For testing

### Optional (Training Only - NOT in request path)

- **scikit-learn**: 1.3+ (for preprocessing, logistic regression, isolation forest)
  - ⚠️ Import guard: Use `try: import sklearn` inside training functions, NOT at module top
- **numpy**: 1.24+ (already a transitive dependency of pandas)
- **pandas**: 2.x (for data wrangling in training scripts)

### Explicitly NOT Added (Yet)

- ❌ `interpret-ml` (for EBM/GA²Ms) - add in PAC-004 if needed
- ❌ `xgboost`/`lightgbm` - add in PAC-005 if logistic isn't good enough
- ❌ `shap` - add in v0.3 for real feature importance explanations

---

## Open Questions & Risks

### Open Questions

1. **Where is ground truth label data?**
   - Risk: Do we have `had_claim`, `had_dispute` flags in our ERP/TMS?
   - Mitigation: Start with synthetic data, plan backfill in PAC-004

2. **What's the business tolerance for false positives?**
   - Risk: If we flag 20% of shipments as high-risk, ops team will ignore alerts
   - Mitigation: Set alert threshold to flag < 10% of shipments, tune for precision

3. **Do we need real-time retraining?**
   - Risk: Models may drift as supply chains change
   - Mitigation: Start with monthly batch retraining, add online learning later if needed

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Training data doesn't exist yet | Can't train real models | Use synthetic data for v0.2, plan backfill for PAC-004 |
| Models are too slow for production | Latency > 100ms kills UX | Benchmark inference time, use simpler models (logistic > trees > deep learning) |
| Glass-box models underperform vs black boxes | Pressure to use opaque models | Set clear accuracy floor: if glass-box < 0.75 AUC, investigate feature engineering before trying deep learning |
| Model explanations don't match stakeholder intuition | Trust issues | Validate feature importance with ops team, enforce monotonicity constraints |

---

## Next Steps (PAC-004 & Beyond)

1. **PAC-004**: Real training on synthetic data
   - Implement `fit_risk_model_v02()` with logistic regression
   - Implement `fit_anomaly_model_v02()` with isolation forest
   - Run offline evaluation, generate metrics report

2. **PAC-005**: Backfill production data
   - Parse risk_score_log_events from observability layer
   - Join with shipment outcomes (TBD: where is this data?)
   - Retrain models on real data

3. **PAC-006**: Shadow mode deployment
   - Load real models in `get_risk_model()` via config flag
   - Run dual scoring (dummy + real), log discrepancies
   - No change to API responses yet

4. **PAC-007**: A/B testing & promotion
   - Route 10% → 50% → 100% traffic to real models
   - Compare STP rates, false positive rates
   - Promote real models to primary if metrics improve

---

## Success Criteria for v0.2

✅ **Documentation**: This plan exists and is reviewed by Benson + Dan
✅ **Code Skeleton**: `datasets.py`, `preprocessing.py`, `training_v02.py` exist and pass tests
✅ **No Production Impact**: All 82 existing tests still pass, API behavior unchanged
✅ **Dry-Run Works**: Can run `python -m app.ml.training_v02` on synthetic data without errors
✅ **Dependencies Managed**: sklearn added to requirements, import-guarded to avoid FastAPI slowdown

---

**End of CHAINIQ_ML_V02_PLAN.md**

*For questions or changes, contact: Maggie (GID-10) or Benson*
