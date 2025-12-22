# Trust Risk Failure Mode Analysis

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-TRUST-01
> **Status**: SPEC (Design Only — No Code)
> **Created**: 2025-12-17

---

## 1. BLUF

This document enumerates failure modes and abuse vectors for the Trust Risk Index (TRI). Each failure mode includes:

- **What can go wrong**
- **How it manifests**
- **Detection mechanism**
- **Mitigation strategy**
- **Residual risk**

The goal: Anticipate failures before they harm customers, auditors, or operations.

---

## 2. Failure Mode Categories

| Category | Description | Impact |
|----------|-------------|--------|
| **Data Sparsity** | Insufficient events for reliable scoring | Unreliable scores |
| **Adversarial Gaming** | Bad actors manipulate inputs | Misleading scores |
| **Human Over-Trust** | People treat scores as guarantees | False assurance |
| **Misinterpretation** | Users misunderstand score meaning | Bad decisions |
| **Commercial Misuse** | Sales/marketing overclaims | Regulatory risk |
| **Technical Failure** | Computation errors | Missing context |

---

## 3. Data Sparsity Failures

### DS-01: Low Event Volume

**What**: Insufficient governance events to compute reliable scores.

**Manifestation**:
- TRI computed from < 100 events
- Wide confidence bands
- Scores fluctuate dramatically

**Detection**:
```python
IF event_count < min_events_for_confidence:
    confidence = LOW
    add_warning("Insufficient data for reliable scoring")
```

**Mitigation**:
- Confidence bands widen with sparse data
- Explicit "UNKNOWN" tier when data insufficient
- Display event count to users

**Residual Risk**: LOW — Confidence system handles this.

---

### DS-02: Uneven Event Distribution

**What**: Events clustered in time, leaving gaps.

**Manifestation**:
- Burst of events on Monday, none rest of week
- TRI represents one moment, not week

**Detection**:
- Track event timestamps
- Compute event density variance
- Alert on gaps > 24 hours

**Mitigation**:
- Use decay functions (exponential)
- Report "observation quality" metric
- Warn when distribution is uneven

**Residual Risk**: MEDIUM — Decay helps but doesn't fully solve.

---

### DS-03: Missing Event Types

**What**: Some event types never occur, leaving blind spots.

**Manifestation**:
- No `SCOPE_VIOLATION` events (system appears clean)
- But scope checking might be disabled

**Detection**:
- Track which event types are present
- Alert on expected event types missing
- Cross-reference with feature null rates

**Mitigation**:
- Null handling returns `null`, not 0
- "Data completeness" affects confidence
- Report which features are computable

**Residual Risk**: MEDIUM — Cannot force events that don't happen.

---

## 4. Adversarial Gaming Failures

### AG-01: Event Dilution Attack

**What**: Attacker floods benign events to dilute bad signals.

**Attack Vector**:
```
1. Malicious agent causes 10 denials
2. Attacker generates 990 successful requests
3. Denial rate = 10/1000 = 1% (appears low)
4. TRI drops despite real issues
```

**Detection**:
- Track event volume anomalies
- Compare rates across time windows
- Alert on sudden volume spikes

**Mitigation**:
- Use absolute counts alongside rates
- Multiple time windows (24h, 7d, 30d)
- Rate limiting on event generation

**Residual Risk**: MEDIUM — Dilution is a real attack vector.

---

### AG-02: Stale Evidence Attack

**What**: Attacker stops generating events to freeze a "good" score.

**Attack Vector**:
```
1. System has good TRI (0.10)
2. Attacker disables telemetry
3. No new events generated
4. Old "good" TRI persists
5. System actually compromised
```

**Detection**:
- Track time since last event
- Freshness violation flag
- Alert when event stream stops

**Mitigation**:
- Trust weight penalizes stale data
- `sd_freshness_violation` signal
- Require recent events for valid TRI

**Residual Risk**: LOW — Freshness system handles this.

---

### AG-03: Selective Event Suppression

**What**: Attacker suppresses only negative events.

**Attack Vector**:
```
1. Compromise event sink
2. Filter out DECISION_DENIED events
3. Only DECISION_ALLOWED events recorded
4. Denial rate appears 0%
```

**Detection**:
- Event integrity checks
- Cross-reference with decision logs
- Hash chain on event stream

**Mitigation**:
- Append-only event logs
- Event sink integrity verification
- Multiple telemetry sources

**Residual Risk**: MEDIUM — Requires event sink compromise.

---

### AG-04: Feature Boundary Gaming

**What**: Attacker stays just below signal thresholds.

**Attack Vector**:
```
1. Attacker knows: denial_rate > 0.10 = MODERATE tier
2. Attacker maintains 0.09 denial rate
3. TRI shows LOW tier
4. Attacker operates in "safe zone"
```

**Detection**:
- Trend analysis (approaching boundaries)
- Distribution anomaly detection
- Compare to historical baseline

**Mitigation**:
- Smooth thresholds (no hard cutoffs in score)
- Multiple features reduce single-feature gaming
- Trust weights add unpredictability

**Residual Risk**: MEDIUM — Boundary gaming is always possible.

---

## 5. Human Over-Trust Failures

### HT-01: Score as Safety Guarantee

**What**: Users believe low TRI means system is "safe".

**Manifestation**:
- "Our TRI is 0.08, so we're secure"
- Skip manual review due to low score
- Ignore other risk indicators

**Detection**:
- Survey user understanding
- Track review skip rates by TRI
- Audit decisions post-incident

**Mitigation**:
- Never label any tier "safe"
- Require "advisory only" disclaimer
- Training on TRI limitations

**Residual Risk**: HIGH — Human psychology is hard to control.

---

### HT-02: Trend Complacency

**What**: Users see improving trend and relax vigilance.

**Manifestation**:
- TRI drops 0.40 → 0.25 → 0.15
- Users assume system is "getting better"
- Reduce monitoring/review
- Incident occurs from undetected vector

**Detection**:
- Track monitoring behavior vs TRI
- Survey vigilance levels
- Incident correlation analysis

**Mitigation**:
- Trend display with caveats
- "Lower TRI ≠ lower vigilance" messaging
- Maintain review frequency regardless

**Residual Risk**: HIGH — Success breeds complacency.

---

### HT-03: False Precision Belief

**What**: Users treat decimal scores as exact measurements.

**Manifestation**:
- "Our TRI is 0.23, not 0.24"
- Debates over 0.01 differences
- Precision implies accuracy

**Detection**:
- Survey user interpretation
- Track decisions based on small differences
- Communication audit

**Mitigation**:
- Display confidence bands prominently
- Round to meaningful precision (0.XX)
- Use tiers, not just numbers

**Residual Risk**: MEDIUM — Communication helps.

---

## 6. Misinterpretation Failures

### MI-01: Causal Confusion

**What**: Users interpret correlation as causation.

**Manifestation**:
- "High TRI caused the incident"
- "Lower TRI will prevent incidents"
- TRI is diagnostic, not causal

**Detection**:
- Language audit in communications
- Survey causal beliefs
- Track claims made about TRI

**Mitigation**:
- Clear documentation: TRI is descriptive
- "Correlation, not causation" messaging
- Avoid causal language in reports

**Residual Risk**: MEDIUM — Requires ongoing education.

---

### MI-02: Reverse Causation

**What**: Users think they can lower TRI by hiding problems.

**Manifestation**:
- Disable logging to reduce denials
- Avoid testing to reduce failures
- "If we don't measure it, TRI improves"

**Detection**:
- Track event volume changes
- Alert on logging gaps
- Cross-reference with operations

**Mitigation**:
- Freshness violation penalizes silence
- Event volume included in confidence
- Audit for logging completeness

**Residual Risk**: MEDIUM — Goodhart's Law always applies.

---

### MI-03: Context Loss

**What**: TRI presented without context leads to wrong conclusions.

**Manifestation**:
- "Competitor TRI is 0.15, ours is 0.25"
- But different systems, different baselines
- Apples-to-oranges comparison

**Detection**:
- Track how TRI is shared externally
- Monitor comparative claims
- Audit marketing materials

**Mitigation**:
- Include context in all TRI displays
- Version and baseline information
- Warn against cross-system comparison

**Residual Risk**: MEDIUM — Context often gets stripped.

---

## 7. Commercial Misuse Failures

### CM-01: Sales Overclaim

**What**: Sales uses TRI to make unwarranted claims.

**Manifestation**:
- "Our TRI is 0.12, lowest in industry"
- "TRI guarantees operational stability"
- "Low TRI = SOC2 compliance"

**Detection**:
- Audit sales materials
- Track customer complaints
- Monitor claims made in RFPs

**Mitigation**:
- Approved language guidelines
- Review process for external claims
- Training on what TRI does NOT mean

**Residual Risk**: HIGH — Sales incentives conflict.

---

### CM-02: Procurement Misrepresentation

**What**: TRI presented as more than it is during procurement.

**Manifestation**:
- "Our ML system detects all threats"
- "TRI replaced our security team"
- "Real-time risk assessment"

**Detection**:
- Review RFP responses
- Track procurement conversations
- Customer expectation surveys

**Mitigation**:
- Standardized procurement response
- Clear limitations section
- Legal review of claims

**Residual Risk**: MEDIUM — Standardization helps.

---

### CM-03: Regulator Misunderstanding

**What**: Regulator interprets TRI as control, not signal.

**Manifestation**:
- Regulator expects TRI to prevent issues
- Audit finding: "TRI should have caught this"
- Liability for ML "failure"

**Detection**:
- Track regulatory communications
- Monitor audit findings
- Legal review of positioning

**Mitigation**:
- Clear regulator briefing document
- Governance contract in audit pack
- Pre-emptive regulator education

**Residual Risk**: HIGH — Regulatory environment is unpredictable.

---

## 8. Technical Failure Modes

### TF-01: Computation Error

**What**: Bug in TRI calculation produces wrong scores.

**Manifestation**:
- Scores outside [0, 1] range
- NaN or Inf values
- Sudden score jumps

**Detection**:
- Bounds checking on output
- NaN/Inf detection
- Anomaly detection on scores

**Mitigation**:
- Comprehensive unit tests
- Integration tests with known data
- Production monitoring

**Residual Risk**: LOW — Standard software QA.

---

### TF-02: Model Version Mismatch

**What**: Different components use different model versions.

**Manifestation**:
- Trust Center shows v1.0 score
- Audit bundle has v1.1 score
- Inconsistent reports

**Detection**:
- Version tracking in all outputs
- Cross-component version check
- Alert on version mismatches

**Mitigation**:
- Centralized model registry
- Version in every output
- Deployment synchronization

**Residual Risk**: LOW — Versioning solves this.

---

### TF-03: Time Zone Confusion

**What**: Timestamp handling causes window misalignment.

**Manifestation**:
- 24h window includes wrong events
- Scores differ by timezone
- Inconsistent results globally

**Detection**:
- UTC enforcement checks
- Cross-timezone validation
- Timestamp audit

**Mitigation**:
- All timestamps in UTC
- Timezone-aware libraries
- Unit tests for edge cases

**Residual Risk**: LOW — Standard practice.

---

## 9. Failure Mode Summary

| ID | Failure Mode | Severity | Detectability | Residual Risk |
|----|--------------|----------|---------------|---------------|
| DS-01 | Low Event Volume | LOW | HIGH | LOW |
| DS-02 | Uneven Distribution | MEDIUM | MEDIUM | MEDIUM |
| DS-03 | Missing Event Types | MEDIUM | MEDIUM | MEDIUM |
| AG-01 | Event Dilution | HIGH | MEDIUM | MEDIUM |
| AG-02 | Stale Evidence | HIGH | HIGH | LOW |
| AG-03 | Event Suppression | CRITICAL | LOW | MEDIUM |
| AG-04 | Boundary Gaming | MEDIUM | LOW | MEDIUM |
| HT-01 | Safety Guarantee | HIGH | LOW | HIGH |
| HT-02 | Trend Complacency | HIGH | LOW | HIGH |
| HT-03 | False Precision | MEDIUM | MEDIUM | MEDIUM |
| MI-01 | Causal Confusion | MEDIUM | LOW | MEDIUM |
| MI-02 | Reverse Causation | HIGH | MEDIUM | MEDIUM |
| MI-03 | Context Loss | MEDIUM | MEDIUM | MEDIUM |
| CM-01 | Sales Overclaim | HIGH | MEDIUM | HIGH |
| CM-02 | Procurement Misrep | HIGH | MEDIUM | MEDIUM |
| CM-03 | Regulator Misunderstand | CRITICAL | LOW | HIGH |
| TF-01 | Computation Error | MEDIUM | HIGH | LOW |
| TF-02 | Version Mismatch | LOW | HIGH | LOW |
| TF-03 | Time Zone Confusion | LOW | HIGH | LOW |

---

## 10. Highest-Priority Mitigations

Based on residual risk analysis:

| Priority | Failure Mode | Required Mitigation |
|----------|--------------|---------------------|
| 1 | HT-01 (Safety Guarantee) | Mandatory "advisory only" labeling |
| 2 | CM-01 (Sales Overclaim) | Approved language guidelines + review |
| 3 | CM-03 (Regulator) | Pre-emptive regulator education |
| 4 | HT-02 (Complacency) | "Lower ≠ safer" messaging |
| 5 | AG-01 (Dilution) | Absolute counts alongside rates |

---

## 11. Monitoring Requirements

### 11.1 Health Metrics

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Event count (24h) | < 100 | LOW_EVENT_VOLUME |
| Null feature rate | > 50% | HIGH_NULL_RATE |
| TRI change rate | > 0.2/hour | RAPID_SCORE_CHANGE |
| Computation latency | > 5s | SLOW_COMPUTATION |
| Error rate | > 1% | HIGH_ERROR_RATE |

### 11.2 Anomaly Detection

| Pattern | Detection Method | Response |
|---------|-----------------|----------|
| Volume spike | Z-score > 3 | Investigate |
| Score discontinuity | > 0.3 jump | Alert + review |
| Feature divergence | KL divergence > 0.1 | Review inputs |

---

## 12. Acceptance Criteria

- [x] All failure categories enumerated
- [x] Detection mechanisms specified
- [x] Mitigation strategies documented
- [x] Residual risks assessed
- [x] Priority ranking provided
- [x] Monitoring requirements defined

---

## 13. References

- [TRUST_RISK_MODEL.md](./TRUST_RISK_MODEL.md) — Score computation
- [TRUST_RISK_GOVERNANCE_CONTRACT.md](./TRUST_RISK_GOVERNANCE_CONTRACT.md) — Authority limits
- [RISK_FAILURE_MODES.md](./RISK_FAILURE_MODES.md) — General ML failures
