# ChainIQ Calibration Plan v1

**PAC Reference:** PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008  
**Author:** Maggie (GID-10) — ML & Applied AI Lead  
**Status:** CANONICAL  
**Version:** v1.0.0  
**Applies To:** ChainIQ Risk Model v1  

---

## 1. Calibration Objective

Risk scores emitted by ChainIQ Risk Model v1 must be **well-calibrated probability estimates**. A score of 0.30 should correspond to approximately 30% empirical loss rate for shipments with similar risk profiles.

**Why Calibration Matters:**
- Enables consistent risk-based pricing decisions
- Supports regulatory requirements for probability-based disclosures
- Allows aggregation of risk across portfolios
- Ensures operator trust through predictable score behavior

---

## 2. Calibration Methodology

### 2.1 Primary Method: Platt Scaling

**Post-hoc calibration** using isotonic regression or Platt scaling on held-out validation data.

```python
# Platt Scaling (sigmoid calibration)
calibrated_prob = 1 / (1 + exp(-(A * raw_score + B)))

# Parameters A, B fitted on validation set to minimize:
# negative_log_likelihood(calibrated_prob, actual_outcomes)
```

**Why Platt Scaling:**
- Preserves monotonicity of raw scores
- Minimal parameters (A, B only)
- Interpretable transformation
- Works well with EBM-style models

### 2.2 Alternative: Isotonic Regression

If Platt scaling produces poor fit (ECE > 0.05), use isotonic regression:

```python
# Non-parametric, monotonic calibration
isotonic_calibrator = IsotonicRegression(out_of_bounds='clip')
calibrated_prob = isotonic_calibrator.fit_transform(raw_scores, outcomes)
```

### 2.3 Calibration Data Split

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Partitioning                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Training Data (T-30 to T-6 months)                             │
│  └─ Used for EBM model training                                 │
│                                                                 │
│  Calibration Data (T-6 to T-3 months)                           │
│  └─ Used for fitting Platt parameters (A, B)                    │
│  └─ NOT seen during model training                              │
│                                                                 │
│  Test Data (T-3 to T-0 months)                                  │
│  └─ Used for final calibration evaluation                       │
│  └─ NOT seen during training OR calibration                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Temporal split is mandatory** — no random sampling that mixes time periods.

---

## 3. Calibration Metrics

### 3.1 Expected Calibration Error (ECE)

Primary calibration metric:

```python
def expected_calibration_error(probs, outcomes, n_bins=10):
    """
    ECE = Σ (|B_m| / N) * |acc(B_m) - conf(B_m)|
    
    Where:
    - B_m = samples in bin m
    - acc(B_m) = actual positive rate in bin
    - conf(B_m) = average predicted probability in bin
    """
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i+1])
        if mask.sum() > 0:
            acc = outcomes[mask].mean()
            conf = probs[mask].mean()
            ece += (mask.sum() / len(probs)) * abs(acc - conf)
    return ece
```

**Target:** ECE < 0.03 (3%)

### 3.2 Maximum Calibration Error (MCE)

```python
def max_calibration_error(probs, outcomes, n_bins=10):
    """
    MCE = max over bins |acc(B_m) - conf(B_m)|
    """
    # Worst-case error in any single bin
```

**Target:** MCE < 0.10 (10%)

### 3.3 Brier Score

Overall probability accuracy:

```python
def brier_score(probs, outcomes):
    """
    Brier = (1/N) * Σ (prob_i - outcome_i)²
    """
    return np.mean((probs - outcomes) ** 2)
```

**Target:** Brier < 0.15

### 3.4 Log Loss

```python
def log_loss(probs, outcomes, eps=1e-15):
    """
    LogLoss = -(1/N) * Σ [y*log(p) + (1-y)*log(1-p)]
    """
    probs = np.clip(probs, eps, 1 - eps)
    return -np.mean(outcomes * np.log(probs) + (1 - outcomes) * np.log(1 - probs))
```

---

## 4. Reliability Diagram

### 4.1 Construction

```python
def reliability_diagram(probs, outcomes, n_bins=10):
    """
    Plot actual vs. predicted probability across bins.
    Perfect calibration = diagonal line.
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = []
    bin_accuracies = []
    bin_counts = []
    
    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i+1])
        if mask.sum() > 0:
            bin_centers.append(probs[mask].mean())
            bin_accuracies.append(outcomes[mask].mean())
            bin_counts.append(mask.sum())
    
    return bin_centers, bin_accuracies, bin_counts
```

### 4.2 Acceptance Criteria

```
┌─────────────────────────────────────────────────────────────────┐
│                    Reliability Diagram                          │
│                                                                 │
│  1.0 │                                        ∙∙∙∙∙∙            │
│      │                                   ∙∙∙∙∙                   │
│  0.8 │                              ∙∙∙∙∙                        │
│      │                         ∙∙∙∙∙                             │
│  0.6 │                    ∙∙∙∙∙         ← Perfect Calibration    │
│ Actual│               ∙∙∙∙∙                                      │
│  0.4 │          ∙∙∙∙∙∙                                           │
│      │     ∙∙∙∙∙                                                 │
│  0.2 │∙∙∙∙∙                                                      │
│      │                                                           │
│  0.0 └───────────────────────────────────────────────────────   │
│      0.0   0.2   0.4   0.6   0.8   1.0                          │
│                    Predicted                                     │
│                                                                 │
│  ACCEPTANCE: All points within ±0.05 of diagonal                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Calibration by Segment

### 5.1 Stratified Calibration Checks

Calibration must be verified **separately** for key segments:

| Segment | Stratification | Target ECE |
|---------|---------------|------------|
| By Corridor | Top 10 corridors | < 0.05 |
| By Mode | AIR, SEA, ROAD, RAIL | < 0.05 |
| By Financing Type | LOC, Open Account, etc. | < 0.05 |
| By Risk Tier | LOW, MODERATE, HIGH, SEVERE, CRITICAL | < 0.05 |
| By Counterparty Tier | Tier 1-5 | < 0.05 |

### 5.2 Segment-Level Recalibration

If a segment shows ECE > 0.05:

1. **Option A:** Fit segment-specific Platt parameters
2. **Option B:** Add segment indicator as calibration feature
3. **Option C:** Flag segment for manual review (temporary)

**Preferred:** Single global calibration if possible (simpler, more robust)

---

## 6. Calibration Monitoring

### 6.1 Production Monitoring

```yaml
monitoring:
  frequency: daily
  lookback_window: 30_days_rolling
  
  alerts:
    - metric: ECE
      threshold: 0.05
      action: ALERT_ML_TEAM
      
    - metric: ECE
      threshold: 0.08
      action: TRIGGER_RECALIBRATION
      
    - metric: score_distribution_shift
      threshold: 0.20  # KL divergence
      action: ALERT_ML_TEAM
```

### 6.2 Drift Detection

```python
def detect_calibration_drift(
    recent_probs: np.ndarray,
    recent_outcomes: np.ndarray,
    baseline_ece: float,
    threshold: float = 0.02
) -> bool:
    """
    Returns True if calibration has drifted beyond threshold.
    """
    current_ece = expected_calibration_error(recent_probs, recent_outcomes)
    return abs(current_ece - baseline_ece) > threshold
```

---

## 7. Recalibration Triggers

### 7.1 Automatic Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| ECE Drift | ECE > 0.08 for 7 consecutive days | Initiate recalibration |
| Outcome Shift | Base rate shifts > 20% | Initiate recalibration |
| Feature Drift | Feature distribution shift detected | Evaluate recalibration |
| New Data Volume | 10,000 new outcomes available | Evaluate recalibration |

### 7.2 Recalibration Process

```
┌─────────────────────────────────────────────────────────────────┐
│                  Recalibration Workflow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1] TRIGGER DETECTED                                           │
│       └─ Log trigger event and metrics                          │
│                                                                 │
│  [2] DATA COLLECTION                                            │
│       └─ Gather recent outcomes (last 90 days)                  │
│       └─ Validate data quality                                  │
│                                                                 │
│  [3] CALIBRATION FITTING                                        │
│       └─ Refit Platt parameters on new data                     │
│       └─ Compute new ECE, MCE, Brier                            │
│                                                                 │
│  [4] VALIDATION                                                 │
│       └─ Compare new calibration vs. old on holdout             │
│       └─ Generate reliability diagram                           │
│                                                                 │
│  [5] REVIEW GATE                                                │
│       └─ ML Lead (Maggie) reviews calibration                   │
│       └─ Approval required for production update                │
│                                                                 │
│  [6] DEPLOYMENT                                                 │
│       └─ Update calibration parameters (A, B)                   │
│       └─ Log version change                                     │
│       └─ Model weights remain FROZEN                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Note:** Recalibration updates only the Platt parameters. Model weights remain frozen.

---

## 8. Calibration Artifacts

### 8.1 Stored Artifacts

```yaml
calibration_artifacts:
  - name: platt_parameters.json
    content:
      A: float  # Slope
      B: float  # Intercept
      fitted_on: datetime
      data_window: [start_date, end_date]
      sample_size: int
      
  - name: calibration_metrics.json
    content:
      ece: float
      mce: float
      brier: float
      log_loss: float
      
  - name: reliability_diagram.png
    content: visual artifact
    
  - name: segment_calibration.json
    content:
      by_corridor: dict
      by_mode: dict
      by_financing_type: dict
```

### 8.2 Artifact Versioning

Every calibration update creates a new versioned artifact:

```
calibration/
├── v1.0.0/
│   ├── platt_parameters.json
│   ├── calibration_metrics.json
│   └── reliability_diagram.png
├── v1.0.1/
│   └── ...
└── current -> v1.0.1/
```

---

## 9. Calibration Validation Checklist

Before deploying new calibration:

- [ ] ECE < 0.03 on holdout data
- [ ] MCE < 0.10 on holdout data
- [ ] Brier score improved or stable
- [ ] Reliability diagram within ±0.05 of diagonal
- [ ] Segment-level ECE < 0.05 for all major segments
- [ ] No score distribution anomalies
- [ ] Review approved by ML Lead
- [ ] Artifacts versioned and stored
- [ ] Audit log entry created

---

## 10. Calibration Evidence for PDO

Every Risk PDO includes calibration evidence:

```json
{
  "calibration": {
    "calibrator_version": "v1.0.1",
    "method": "platt_scaling",
    "parameters": {
      "A": 1.234,
      "B": -0.567
    },
    "validation_metrics": {
      "ece": 0.024,
      "mce": 0.078,
      "brier": 0.142
    },
    "validation_window": {
      "start": "2025-09-01",
      "end": "2025-11-30"
    },
    "validation_sample_size": 15234
  }
}
```

---

## 11. Attestation

```yaml
attestation:
  pac_id: PAC-BENSON-EXEC-MAGGIE-CHAINIQ-008
  author: Maggie (GID-10)
  role: ML & Applied AI Lead
  document: calibration_plan.md
  calibration_method: platt_scaling
  target_ece: 0.03
  created_at: 2025-12-26T00:00:00Z
  status: CANONICAL
```

---

**END OF DOCUMENT — calibration_plan.md**
