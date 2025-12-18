# Risk Signal Failure & Abuse Analysis

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-SIGNALS-01
> **Status**: SPEC (Design Only — No Code Changes)
> **Created**: 2025-12-17

---

## 1. BLUF

This document enumerates failure modes and abuse vectors for the glass-box risk signal layer. For each risk, we specify:

- **What can go wrong**
- **How to detect it**
- **How existing controls mitigate it**
- **Residual risk after mitigation**

The goal is proactive defense — identifying vulnerabilities before adversaries exploit them.

---

## 2. Risk Categories

| Category | Description | Severity |
|----------|-------------|----------|
| **Model Failure** | ML system produces incorrect outputs | HIGH |
| **Data Integrity** | Input data is corrupted or manipulated | CRITICAL |
| **Human Misuse** | Operators over-trust or misinterpret ML | HIGH |
| **Adversarial Attack** | Bad actors game the system | CRITICAL |
| **Operational Failure** | System availability or performance issues | MEDIUM |
| **Drift & Decay** | Model degrades over time | MEDIUM |

---

## 3. Model Failure Modes

### 3.1. MF-01: Feature Extraction Bug

**What**: Bug in feature preprocessing produces incorrect feature values.

**Example**:
```python
# Bug: Division by zero when no decisions
denial_rate = denied / (denied + allowed)  # Crashes if both are 0
```

**Detection**:
- Unit tests for edge cases (zero counts, null values)
- Feature value bounds checking (rate must be [0,1])
- Automated feature validation in pipeline

**Existing Control**:
- Deterministic feature preprocessing in `RiskFeaturePreprocessor`
- Explicit handling of missing values (return `null`, not impute)

**Residual Risk**: LOW — Standard software testing practices apply.

---

### 3.2. MF-02: Model Loading Failure

**What**: Serialized model fails to load (corruption, version mismatch).

**Example**:
```
Model file corrupted during deployment.
pickle.load() fails with UnpicklingError.
```

**Detection**:
- Model file hash verification on load
- Startup health check with test inference
- Model version compatibility check

**Existing Control**:
- Model versioning in `models/risk_model_vX.Y.Z/`
- `training_hash.sha256` integrity file
- Governance boot checks (`GOVERNANCE_BOOT_PASSED/FAILED`)

**Residual Risk**: LOW — Hash verification catches corruption.

---

### 3.3. MF-03: Numerical Instability

**What**: Floating point issues produce NaN, Inf, or extreme values.

**Example**:
```python
log_transform = math.log(count)  # log(0) = -inf
confidence = 1 / variance  # 1/0 = inf
```

**Detection**:
- Output bounds checking (score must be [0,1])
- NaN/Inf detection before publishing
- Automated alerts on invalid outputs

**Existing Control**:
- EBM models are inherently stable (tree-based)
- Log transform uses `log(count + 1)` to avoid log(0)

**Residual Risk**: LOW — Standard numerical hygiene.

---

### 3.4. MF-04: Monotonicity Violation

**What**: Model violates expected monotonic behavior.

**Example**:
```
Agent A: 10% denial rate → 0.25 risk score
Agent B: 20% denial rate → 0.20 risk score  # VIOLATION
```

**Detection**:
- Monotonicity validation during training
- Post-deployment monotonicity audit
- Comparison with constrained baseline model

**Existing Control**:
- `MONOTONIC_CONSTRAINTS` enforced in EBM training
- Secondary GAM model for cross-validation

**Residual Risk**: LOW — EBM enforces constraints by construction.

---

## 4. Data Integrity Risks

### 4.1. DI-01: Event Log Tampering

**What**: Adversary modifies governance event logs to manipulate risk scores.

**Attack**:
```
1. Attacker gains write access to event logs
2. Deletes DECISION_DENIED events for malicious agent
3. Risk score drops (fewer denials)
4. Operator trusts low risk score
```

**Detection**:
- Append-only log enforcement
- Event log hash chain integrity
- Gap detection in event sequence
- Cross-reference with telemetry sources

**Existing Control**:
- `GovernanceEventType` events are append-only by design
- Event sink uses structured logging to protected path
- ATLAS (GID-11) domain boundary enforcement
- Proofpack hash chain for audit trail

**Residual Risk**: MEDIUM — Requires compromised write access, but impact is high if achieved.

---

### 4.2. DI-02: Clock Skew Attack

**What**: Manipulated timestamps create artificial event patterns.

**Attack**:
```
1. Attacker compromises agent clock
2. Backdates denial events to outside rolling window
3. Recent window appears clean
4. Risk score drops
```

**Detection**:
- Server-side timestamp assignment (not client)
- Clock skew detection between sources
- Timestamp validation against monotonic sequence

**Existing Control**:
- `_utc_now()` in event creation uses server time
- Event IDs are server-generated

**Residual Risk**: LOW — Server-side timestamps prevent client manipulation.

---

### 4.3. DI-03: Event Flooding (Dilution)

**What**: Attacker floods system with benign events to dilute denial rate.

**Attack**:
```
1. Malicious agent issues 1000 safe requests
2. Only 10 malicious requests (denied)
3. Denial rate = 10/1010 = 0.99% (appears safe)
4. Risk score drops
```

**Detection**:
- Anomaly detection on event volume
- Rate limiting on event emission
- Absolute counts in addition to rates
- Time-normalized metrics

**Existing Control**:
- Composite signals include absolute counts (TMS-01: forbidden_tool_attempts)
- Not all signals are rate-based

**Mitigation Enhancement**:
- Add `event_volume_anomaly` signal to detect flooding
- Use time-weighted rates (recent events weighted more)

**Residual Risk**: MEDIUM — Dilution is a known statistical attack vector.

---

### 4.4. DI-04: Label Poisoning

**What**: Attacker corrupts training labels to bias model.

**Attack**:
```
1. Attacker gains access to label database
2. Marks malicious agents as "clean" (label flip)
3. Model trains on poisoned labels
4. Model learns to give low risk to malicious patterns
```

**Detection**:
- Label audit trail (who labeled what, when)
- Label quality checks (≥2 reviewers agree)
- Holdout validation set with trusted labels
- Periodic manual audit of high-confidence predictions

**Existing Control**:
- Training labels require "≥2 reviewers agree" (from Model Architecture)
- Model card documents label source and quality

**Residual Risk**: MEDIUM — Training is offline and audited, but poisoning is subtle.

---

## 5. Human Misuse Risks

### 5.1. HM-01: Over-Trust of ML

**What**: Operators treat ML risk score as ground truth.

**Scenario**:
```
1. Agent has 0.08 risk score (LOW tier)
2. Operator assumes agent is safe
3. Operator ignores suspicious behavior
4. Agent exploits blind spot
```

**Detection**:
- Track operator decisions vs ML recommendations
- Audit cases where low-risk agents caused incidents
- Monitor "rubber stamp" patterns

**Existing Control**:
- Governance contract: ML CANNOT ALLOW/DENY
- Risk score is annotation, not decision
- Audit records show separation

**Mitigation Enhancement**:
- Dashboard warning: "Risk score is advisory only"
- Periodic training on ML limitations
- Require explicit acknowledgment for low-risk overrides

**Residual Risk**: HIGH — Human psychology is hard to control.

---

### 5.2. HM-02: Under-Trust of ML

**What**: Operators ignore ML warnings entirely.

**Scenario**:
```
1. Agent has 0.85 risk score (CRITICAL tier)
2. Operator ignores warning
3. Agent causes incident
4. Post-mortem: "We had a warning but didn't act"
```

**Detection**:
- Track acknowledgment rate on ML warnings
- Audit cases where high-risk warnings were ignored
- Monitor time-to-acknowledge for critical alerts

**Existing Control**:
- Warning system requires explicit acknowledgment
- Warnings persist until addressed

**Mitigation Enhancement**:
- Escalation ladder: unacknowledged warnings auto-escalate
- Dashboard shows warning response times
- Performance metrics include warning response

**Residual Risk**: MEDIUM — Requires organizational discipline.

---

### 5.3. HM-03: Misinterpretation of Explanation

**What**: Operator misunderstands feature contribution explanation.

**Scenario**:
```
Explanation: "denial_rate_24h (+0.08)"
Operator interprets: "Agent had 8% denial rate"
Actual meaning: "Denial rate contributed +8 percentage points to risk"
```

**Detection**:
- User feedback on explanation clarity
- Comprehension testing during training
- A/B testing of explanation formats

**Existing Control**:
- Explanation includes human-readable interpretation field
- Feature contributions are additive (intuitive)

**Mitigation Enhancement**:
- Standardize explanation format with examples
- Tooltip explanations in dashboard
- User training on reading explanations

**Residual Risk**: MEDIUM — Explanations are inherently complex.

---

## 6. Adversarial Attack Risks

### 6.1. AA-01: Feature Manipulation

**What**: Adversary crafts behavior to achieve desired risk score.

**Attack**:
```
1. Adversary knows model features
2. Adversary maintains low denial rate by avoiding detected attacks
3. Adversary executes undetected attacks (not in features)
4. Risk score stays low despite malicious activity
```

**Detection**:
- Monitor for novel attack patterns not in features
- Periodic feature relevance audit
- Red team exercises

**Existing Control**:
- Governance decisions are ACM-based, not risk-based
- ML cannot override DENY decisions
- Deterministic rules still catch known bad behavior

**Mitigation Enhancement**:
- Anomaly detection for out-of-distribution behavior
- Human review for high-impact actions regardless of score
- Feature coverage audit (what's NOT measured?)

**Residual Risk**: HIGH — Classic adversarial ML problem.

---

### 6.2. AA-02: Gradual Norm Shifting

**What**: Adversary slowly shifts baseline to make attacks appear normal.

**Attack**:
```
Week 1: Normal behavior (baseline established)
Week 2: Slightly elevated denial rate (new normal)
Week 3: More elevated (drift not detected)
Week 4: Attack (appears within "normal" variance)
```

**Detection**:
- Long-term trend analysis
- Multiple time windows (24h, 7d, 30d)
- Absolute thresholds in addition to relative

**Existing Control**:
- Drift monitoring in model governance
- Multiple window sizes for signals

**Mitigation Enhancement**:
- Cumulative sum (CUSUM) for trend detection
- Baseline anchoring to historical "clean" period
- Drift alerts trigger human review

**Residual Risk**: MEDIUM — Slow drift is hard to detect.

---

### 6.3. AA-03: Mimicry Attack

**What**: Malicious agent mimics behavior of trusted agents.

**Attack**:
```
1. Attacker observes behavior of trusted agents
2. Attacker replicates pattern (same tools, same rate)
3. Risk model sees "trusted" pattern
4. Attacker executes malicious action
```

**Detection**:
- Identity verification (is agent who they claim?)
- Behavioral consistency over time
- Cross-agent correlation analysis

**Existing Control**:
- ACM verifies agent GID for every decision
- Scope boundaries limit what any agent can do
- ATLAS domain enforcement

**Residual Risk**: MEDIUM — Mimicry attacks surface identity, not behavior.

---

### 6.4. AA-04: Model Extraction

**What**: Adversary reverse-engineers model by querying.

**Attack**:
```
1. Attacker submits many queries with known inputs
2. Attacker observes risk score outputs
3. Attacker reconstructs model
4. Attacker uses model to find blind spots
```

**Detection**:
- Query rate limiting
- Anomaly detection on query patterns
- Monitor for systematic probing

**Existing Control**:
- Risk scores are annotations, not exposed as API
- Scores visible only in dashboard (authenticated)

**Mitigation Enhancement**:
- Rate limit dashboard queries
- Add noise to scores (differential privacy)
- Alert on unusual query patterns

**Residual Risk**: LOW — Scores are internal, not publicly queryable.

---

## 7. Operational Failure Risks

### 7.1. OF-01: ML Service Outage

**What**: ML inference service becomes unavailable.

**Impact**:
- No risk scores available
- Dashboard shows "no signal"
- Operators lose risk context

**Detection**:
- Health check endpoint
- Inference latency monitoring
- Automatic failover detection

**Existing Control**:
- Governance proceeds without ML (MLFailurePolicy)
- Explicit "ML_UNAVAILABLE" failure mode
- Non-blocking integration

**Residual Risk**: LOW — Governance is independent of ML.

---

### 7.2. OF-02: Inference Latency Spike

**What**: ML inference becomes slow, blocking dashboard.

**Impact**:
- Dashboard timeouts
- Stale risk scores displayed
- User frustration

**Detection**:
- P99 latency monitoring
- Timeout tracking
- Cache hit rate monitoring

**Existing Control**:
- MLFailurePolicy.on_ml_timeout() returns graceful failure
- Async inference (non-blocking)

**Mitigation Enhancement**:
- Score caching with TTL
- Precomputed scores for known agents
- Lazy loading in dashboard

**Residual Risk**: LOW — Standard operational practice.

---

### 7.3. OF-03: Resource Exhaustion

**What**: ML system consumes excessive memory/CPU.

**Impact**:
- System degradation
- Potential outage
- Cascading failures

**Detection**:
- Resource monitoring (CPU, memory)
- Container limits enforcement
- Alert thresholds

**Existing Control**:
- Containerized deployment with resource limits
- Horizontal scaling capability

**Residual Risk**: LOW — Standard DevOps practice.

---

## 8. Drift & Decay Risks

### 8.1. DD-01: Feature Drift

**What**: Feature distributions shift from training data.

**Cause**:
- New agent behaviors emerge
- System changes affect metrics
- External factors change patterns

**Detection**:
- KL divergence monitoring (from Model Architecture)
- Feature distribution dashboards
- Automated drift alerts

**Existing Control**:
- DriftMonitor class for feature drift
- Weekly calibration checks

**Residual Risk**: MEDIUM — Drift is inevitable; detection is key.

---

### 8.2. DD-02: Concept Drift

**What**: Relationship between features and risk changes.

**Cause**:
- New attack vectors
- Changed governance policies
- Evolved adversary behavior

**Detection**:
- Calibration decay monitoring (ECE over time)
- Prediction-outcome correlation tracking
- Periodic backtesting on recent data

**Existing Control**:
- Quarterly full retraining schedule
- ECE < 0.05 threshold

**Mitigation Enhancement**:
- Continuous evaluation on holdout
- Trigger retraining on calibration breach
- Shadow model comparison

**Residual Risk**: MEDIUM — Concept drift is harder to detect than feature drift.

---

### 8.3. DD-03: Label Drift

**What**: Definition of "risky" changes over time.

**Cause**:
- New incident types
- Changing organizational risk appetite
- Regulatory changes

**Detection**:
- Label distribution monitoring
- Labeler agreement tracking
- Periodic label definition review

**Existing Control**:
- Documented label definitions in Model Card
- Multi-reviewer requirement

**Mitigation Enhancement**:
- Annual label definition review
- Governance sign-off on label changes
- Version labels with model

**Residual Risk**: MEDIUM — Requires organizational process.

---

## 9. Risk Mitigation Summary

| Risk ID | Risk | Severity | Existing Control | Additional Mitigation | Residual |
|---------|------|----------|------------------|----------------------|----------|
| MF-01 | Feature Bug | HIGH | Unit tests, bounds | - | LOW |
| MF-02 | Model Load Fail | HIGH | Hash verification | - | LOW |
| MF-03 | Numerical Issues | MEDIUM | EBM stability | - | LOW |
| MF-04 | Monotonicity | HIGH | EBM constraints | - | LOW |
| DI-01 | Log Tampering | CRITICAL | Append-only, hash | Cross-ref validation | MEDIUM |
| DI-02 | Clock Skew | HIGH | Server timestamps | - | LOW |
| DI-03 | Event Flooding | HIGH | Absolute counts | Volume anomaly signal | MEDIUM |
| DI-04 | Label Poisoning | CRITICAL | Multi-reviewer | Holdout validation | MEDIUM |
| HM-01 | Over-Trust | HIGH | Contract separation | Dashboard warnings | HIGH |
| HM-02 | Under-Trust | MEDIUM | Ack requirement | Escalation ladder | MEDIUM |
| HM-03 | Misinterpretation | MEDIUM | Explanations | User training | MEDIUM |
| AA-01 | Feature Manip | CRITICAL | ACM authority | OOD detection | HIGH |
| AA-02 | Norm Shifting | HIGH | Multi-window | CUSUM detection | MEDIUM |
| AA-03 | Mimicry | HIGH | GID verification | Behavioral analysis | MEDIUM |
| AA-04 | Model Extract | MEDIUM | Internal only | Query rate limits | LOW |
| OF-01 | Service Outage | MEDIUM | Non-blocking | - | LOW |
| OF-02 | Latency Spike | MEDIUM | Timeout handling | Caching | LOW |
| OF-03 | Resource Exhaust | MEDIUM | Container limits | - | LOW |
| DD-01 | Feature Drift | MEDIUM | KL monitoring | - | MEDIUM |
| DD-02 | Concept Drift | HIGH | Quarterly retrain | Continuous eval | MEDIUM |
| DD-03 | Label Drift | MEDIUM | Multi-reviewer | Annual review | MEDIUM |

---

## 10. Control Mapping to ChainBridge Components

| Control | ChainBridge Component | Status |
|---------|----------------------|--------|
| Append-only logs | `core/governance/event_sink.py` | ✅ Exists |
| Hash verification | `core/governance/governance_fingerprint.py` | ✅ Exists |
| Server timestamps | `core/governance/events.py` (`_utc_now`) | ✅ Exists |
| ACM authority | `core/governance/acm_evaluator.py` | ✅ Exists |
| GID verification | `core/governance/acm_loader.py` | ✅ Exists |
| Non-blocking ML | `RISK_GOVERNANCE_CONTRACT.md` | 📄 Specified |
| Boot checks | `core/governance/boot_checks.py` | ✅ Exists |
| Drift monitoring | `docs/ml/AT02_DRIFT_MONITORING.md` | 📄 Specified |
| Retention policy | `docs/governance/RETENTION_POLICY.md` | ✅ Exists |

---

## 11. Acceptance Criteria

- [ ] All model failure modes enumerated with detection methods
- [ ] All data integrity risks traced to existing controls
- [ ] All human misuse risks have mitigation strategies
- [ ] All adversarial attacks have detection mechanisms
- [ ] All operational failures have graceful degradation
- [ ] All drift risks have monitoring approaches
- [ ] Risk severity rated consistently
- [ ] Residual risk assessed after controls

---

## 12. References

- [core/governance/events.py](../../core/governance/events.py) — Event schema
- [core/governance/acm_evaluator.py](../../core/governance/acm_evaluator.py) — ACM authority
- [RISK_SIGNAL_TAXONOMY.md](./RISK_SIGNAL_TAXONOMY.md) — Signal definitions
- [RISK_MODEL_ARCHITECTURE.md](./RISK_MODEL_ARCHITECTURE.md) — Model design
- [RISK_GOVERNANCE_CONTRACT.md](./RISK_GOVERNANCE_CONTRACT.md) — Integration rules
