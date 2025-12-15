# ChainBridge Decision Explainability Policy

**Owner:** GID-08 ALEX — Governance & Alignment Engine
**Version:** 1.0
**Effective:** 2025-12-15
**Status:** ACTIVE

---

## Purpose

Answer the regulator's question before it's asked:

> **"Why did the system do this?"**

This policy ensures every automated decision in ChainBridge can be explained in <60 seconds using the Decision Explainability Checklist, Governance Approval Flow, and Override Logging Policy.

---

## 1. Decision Explainability Checklist

Every decision artifact in the OCC (Operator Control Center) **MUST** satisfy these criteria:

### 1.1 Required Fields (Glass-Box Compliance)

| Field | Description | Required | Example |
|-------|-------------|----------|---------|
| `decision_type` | APPROVE / REJECT / CONDITIONAL / ESCALATE | ✅ | `APPROVE` |
| `entity_type` | shipment / payment / settlement / risk | ✅ | `payment` |
| `entity_id` | Unique identifier of the entity | ✅ | `PAY-2025-001` |
| `rationale` | Human-readable explanation | ✅ | `"Low risk score (0.12) with verified counterparty"` |
| `confidence` | Confidence score (0.0-1.0) | ✅ | `0.87` |
| `factors` | List of contributing factors | ✅ | `[{"name": "risk_score", "value": 0.12, "weight": 0.4}]` |
| `inputs` | All inputs that influenced decision | ✅ | `{"risk_score": 0.12, "counterparty_verified": true}` |
| `model_version` | Version of decision model | ✅ | `v1.2.3` |
| `created_at` | UTC timestamp | ✅ | `2025-12-15T10:30:00Z` |

### 1.2 Explainability Questions (60-Second Test)

A decision passes the explainability test if these questions can be answered in <60 seconds:

| # | Question | Source Field |
|---|----------|--------------|
| 1 | **What** was decided? | `decision_type`, `recommendation` |
| 2 | **Why** was it decided? | `rationale`, `factors` |
| 3 | **When** was it decided? | `created_at` |
| 4 | **Who/What** made the decision? | `model_version`, `agent_id` |
| 5 | **What inputs** drove the decision? | `inputs` |
| 6 | **How confident** is the system? | `confidence` |
| 7 | **What conditions** apply? | `conditions` (if CONDITIONAL) |
| 8 | **Was it overridden?** | `override_reason`, `reviewed_by` |

### 1.3 Factor Attribution Format

Each factor in `factors` array must include:

```json
{
  "name": "risk_score",
  "value": 0.12,
  "weight": 0.4,
  "direction": "positive",  // or "negative"
  "explanation": "Low risk score indicates reliable counterparty"
}
```

---

## 2. Governance Approval Flow

### 2.1 Decision Lifecycle States

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   PENDING   │────▶│  IN_REVIEW  │────▶│  APPROVED   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │            ┌─────────────┐            │
       └───────────▶│  ESCALATED  │◀───────────┘
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  REJECTED   │
                    └─────────────┘
```

### 2.2 Approval Authority Matrix

| Decision Type | Risk Tier | Auto-Approve | Requires Review | Requires Escalation |
|--------------|-----------|--------------|-----------------|---------------------|
| Settlement | LOW (0.0-0.3) | ✅ | ❌ | ❌ |
| Settlement | MEDIUM (0.3-0.7) | ❌ | ✅ | ❌ |
| Settlement | HIGH (0.7-1.0) | ❌ | ❌ | ✅ |
| Override | Any | ❌ | ❌ | ✅ |
| Policy Change | Any | ❌ | ❌ | ✅ |

### 2.3 Review Requirements

**For IN_REVIEW decisions:**
- Reviewer must have `governance:review` permission
- Review must be completed within 24 hours
- Review must include `reviewed_by` and `reviewed_at`

**For ESCALATED decisions:**
- Escalation must include `escalation_reason`
- Escalation chain: Agent → Lead → ALEX (GID-08) → Human Operator
- Maximum escalation time: 4 hours

### 2.4 Audit Event Types

Every state transition generates an audit event:

| Event Type | Description |
|------------|-------------|
| `DECISION_CREATED` | Decision artifact created |
| `DECISION_APPROVED` | Decision approved (auto or manual) |
| `DECISION_REJECTED` | Decision rejected |
| `DECISION_ESCALATED` | Decision escalated for review |
| `DECISION_OVERRIDDEN` | Decision manually overridden |
| `DECISION_REVIEWED` | Decision reviewed (no change) |

---

## 3. Override Logging Policy

### 3.1 Override Definition

An **override** occurs when:
- A human operator changes an automated decision
- An agent bypasses a governance rule
- A system parameter is manually adjusted

### 3.2 Mandatory Override Fields

| Field | Description | Required |
|-------|-------------|----------|
| `override_reason` | Why the override was made | ✅ |
| `override_by` | Who made the override | ✅ |
| `override_at` | When the override was made | ✅ |
| `original_decision` | The original automated decision | ✅ |
| `new_decision` | The overridden decision | ✅ |
| `authorization_ref` | Reference to authorization (if applicable) | Conditional |

### 3.3 Override Audit Trail

```json
{
  "event_type": "DECISION_OVERRIDDEN",
  "actor": "operator@chainbridge.io",
  "timestamp": "2025-12-15T14:30:00Z",
  "details": {
    "original_decision": "REJECT",
    "new_decision": "APPROVE",
    "override_reason": "Manual verification confirmed legitimate transaction",
    "authorization_ref": "AUTH-2025-001"
  },
  "artifact_id": "dec-abc123",
  "policy_ref": "DECISION_EXPLAINABILITY_POLICY_v1.0"
}
```

### 3.4 Override Restrictions

| Restriction | Enforcement |
|-------------|-------------|
| Overrides require documented reason | BLOCK if `override_reason` empty |
| HIGH risk overrides require dual approval | ESCALATE to second reviewer |
| Overrides logged to immutable audit trail | AUTOMATIC |
| Override rate monitored (>5% triggers alert) | ALERT |

### 3.5 Override Metrics

The system tracks:
- Override rate by decision type
- Override rate by operator
- Override reversal rate (overrides that were later reverted)
- Time to override (latency from decision to override)

---

## 4. Implementation Checklist

### 4.1 Backend Requirements

- [ ] Decision schema includes all required explainability fields
- [ ] Audit events generated for all state transitions
- [ ] Override logging integrated with audit trail
- [ ] Factor attribution recorded for all decisions

### 4.2 Frontend Requirements

- [ ] Decision details page shows all explainability fields
- [ ] Audit timeline visible for each decision
- [ ] Override UI requires reason field
- [ ] Export capability for regulatory requests

### 4.3 Governance Integration

- [ ] ALEX (GID-08) validates decision compliance
- [ ] CI/CD checks for missing required fields
- [ ] Alerting on override rate thresholds
- [ ] Quarterly explainability audit

---

## 5. Regulatory Compliance

This policy supports compliance with:

| Regulation | Requirement | Coverage |
|------------|-------------|----------|
| **GDPR Art. 22** | Right to explanation for automated decisions | ✅ rationale, factors |
| **EU AI Act** | High-risk AI transparency | ✅ Glass-box models |
| **SOC 2** | Audit trail requirements | ✅ Immutable audit log |
| **ISO 27001** | Information security controls | ✅ Override logging |

---

## 6. Quick Reference

### Answering "Why did the system do this?"

```
1. Open /occ/artifacts/{decision_id}
2. Read `rationale` field (plain English explanation)
3. Review `factors` array (weighted contributions)
4. Check `inputs` (raw data that drove decision)
5. Verify `confidence` score
6. If overridden, read `override_reason`
```

### Time to Answer: <60 seconds ✅

---

## References

- [OCC Artifact Schema](../../core/occ/schemas/artifact.py)
- [Decision Schema](../../core/oc/schemas/decision.py)
- [PAC Standard](./PAC_STANDARD.md)
- [ALEX Protection Manual](../../docs/governance/ALEX_PROTECTION_MANUAL.md)
