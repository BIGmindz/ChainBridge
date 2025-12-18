# Risk Governance Integration Contract

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-SIGNALS-01
> **Status**: SPEC (Design Only — No Code Changes)
> **Created**: 2025-12-17

---

## 1. BLUF

This contract specifies **exactly how governance may consume ML risk signals**. The contract is asymmetric:

- **Governance owns all authority** — ML has zero
- **ML may annotate** — Governance may ignore
- **ML may warn** — Governance decides response
- **ML may prioritize** — Governance executes order
- **ML may NEVER allow, deny, or execute**

This is non-negotiable. Violation of this contract is a governance failure.

---

## 2. Fundamental Principles

### 2.1. The Authority Axiom

```
GOVERNANCE_AUTHORITY := ABSOLUTE
ML_AUTHORITY := ZERO

∀ decision d:
    d.authority ∈ {ACM, DRCP, Diggi, ALEX, Human}
    d.authority ∉ {ML, Risk_Model, Signal_Layer}
```

### 2.2. The Information Asymmetry

ML sees:
- Historical events (past)
- Statistical patterns (aggregate)
- Probabilistic estimates (uncertain)

Governance sees:
- Current intent (present)
- Deterministic rules (exact)
- Binary decisions (certain)

ML cannot know what governance knows. ML provides context, not judgment.

### 2.3. The Degradation Guarantee

```
IF ml_signal == UNAVAILABLE:
    governance.proceed_normally()  # Zero behavior change

IF ml_signal == HIGH_RISK:
    governance.proceed_normally()  # ML cannot block

IF ml_signal == LOW_RISK:
    governance.proceed_normally()  # ML cannot approve
```

---

## 3. Permitted ML Actions

### 3.1. ANNOTATE

ML may attach risk annotations to governance artifacts.

**Definition**: Add metadata that does not affect decision logic.

```python
# PERMITTED: Annotate envelope with risk score
def annotate_envelope(
    envelope: GatewayDecisionEnvelope,
    risk_score: RiskScore,
) -> GatewayDecisionEnvelope:
    """
    Attach risk annotation to envelope.

    This does NOT modify the decision.
    The envelope.decision field is UNCHANGED.
    """
    envelope.annotations["ml_risk_score"] = risk_score.value
    envelope.annotations["ml_risk_tier"] = risk_score.tier
    envelope.annotations["ml_risk_explanation"] = risk_score.explanation
    return envelope
```

**Constraints**:
- Annotations go in designated `annotations` field
- Annotations MUST NOT modify `decision`, `reason`, or `next_hop`
- Annotations are optional and may be stripped before execution
- Annotation failure MUST NOT block governance

### 3.2. WARN

ML may emit warnings for human attention.

**Definition**: Create alerts that require human acknowledgment.

```python
# PERMITTED: Emit warning for high-risk agent
def emit_risk_warning(
    agent_gid: str,
    risk_score: float,
    threshold: float = 0.70,
) -> None:
    """
    Emit warning if risk score exceeds threshold.

    Warning goes to monitoring system, NOT to governance.
    Governance continues regardless of warning.
    """
    if risk_score > threshold:
        alert_system.emit(
            alert_type="ML_RISK_WARNING",
            severity="HIGH",
            agent_gid=agent_gid,
            risk_score=risk_score,
            message=f"Agent {agent_gid} risk score {risk_score:.2f} exceeds threshold",
            requires_ack=True,
        )
```

**Constraints**:
- Warnings route to monitoring/alerting, not governance
- Warnings do not pause, block, or modify execution
- Warning fatigue must be managed (thresholds, dedup)
- Human must explicitly act on warning (no auto-response)

### 3.3. PRIORITIZE

ML may suggest ordering for human review queues.

**Definition**: Rank items for human attention, without changing which items are reviewed.

```python
# PERMITTED: Prioritize review queue by risk
def prioritize_review_queue(
    pending_reviews: list[ReviewItem],
    risk_scores: dict[str, float],
) -> list[ReviewItem]:
    """
    Sort review queue by risk score (highest first).

    Does NOT add or remove items from queue.
    Does NOT auto-approve or auto-deny anything.
    """
    return sorted(
        pending_reviews,
        key=lambda item: risk_scores.get(item.agent_gid, 0.0),
        reverse=True,  # Highest risk first
    )
```

**Constraints**:
- Prioritization affects order only, not inclusion
- All items still require human review
- Prioritization is advisory (human may re-sort)
- Must not create "never reviewed" backlog tail

### 3.4. ENRICH

ML may add context to decision records for audit.

**Definition**: Append explanatory data to audit trails.

```python
# PERMITTED: Enrich audit record with ML context
def enrich_audit_record(
    audit_record: dict,
    risk_context: RiskContext,
) -> dict:
    """
    Add ML context to audit record.

    This is for post-hoc analysis, not real-time decisions.
    """
    audit_record["ml_context"] = {
        "risk_score_at_time": risk_context.score,
        "risk_tier_at_time": risk_context.tier,
        "feature_values_at_time": risk_context.features,
        "model_version": risk_context.model_version,
        "explanation": risk_context.explanation,
    }
    return audit_record
```

**Constraints**:
- Enrichment is append-only (no modification of original)
- Enrichment timestamp must be recorded
- Enrichment must be clearly labeled as ML-derived
- Audit record validity independent of enrichment

---

## 4. Forbidden ML Actions

### 4.1. ❌ ALLOW

ML may NEVER grant permission.

```python
# FORBIDDEN
def ml_allow_intent(intent: AgentIntent, risk_score: float) -> bool:
    if risk_score < 0.10:
        return True  # ❌ ML CANNOT ALLOW
    return False
```

**Why forbidden**: Even low-risk does not mean permitted. ACM is the sole authority.

### 4.2. ❌ DENY

ML may NEVER reject a request.

```python
# FORBIDDEN
def ml_deny_intent(intent: AgentIntent, risk_score: float) -> bool:
    if risk_score > 0.90:
        return True  # ❌ ML CANNOT DENY
    return False
```

**Why forbidden**: High-risk does not mean impermissible. ACM permits what ACM permits.

### 4.3. ❌ EXECUTE

ML may NEVER trigger actions.

```python
# FORBIDDEN
def ml_auto_revoke(agent_gid: str, risk_score: float) -> None:
    if risk_score > 0.95:
        revoke_agent_privileges(agent_gid)  # ❌ ML CANNOT EXECUTE
```

**Why forbidden**: Execution requires governance authority. ML has none.

### 4.4. ❌ ESCALATE (Automatically)

ML may NEVER auto-escalate to humans.

```python
# FORBIDDEN
def ml_auto_escalate(intent: AgentIntent, risk_score: float) -> None:
    if risk_score > 0.80:
        force_human_review(intent)  # ❌ ML CANNOT FORCE ESCALATION
```

**Why forbidden**: Escalation is a governance decision (DRCP). ML may warn, not escalate.

### 4.5. ❌ MODIFY DECISION

ML may NEVER change a governance decision.

```python
# FORBIDDEN
def ml_modify_decision(envelope: GatewayDecisionEnvelope, risk_score: float) -> None:
    if risk_score > 0.90 and envelope.decision == "ALLOW":
        envelope.decision = "DENY"  # ❌ ML CANNOT MODIFY DECISION
```

**Why forbidden**: Decisions are governance outputs. ML is read-only.

---

## 5. Integration Points

### 5.1. Pre-Evaluation Context (ANNOTATE)

```
┌─────────────────────────────────────────────────────────────┐
│                     PRE-EVALUATION FLOW                     │
│                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Intent  │───▶│ Risk Signal  │───▶│    ACM       │       │
│  │ Arrives │    │   Lookup     │    │  Evaluator   │       │
│  └─────────┘    └──────────────┘    └──────────────┘       │
│                        │                    │               │
│                        │                    │               │
│                        ▼                    ▼               │
│               ┌──────────────┐    ┌──────────────┐         │
│               │ risk_score   │    │  ALLOW/DENY  │         │
│               │ (annotation) │    │ (decision)   │         │
│               └──────────────┘    └──────────────┘         │
│                        │                    │               │
│                        │                    │               │
│                        └────────┬───────────┘               │
│                                 │                           │
│                                 ▼                           │
│                        ┌──────────────┐                     │
│                        │   Envelope   │                     │
│                        │  (decision + │                     │
│                        │  annotations)│                     │
│                        └──────────────┘                     │
│                                                             │
│  NOTE: Risk score is IN the envelope but does NOT          │
│        influence the decision field.                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2. Post-Denial Enrichment (ENRICH)

```
┌─────────────────────────────────────────────────────────────┐
│                   POST-DENIAL FLOW                          │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   DENY      │───▶│    DRCP      │───▶│  Audit Log   │   │
│  │  Decision   │    │  Processing  │    │   Write      │   │
│  └─────────────┘    └──────────────┘    └──────────────┘   │
│                                                │            │
│                                                │            │
│                                                ▼            │
│                                       ┌──────────────┐      │
│                                       │ ML Enricher  │      │
│                                       │ (async, non- │      │
│                                       │  blocking)   │      │
│                                       └──────────────┘      │
│                                                │            │
│                                                ▼            │
│                                       ┌──────────────┐      │
│                                       │  Enriched    │      │
│                                       │  Audit Log   │      │
│                                       └──────────────┘      │
│                                                             │
│  NOTE: Enrichment happens AFTER decision is final.         │
│        Cannot change outcome.                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.3. Dashboard Display (WARN + PRIORITIZE)

```
┌─────────────────────────────────────────────────────────────┐
│                   DASHBOARD FLOW                            │
│                                                             │
│  ┌─────────────┐                                            │
│  │ Risk Score  │                                            │
│  │  Compute    │                                            │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ├────────────────┬────────────────┐                 │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Risk Badge  │  │ Alert Panel │  │ Review Queue│         │
│  │ (visual)    │  │ (warnings)  │  │ (prioritized)│        │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                 │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │              HUMAN OPERATOR                      │       │
│  │  (sees risk context, makes governance decision) │       │
│  └─────────────────────────────────────────────────┘       │
│                                                             │
│  NOTE: Human sees ML context. Human decides.                │
│        ML cannot constrain human options.                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Data Flow Contracts

### 6.1. Input Contract (Governance → ML)

ML reads governance events. Governance writes governance events.

```python
@dataclass(frozen=True)
class GovernanceEventFeed:
    """
    Read-only feed of governance events for ML consumption.

    ML CANNOT write to this feed.
    ML CANNOT delete from this feed.
    ML CANNOT modify events in this feed.
    """

    def read_events(
        self,
        start_time: datetime,
        end_time: datetime,
        event_types: list[str] | None = None,
    ) -> Iterator[GovernanceEvent]:
        """Read events in time range."""
        ...

    def read_agent_events(
        self,
        agent_gid: str,
        window_hours: int = 24,
    ) -> list[GovernanceEvent]:
        """Read events for specific agent."""
        ...

    # NO write methods
    # NO delete methods
    # NO modify methods
```

### 6.2. Output Contract (ML → Consumers)

ML writes to annotation channels only.

```python
@dataclass
class RiskAnnotationChannel:
    """
    Write-only channel for ML risk annotations.

    Consumers (dashboard, audit, alerts) read from this channel.
    Governance DOES NOT read from this channel for decisions.
    """

    def publish_score(
        self,
        agent_gid: str,
        score: RiskScore,
    ) -> None:
        """Publish risk score for agent."""
        ...

    def publish_warning(
        self,
        warning: RiskWarning,
    ) -> None:
        """Publish risk warning."""
        ...

    # Consumers decide what to do with annotations
    # ML cannot control consumer behavior
```

---

## 7. Failure Handling

### 7.1. ML System Failure

```python
class MLFailurePolicy:
    """
    Policy for ML system failures.

    Core principle: Governance continues. ML fails silent.
    """

    @staticmethod
    def on_ml_unavailable() -> RiskScore:
        """Return when ML system is down."""
        return RiskScore(
            value=None,
            tier="UNKNOWN",
            confidence=0.0,
            explanation="ML system unavailable - no risk signal",
            failure_mode="ML_UNAVAILABLE",
        )

    @staticmethod
    def on_ml_timeout() -> RiskScore:
        """Return when ML inference times out."""
        return RiskScore(
            value=None,
            tier="UNKNOWN",
            confidence=0.0,
            explanation="ML inference timeout - no risk signal",
            failure_mode="ML_TIMEOUT",
        )

    @staticmethod
    def on_ml_error(error: Exception) -> RiskScore:
        """Return when ML throws error."""
        return RiskScore(
            value=None,
            tier="UNKNOWN",
            confidence=0.0,
            explanation=f"ML error - no risk signal: {type(error).__name__}",
            failure_mode="ML_ERROR",
        )
```

### 7.2. Governance Behavior on ML Failure

```python
def evaluate_intent_with_ml_context(
    intent: AgentIntent,
    acm_evaluator: ACMEvaluator,
    ml_scorer: RiskScorer | None,
) -> EvaluationResult:
    """
    Evaluate intent with optional ML context.

    ML failure does NOT affect governance decision.
    """
    # Step 1: Get ML context (optional, non-blocking)
    ml_context = None
    if ml_scorer is not None:
        try:
            ml_context = ml_scorer.score(intent.agent_gid)
        except Exception as e:
            ml_context = MLFailurePolicy.on_ml_error(e)
            logger.warning("ML scoring failed, continuing without: %s", e)

    # Step 2: Evaluate intent (ALWAYS happens, regardless of ML)
    result = acm_evaluator.evaluate(intent)

    # Step 3: Annotate result with ML context (if available)
    if ml_context is not None:
        result.annotations["ml_risk"] = ml_context.to_dict()

    return result
```

---

## 8. Audit Requirements

### 8.1. ML Decision Separation Audit

Every audit record must show:

1. **Governance decision** — ACM output (ALLOW/DENY)
2. **ML annotation** — Risk score (if available)
3. **Clear separation** — Decision did NOT depend on annotation

```json
{
  "event_id": "gov-abc123def456",
  "timestamp": "2025-12-17T15:30:00Z",

  "governance_decision": {
    "decision": "ALLOW",
    "reason_code": null,
    "evaluated_by": "ACM_EVALUATOR",
    "acm_version": "2.3.1"
  },

  "ml_annotation": {
    "risk_score": 0.23,
    "risk_tier": "MEDIUM",
    "model_version": "ebm-v1.0.0",
    "note": "ANNOTATION ONLY - DID NOT INFLUENCE DECISION"
  },

  "audit_assertion": "Governance decision independent of ML annotation"
}
```

### 8.2. Regulator Explanation

When asked "Why was this allowed/denied?", the answer is ALWAYS:

> "The decision was made by the Access Control Matrix (ACM) based on the agent's permissions and the requested action. The ML risk score was recorded for monitoring purposes but did not influence the decision."

NEVER:

> ~~"The ML model determined the risk was acceptable."~~

---

## 9. Testing Requirements

### 9.1. Independence Test

```python
def test_governance_independent_of_ml():
    """
    Verify governance decisions are identical with/without ML.
    """
    intents = generate_test_intents(n=1000)

    # Evaluate without ML
    results_without_ml = [
        acm_evaluator.evaluate(intent)
        for intent in intents
    ]

    # Evaluate with ML
    results_with_ml = [
        evaluate_with_ml_context(intent, acm_evaluator, ml_scorer)
        for intent in intents
    ]

    # Decisions MUST be identical
    for r1, r2 in zip(results_without_ml, results_with_ml):
        assert r1.decision == r2.decision
        assert r1.reason_code == r2.reason_code
```

### 9.2. Degradation Test

```python
def test_governance_survives_ml_failure():
    """
    Verify governance works when ML fails.
    """
    # Simulate ML failures
    failing_scorer = MockMLScorer(always_fail=True)

    intents = generate_test_intents(n=100)

    # Should NOT raise, should NOT block
    for intent in intents:
        result = evaluate_with_ml_context(
            intent,
            acm_evaluator,
            failing_scorer
        )
        assert result.decision in ["ALLOW", "DENY"]
        assert "ml_risk" in result.annotations
        assert result.annotations["ml_risk"]["failure_mode"] == "ML_ERROR"
```

---

## 10. Acceptance Criteria

- [ ] ML cannot ALLOW — verified by code review and test
- [ ] ML cannot DENY — verified by code review and test
- [ ] ML cannot EXECUTE — verified by code review and test
- [ ] ML can ANNOTATE — integration point specified
- [ ] ML can WARN — alert system integration specified
- [ ] ML can PRIORITIZE — queue ordering specified
- [ ] ML failure does not block governance — degradation test passes
- [ ] Audit records show decision/annotation separation
- [ ] Regulator explanation script defined

---

## 11. References

- [core/governance/acm_evaluator.py](../../core/governance/acm_evaluator.py) — ACM authority
- [core/governance/drcp.py](../../core/governance/drcp.py) — Denial routing
- [core/governance/telemetry.py](../../core/governance/telemetry.py) — Event emission
- [RISK_SIGNAL_TAXONOMY.md](./RISK_SIGNAL_TAXONOMY.md) — Signal definitions
- [RISK_MODEL_ARCHITECTURE.md](./RISK_MODEL_ARCHITECTURE.md) — Model design
