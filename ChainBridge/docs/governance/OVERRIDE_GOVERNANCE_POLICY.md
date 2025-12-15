# ChainBridge Override Governance Policy

**Owner:** GID-08 ALEX — Governance & Alignment Engine
**Version:** 1.0
**Effective:** 2025-12-15
**Status:** ACTIVE
**PAC Reference:** PAC-06-E

---

## Purpose

**Theme: Humans Stay in Control**

This policy ensures that automated decisions can always be overridden by authorized humans, with full audit trail and accountability. Every override is:
- **Traceable** — Who, what, when, why
- **Auditable** — Immutable record
- **Justified** — Documented reason required
- **Authorized** — Role-based permissions

---

## 1. Override State Machine

### 1.1 State Diagram

```
                                    ┌─────────────────┐
                                    │                 │
                                    ▼                 │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   PENDING    │───▶│  REQUESTED   │───▶│   APPROVED   │
│  (Initial)   │    │  (Override   │    │  (Override   │
│              │    │   Initiated) │    │   Applied)   │
└──────────────┘    └──────────────┘    └──────────────┘
                           │                    │
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐    ┌──────────────┐
                    │   REJECTED   │    │   REVERTED   │
                    │  (Override   │    │  (Override   │
                    │   Denied)    │    │   Undone)    │
                    └──────────────┘    └──────────────┘
```

### 1.2 State Definitions

| State | Description | Next States |
|-------|-------------|-------------|
| **PENDING** | Automated decision awaiting review | REQUESTED |
| **REQUESTED** | Override has been initiated by operator | APPROVED, REJECTED |
| **APPROVED** | Override approved and applied | REVERTED |
| **REJECTED** | Override denied by approver | (terminal) |
| **REVERTED** | Override was undone, original restored | (terminal) |

### 1.3 Transition Rules

| From | To | Trigger | Authorization |
|------|----|---------|---------------|
| PENDING | REQUESTED | Operator clicks "Override" | `override:request` |
| REQUESTED | APPROVED | Approver confirms | `override:approve` |
| REQUESTED | REJECTED | Approver denies | `override:approve` |
| APPROVED | REVERTED | Operator reverts | `override:revert` |

---

## 2. Approval Authority Matrix

### 2.1 Risk-Based Authorization

| Risk Tier | Override Type | Required Approvals | Approver Role |
|-----------|--------------|-------------------|---------------|
| **LOW** (0.0-0.3) | Single decision | 1 | Operator |
| **MEDIUM** (0.3-0.7) | Single decision | 1 | Senior Operator |
| **HIGH** (0.7-1.0) | Single decision | 2 | Lead + Compliance |
| **CRITICAL** | Policy/system-wide | 2 | ALEX (GID-08) + Human Executive |

### 2.2 Role Permissions

| Role | Permissions | Scope |
|------|-------------|-------|
| **Operator** | `override:request`, `override:revert` | Own assignments |
| **Senior Operator** | `override:request`, `override:approve`, `override:revert` | Team scope |
| **Lead** | All operator + `override:approve` for HIGH | Department scope |
| **Compliance** | `override:approve` for HIGH, audit review | All |
| **ALEX (GID-08)** | Policy override validation | System-wide |
| **Human Executive** | Emergency override, policy changes | System-wide |

### 2.3 Dual-Approval Flow (HIGH/CRITICAL)

```
Operator Request
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   Approver   │────▶│   Approver   │────▶ APPROVED
│      #1      │     │      #2      │
│   (Lead)     │     │ (Compliance) │
└──────────────┘     └──────────────┘
       │                    │
       ▼                    ▼
   REJECTED             REJECTED
  (if denied)          (if denied)
```

---

## 3. Required Fields

### 3.1 Override Request (Mandatory)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `override_id` | UUID | ✅ | Unique override identifier |
| `artifact_id` | UUID | ✅ | Decision artifact being overridden |
| `requested_by` | string | ✅ | Operator email/ID |
| `requested_at` | datetime | ✅ | UTC timestamp |
| `original_decision` | enum | ✅ | APPROVE/REJECT/CONDITIONAL/ESCALATE |
| `new_decision` | enum | ✅ | Requested new decision |
| `reason` | string | ✅ | Justification (min 20 chars) |
| `risk_tier` | enum | ✅ | LOW/MEDIUM/HIGH/CRITICAL |
| `supporting_evidence` | array | ⚠️ | References/documents (required for HIGH+) |

### 3.2 Override Approval (Mandatory)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approved_by` | string | ✅ | Approver email/ID |
| `approved_at` | datetime | ✅ | UTC timestamp |
| `approval_notes` | string | ⚠️ | Additional context (optional for LOW) |
| `approval_reference` | string | ⚠️ | External auth reference (required for HIGH+) |

### 3.3 Override Rejection (Mandatory)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rejected_by` | string | ✅ | Rejector email/ID |
| `rejected_at` | datetime | ✅ | UTC timestamp |
| `rejection_reason` | string | ✅ | Why override was denied |

### 3.4 Override Reversion (Mandatory)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reverted_by` | string | ✅ | Who reverted |
| `reverted_at` | datetime | ✅ | UTC timestamp |
| `reversion_reason` | string | ✅ | Why override was undone |

---

## 4. Audit Trail

### 4.1 Event Types

Every override generates immutable audit events:

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `OVERRIDE_REQUESTED` | Operator initiates override | Request fields |
| `OVERRIDE_APPROVED` | Approver confirms | Approval fields |
| `OVERRIDE_REJECTED` | Approver denies | Rejection fields |
| `OVERRIDE_APPLIED` | System applies override | Before/after state |
| `OVERRIDE_REVERTED` | Operator reverts | Reversion fields |

### 4.2 Audit Event Schema

```json
{
  "event_id": "evt-uuid",
  "event_type": "OVERRIDE_APPROVED",
  "artifact_id": "art-uuid",
  "override_id": "ovr-uuid",
  "actor": "operator@chainbridge.io",
  "timestamp": "2025-12-15T14:30:00Z",
  "details": {
    "original_decision": "REJECT",
    "new_decision": "APPROVE",
    "reason": "Manual verification confirmed legitimate transaction",
    "risk_tier": "MEDIUM",
    "approver": "lead@chainbridge.io"
  },
  "policy_ref": "OVERRIDE_GOVERNANCE_POLICY_v1.0",
  "immutable": true
}
```

### 4.3 Retention Policy

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Override requests | 7 years | Regulatory compliance |
| Audit events | 7 years | SOC 2 / ISO 27001 |
| Supporting evidence | 7 years | Dispute resolution |

---

## 5. Constraints & Guardrails

### 5.1 Hard Constraints

| # | Constraint | Enforcement |
|---|------------|-------------|
| 1 | Override reason required | BLOCK if `reason` empty or < 20 chars |
| 2 | Dual approval for HIGH+ | BLOCK if only 1 approver |
| 3 | Self-approval prohibited | BLOCK if `requested_by` == `approved_by` |
| 4 | Audit trail immutable | BLOCK any edit/delete of audit events |
| 5 | Time-bound requests | AUTO-REJECT if pending > 24 hours |

### 5.2 Soft Constraints (Alerts)

| # | Constraint | Action |
|---|------------|--------|
| 1 | Override rate > 5% | ALERT to compliance |
| 2 | Same operator > 3 overrides/day | ALERT to lead |
| 3 | Override on same artifact twice | ALERT + require escalation |
| 4 | Reversion within 1 hour | ALERT (potential error) |

### 5.3 Emergency Override

For system-critical situations:

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️  EMERGENCY OVERRIDE PROTOCOL                        │
├─────────────────────────────────────────────────────────┤
│  1. Human Executive authorization required              │
│  2. ALEX (GID-08) must validate policy compliance       │
│  3. Post-incident review within 24 hours                │
│  4. All standard audit fields + incident reference      │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Integration Points

### 6.1 OCC Artifact Integration

Overrides attach to OCC artifacts via:
- `artifact.override_history[]` — List of override records
- `artifact.current_override_status` — Active override state
- `artifact.override_count` — Total overrides on this artifact

### 6.2 Decision Schema Integration

Links to `DECISION_EXPLAINABILITY_POLICY.md`:
- `decision.override_reason` — From override request
- `decision.reviewed_by` — From override approval
- `decision.reviewed_at` — From override timestamp

### 6.3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/oc/decisions/{id}/override` | POST | Request override |
| `/oc/decisions/{id}/override/approve` | POST | Approve override |
| `/oc/decisions/{id}/override/reject` | POST | Reject override |
| `/oc/decisions/{id}/override/revert` | POST | Revert override |
| `/oc/decisions/{id}/override/history` | GET | Override audit trail |

---

## 7. Compliance Mapping

| Regulation | Requirement | Coverage |
|------------|-------------|----------|
| **GDPR Art. 22** | Human intervention right | ✅ Override flow |
| **EU AI Act** | Human oversight for high-risk AI | ✅ Dual approval |
| **SOC 2 CC6.1** | Logical access controls | ✅ Role matrix |
| **ISO 27001 A.9** | Access control policy | ✅ Permission model |

---

## 8. Quick Reference

### Override Checklist

```
□ Identify artifact to override
□ Document reason (≥20 chars)
□ Attach evidence (if HIGH+)
□ Submit request
□ Await approval (dual if HIGH+)
□ Verify override applied
□ Confirm audit event logged
```

### Emergency Protocol

```
1. Contact Human Executive
2. State: artifact_id, reason, urgency
3. ALEX validates policy compliance
4. Executive authorizes
5. Override applied
6. Post-incident review scheduled
```

---

## References

- [Decision Explainability Policy](./DECISION_EXPLAINABILITY_POLICY.md)
- [PAC Standard](./PAC_STANDARD.md)
- [ALEX Protection Manual](../../docs/governance/ALEX_PROTECTION_MANUAL.md)
- [OCC Artifact Schema](../../core/occ/schemas/artifact.py)
- [Decision Schema](../../core/oc/schemas/decision.py)
