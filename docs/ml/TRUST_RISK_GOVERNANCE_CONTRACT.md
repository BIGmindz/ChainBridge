# Trust Risk Governance Contract

> **Author**: 🟣 MAGGIE (GID-10) — Machine Learning & Applied AI Lead
> **PAC**: PAC-MAGGIE-RISK-TRUST-01
> **Status**: SPEC (Design Only — No Code)
> **Created**: 2025-12-17

---

## 1. BLUF

This contract defines **exactly what Trust Risk Index (TRI) may and may not do**. The contract is asymmetric and non-negotiable:

- **Governance has absolute authority** — TRI has zero
- **TRI is advisory** — Governance is authoritative
- **TRI annotates** — Governance decides
- **TRI informs humans** — Governance enforces rules

Violation of this contract is a governance failure.

---

## 2. Fundamental Authority Model

### 2.1 Authority Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTHORITY LAYER                          │
│                                                             │
│   ACM Evaluator → DRCP → Diggi → ALEX Gateway              │
│                                                             │
│   DECISION AUTHORITY: ALLOW / DENY / ESCALATE              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (events flow down, read-only)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SIGNAL LAYER                             │
│                                                             │
│   Trust Risk Index (TRI)                                    │
│                                                             │
│   DECISION AUTHORITY: NONE                                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (annotations flow to consumers)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   CONSUMER LAYER                            │
│                                                             │
│   Trust Center │ Audit Bundles │ Sales │ Procurement        │
│                                                             │
│   ACTION AUTHORITY: HUMAN DECISION ONLY                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Authority Axiom

```
∀ action a:
    IF a.type ∈ {ALLOW, DENY, EXECUTE, BLOCK, ESCALATE}:
        a.authority ∈ {ACM, DRCP, Diggi, ALEX, Human}
        a.authority ∉ {TRI, ML, Risk_Model}
```

**Corollary**: TRI cannot make any action happen or not happen.

---

## 3. What TRI MAY Do

### 3.1 ✅ ANNOTATE — Trust Center

TRI may display risk signals on the Trust Center.

**Contract**:
```python
def annotate_trust_center(tri_output: TrustRiskIndex) -> TrustCenterAnnotation:
    """
    Add TRI to Trust Center display.

    Constraints:
    - Display only, no action triggers
    - Must include confidence level
    - Must include "advisory only" disclaimer
    - Must show last-computed timestamp
    """
    return TrustCenterAnnotation(
        risk_index=tri_output.value,
        risk_tier=tri_output.tier,
        confidence=tri_output.confidence,
        computed_at=tri_output.computed_at,
        disclaimer="Advisory risk signal. Does not affect governance decisions.",
    )
```

**Permitted Display**:
```
┌─────────────────────────────────────────┐
│        Trust Risk Index: 0.23           │
│        Tier: LOW                        │
│        Confidence: 85%                  │
│        As of: 2025-12-17 15:30 UTC      │
│                                         │
│  ⓘ Advisory only. Does not affect      │
│    governance decisions.                │
└─────────────────────────────────────────┘
```

---

### 3.2 ✅ ANNOTATE — Audit Bundles

TRI may be included in audit bundles as supplementary data.

**Contract**:
```python
def annotate_audit_bundle(
    bundle: AuditBundle,
    tri_output: TrustRiskIndex,
) -> AuditBundle:
    """
    Add TRI to audit bundle metadata.

    Constraints:
    - Goes in 'supplementary' section, not core
    - Clearly labeled as ML-derived
    - Does not affect bundle validity
    - Bundle remains valid if TRI is null
    """
    bundle.supplementary["trust_risk_index"] = {
        "value": tri_output.value,
        "tier": tri_output.tier,
        "computed_at": tri_output.computed_at,
        "model_version": tri_output.model_version,
        "note": "ML-derived advisory signal, not governance output",
    }
    return bundle
```

**Audit Bundle Structure**:
```yaml
audit_bundle:
  # Core (governance-authoritative)
  governance_events: [...]
  artifact_hashes: [...]
  fingerprint: {...}

  # Supplementary (advisory)
  supplementary:
    trust_risk_index:
      value: 0.23
      tier: "LOW"
      computed_at: "2025-12-17T15:30:00Z"
      model_version: "tri-v1.0.0"
      note: "ML-derived advisory signal, not governance output"
```

---

### 3.3 ✅ INFORM — Human Review

TRI may inform humans during review processes.

**Contract**:
```python
def inform_human_review(
    review_item: ReviewItem,
    tri_output: TrustRiskIndex,
) -> ReviewContext:
    """
    Provide TRI context to human reviewer.

    Constraints:
    - Human makes final decision
    - TRI cannot require any action
    - Human may ignore TRI entirely
    - Decision must be logged independently of TRI
    """
    return ReviewContext(
        item=review_item,
        risk_context={
            "trust_risk_index": tri_output.value,
            "risk_tier": tri_output.tier,
            "top_contributors": tri_output.top_contributors,
            "confidence": tri_output.confidence,
        },
        reviewer_instruction="Advisory context only. Your judgment prevails.",
    )
```

---

### 3.4 ✅ PRIORITIZE — Review Queues (Advisory)

TRI may suggest ordering for human review queues.

**Contract**:
```python
def suggest_review_order(
    pending_items: list[ReviewItem],
    tri_scores: dict[str, float],
) -> list[ReviewItem]:
    """
    Suggest ordering by risk score.

    Constraints:
    - Human may override order
    - All items still require review
    - Order is suggestion only
    - Must not create "never reviewed" tail
    """
    suggested = sorted(
        pending_items,
        key=lambda x: tri_scores.get(x.id, 0.0),
        reverse=True,  # Higher risk first
    )
    return suggested
```

---

### 3.5 ✅ SUPPORT — Procurement Questions

TRI may provide answers to procurement/RFP questions.

**Contract**:
```
Q: "What is your current operational risk level?"
A: "Our Trust Risk Index is currently 0.23 (LOW tier) with 85% confidence,
    based on governance telemetry from the last 7 days. This is an advisory
    metric derived from 1,247 governance events. It does not affect system
    behavior — all access control decisions are made by deterministic
    governance rules."
```

**Permitted Claims**:
- "Our TRI is X"
- "This indicates Y tier"
- "Based on Z events"
- "Advisory only"

**Forbidden Claims**:
- ~~"Our system is safe"~~
- ~~"Risk is guaranteed below X"~~
- ~~"TRI prevents incidents"~~

---

## 4. What TRI MAY NOT Do

### 4.1 ❌ GATE — Execution

TRI may NEVER block or permit execution.

```python
# ❌ FORBIDDEN
def tri_gate_execution(action: Action, tri_score: float) -> bool:
    if tri_score > 0.75:
        return False  # BLOCK — NOT ALLOWED
    return True
```

**Why Forbidden**: TRI is not a control. ACM is the control.

---

### 4.2 ❌ TRIGGER — Escalation

TRI may NEVER automatically escalate to humans.

```python
# ❌ FORBIDDEN
def tri_auto_escalate(agent_gid: str, tri_score: float) -> None:
    if tri_score > 0.50:
        force_human_review(agent_gid)  # NOT ALLOWED
```

**Why Forbidden**: Escalation is a DRCP decision. TRI cannot create governance load.

---

### 4.3 ❌ MODIFY — Decisions

TRI may NEVER change governance decisions.

```python
# ❌ FORBIDDEN
def tri_modify_decision(envelope: DecisionEnvelope, tri_score: float) -> None:
    if tri_score > 0.80 and envelope.decision == "ALLOW":
        envelope.decision = "DENY"  # NOT ALLOWED
```

**Why Forbidden**: Decisions are ACM outputs. TRI cannot override.

---

### 4.4 ❌ ALERT — Automated Response

TRI may NEVER trigger automated responses.

```python
# ❌ FORBIDDEN
def tri_auto_respond(tri_score: float) -> None:
    if tri_score > 0.90:
        revoke_all_permissions()  # NOT ALLOWED
        notify_security_team()    # NOT ALLOWED (automated)
        lock_system()             # NOT ALLOWED
```

**Why Forbidden**: Automated responses based on ML scores create attack surface.

---

### 4.5 ❌ LABEL — Safe/Unsafe

TRI may NEVER label anything as "safe" or "unsafe".

```python
# ❌ FORBIDDEN
def get_safety_label(tri_score: float) -> str:
    if tri_score < 0.10:
        return "SAFE"    # NOT ALLOWED
    if tri_score > 0.75:
        return "UNSAFE"  # NOT ALLOWED
```

**Why Forbidden**: Binary safety labels create false assurance and liability.

---

### 4.6 ❌ GUARANTEE — Risk Bounds

TRI may NEVER make guarantees about risk.

```python
# ❌ FORBIDDEN
def risk_guarantee(tri_score: float) -> str:
    return f"Risk is guaranteed below {tri_score}"  # NOT ALLOWED
```

**Why Forbidden**: ML scores have confidence bounds; guarantees are false precision.

---

## 5. Data Flow Contract

### 5.1 Input Flow (Governance → TRI)

TRI reads governance events. TRI cannot write to governance.

```
┌─────────────────┐
│ Governance      │
│ Event Stream    │
└────────┬────────┘
         │ READ ONLY
         ▼
┌─────────────────┐
│ TRI Computation │
└─────────────────┘
```

**Constraints**:
- TRI reads from event sink
- TRI cannot write events
- TRI cannot delete events
- TRI cannot modify events

### 5.2 Output Flow (TRI → Consumers)

TRI writes to annotation channels only.

```
┌─────────────────┐
│ TRI Computation │
└────────┬────────┘
         │ ANNOTATIONS ONLY
         ├──────────────────┐──────────────────┐
         ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│Trust Center │    │Audit Bundle │    │  Human UI   │
│ (display)   │    │(supplement) │    │ (context)   │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Constraints**:
- Outputs go to display/context layers
- Outputs never go to decision layers
- Outputs are optional (system works without)

---

## 6. Failure Handling

### 6.1 TRI Unavailable

```python
def handle_tri_unavailable() -> TrustRiskIndex:
    """
    Return when TRI cannot be computed.

    Governance continues normally.
    """
    return TrustRiskIndex(
        value=None,
        tier="UNKNOWN",
        confidence=0.0,
        message="Trust Risk Index unavailable",
        failure_mode="TRI_UNAVAILABLE",
    )
```

**System Behavior**: No change. Governance proceeds without TRI.

### 6.2 TRI Computation Error

```python
def handle_tri_error(error: Exception) -> TrustRiskIndex:
    """
    Return when TRI computation fails.

    Governance continues normally.
    """
    return TrustRiskIndex(
        value=None,
        tier="UNKNOWN",
        confidence=0.0,
        message=f"TRI computation error: {type(error).__name__}",
        failure_mode="TRI_ERROR",
    )
```

**System Behavior**: No change. Governance proceeds without TRI.

### 6.3 Stale TRI

```python
def handle_stale_tri(tri: TrustRiskIndex, max_age_hours: int = 24) -> TrustRiskIndex:
    """
    Mark TRI as stale if too old.

    Does NOT block anything. Just adds warning.
    """
    age_hours = (now() - tri.computed_at).total_seconds() / 3600
    if age_hours > max_age_hours:
        tri.staleness_warning = f"TRI is {age_hours:.1f} hours old"
    return tri
```

**System Behavior**: Display warning. No operational change.

---

## 7. Audit Requirements

### 7.1 Separation of Concerns

Every audit record must clearly show:

1. **Governance decision** — ACM/DRCP output
2. **TRI annotation** — If present
3. **Independence statement** — Decision was not influenced by TRI

```json
{
  "event_id": "gov-abc123",
  "timestamp": "2025-12-17T15:30:00Z",

  "governance_decision": {
    "decision": "ALLOW",
    "evaluated_by": "ACM_EVALUATOR",
    "acm_version": "2.3.1"
  },

  "tri_annotation": {
    "value": 0.23,
    "tier": "LOW",
    "model_version": "tri-v1.0.0",
    "note": "ANNOTATION ONLY - DID NOT INFLUENCE DECISION"
  },

  "audit_assertion": "Governance decision independent of TRI annotation"
}
```

### 7.2 Regulator Response Template

When asked "Does your ML affect decisions?":

> "No. The Trust Risk Index is a quantified risk signal derived from governance
> telemetry. It is displayed in our Trust Center and included in audit bundles
> as supplementary context. All access control decisions are made by
> deterministic rules in our Access Control Matrix (ACM). The TRI cannot allow,
> deny, escalate, or modify any decision. It is advisory only."

---

## 8. Testing Requirements

### 8.1 Independence Test

```python
def test_governance_independent_of_tri():
    """
    Verify governance decisions are identical with/without TRI.
    """
    intents = generate_test_intents(n=1000)

    # Decisions without TRI
    results_without = [acm.evaluate(i) for i in intents]

    # Decisions with TRI
    results_with = [acm.evaluate_with_tri_context(i, tri) for i in intents]

    # MUST be identical
    for r1, r2 in zip(results_without, results_with):
        assert r1.decision == r2.decision
        assert r1.reason_code == r2.reason_code
```

### 8.2 No-Authority Test

```python
def test_tri_has_no_authority():
    """
    Verify TRI cannot affect system state.
    """
    # TRI should have no methods that:
    assert not hasattr(tri, 'allow')
    assert not hasattr(tri, 'deny')
    assert not hasattr(tri, 'execute')
    assert not hasattr(tri, 'block')
    assert not hasattr(tri, 'escalate')
    assert not hasattr(tri, 'modify_decision')
```

### 8.3 Failure Resilience Test

```python
def test_system_works_without_tri():
    """
    Verify system operates normally when TRI fails.
    """
    # Simulate TRI failure
    mock_tri = MockTRI(always_fail=True)

    # System should still work
    for intent in test_intents:
        result = acm.evaluate(intent)
        assert result.decision in ["ALLOW", "DENY"]
```

---

## 9. Contract Summary

| Action | TRI Permitted | Governance Required |
|--------|---------------|---------------------|
| Display in Trust Center | ✅ Yes | No |
| Include in audit bundle | ✅ Yes | No |
| Inform human reviewer | ✅ Yes | No |
| Suggest review order | ✅ Yes | No |
| Answer procurement questions | ✅ Yes | No |
| Allow/permit action | ❌ No | Yes (ACM) |
| Deny/block action | ❌ No | Yes (ACM) |
| Escalate to human | ❌ No | Yes (DRCP) |
| Trigger automation | ❌ No | Yes (Governance) |
| Modify decision | ❌ No | Never |
| Label as safe/unsafe | ❌ No | Never |

---

## 10. Acceptance Criteria

- [x] Authority hierarchy documented
- [x] Permitted actions explicitly listed
- [x] Forbidden actions explicitly listed
- [x] Data flow contracts specified
- [x] Failure handling defined
- [x] Audit requirements specified
- [x] Test requirements specified
- [x] Regulator response template provided

---

## 11. References

- [core/governance/acm_evaluator.py](../../core/governance/acm_evaluator.py) — ACM authority
- [core/governance/drcp.py](../../core/governance/drcp.py) — Escalation authority
- [TRUST_RISK_MODEL.md](./TRUST_RISK_MODEL.md) — TRI computation
- [RISK_GOVERNANCE_CONTRACT.md](./RISK_GOVERNANCE_CONTRACT.md) — General ML contract
