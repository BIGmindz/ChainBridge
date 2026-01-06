# Observer Role Definition

**PAC Reference:** PAC-JEFFREY-P45  
**Classification:** AUDIT-GRADE / READ-ONLY  
**Governance Mode:** HARD / FAIL-CLOSED  
**Version:** 1.0.0  
**Date:** 2026-01-02

---

## 1. Overview

The **Observer Role** provides regulated entities (auditors, regulators, compliance officers) with **read-only, audit-grade access** to ChainBridge's Operator Control Center (OCC) for the purpose of verification, inspection, and compliance monitoring.

### Core Principle

> **Observability without authority builds regulatory trust.**

Observers can SEE everything relevant to their audit scope. They can MODIFY nothing. They can DECIDE nothing.

---

## 2. Role Identity

| Property | Value |
|----------|-------|
| Role Name | `OBSERVER` |
| Role Type | External / Regulated |
| Trust Level | `AUDIT_READ_ONLY` |
| Permission Class | `L0_OBSERVE` |
| Session Type | Time-bounded |
| Auth Method | Federated / Pre-authorized |

---

## 3. Observer Categories

### 3.1 Regulatory Observer (`OBSERVER_REG`)

**Purpose:** Government or regulatory body representatives conducting official inspections.

| Attribute | Value |
|-----------|-------|
| Access Scope | Full audit trail |
| PDO Visibility | SHADOW only (no production data) |
| Timeline Depth | Complete history |
| ProofPack Access | Full verification |
| Session Duration | 8 hours max |

### 3.2 External Auditor (`OBSERVER_AUDIT`)

**Purpose:** Third-party auditors conducting SOC2, ISO, or similar assessments.

| Attribute | Value |
|-----------|-------|
| Access Scope | Scoped to audit engagement |
| PDO Visibility | SHADOW only |
| Timeline Depth | Engagement window |
| ProofPack Access | Full verification |
| Session Duration | 4 hours max |

### 3.3 Compliance Monitor (`OBSERVER_COMPLIANCE`)

**Purpose:** Internal or partner compliance teams monitoring ongoing operations.

| Attribute | Value |
|-----------|-------|
| Access Scope | Active operations |
| PDO Visibility | SHADOW only |
| Timeline Depth | Rolling 30 days |
| ProofPack Access | Summary only |
| Session Duration | 2 hours max |

---

## 4. Capability Matrix

### 4.1 Permitted Capabilities

| Capability | Observer | Description |
|------------|----------|-------------|
| `timeline:read` | ✅ | View decision timelines |
| `pdo:read:shadow` | ✅ | Read shadow/test PDOs |
| `proofpack:verify` | ✅ | Verify proofpack integrity |
| `proofpack:download` | ✅ | Download proofpack artifacts |
| `audit:read` | ✅ | Read audit logs |
| `kill_switch:view_state` | ✅ | View kill-switch state |
| `health:read` | ✅ | Read system health |
| `activity:read` | ✅ | Read activity logs |
| `agent:view_state` | ✅ | View agent states |
| `governance:read` | ✅ | Read governance rules |

### 4.2 Denied Capabilities (HARD BLOCK)

| Capability | Observer | Reason |
|------------|----------|--------|
| `pdo:create` | ❌ | No mutation authority |
| `pdo:update` | ❌ | No mutation authority |
| `pdo:delete` | ❌ | No mutation authority |
| `pdo:read:production` | ❌ | Production data isolation |
| `kill_switch:arm` | ❌ | No control authority |
| `kill_switch:engage` | ❌ | No control authority |
| `kill_switch:disengage` | ❌ | No control authority |
| `settlement:*` | ❌ | No settlement authority |
| `operator:*` | ❌ | No operator authority |
| `config:*` | ❌ | No configuration authority |
| `agent:modify` | ❌ | No agent control |
| `governance:modify` | ❌ | No governance control |
| `user:*` | ❌ | No user management |

---

## 5. Authentication Requirements

### 5.1 Identity Verification

```
REQUIRED:
- Pre-authorized organization
- Named individual (no shared accounts)
- Multi-factor authentication (MFA)
- Session-scoped JWT
```

### 5.2 Token Constraints

| Constraint | Value |
|------------|-------|
| Token Lifetime | 4 hours max |
| Token Refresh | NOT PERMITTED |
| Token Audience | `chainbridge-observer` |
| Token Issuer | ChainBridge Auth Service |
| Token Scope | `observer:read` |

### 5.3 Session Constraints

| Constraint | Value |
|------------|-------|
| Concurrent Sessions | 1 per user |
| Idle Timeout | 30 minutes |
| Absolute Timeout | Per observer category |
| Re-auth Required | On timeout |

---

## 6. Data Access Boundaries

### 6.1 Visible Data

- All SHADOW classification PDOs
- Decision timelines and outcomes
- ProofPack verification data
- Audit logs (sanitized)
- Kill-switch state (read-only)
- Agent states (read-only)
- System health metrics

### 6.2 Hidden Data

- PRODUCTION classification PDOs
- Real financial data
- Customer PII
- Internal operator communications
- System credentials
- Kill-switch control interfaces
- Agent modification interfaces

### 6.3 Data Sanitization

All observer-visible data is processed through:

1. **PII Scrubber** — Removes/masks personal identifiers
2. **Amount Masker** — Replaces real amounts with synthetic values
3. **Reference Hasher** — Hashes external references
4. **Timestamp Normalizer** — Preserves sequence, masks exact times

---

## 7. Behavioral Constraints

### 7.1 Rate Limits

| Limit | Value |
|-------|-------|
| Requests per minute | 20 |
| Requests per hour | 300 |
| Concurrent connections | 1 |
| Burst limit | 5 |
| ProofPack downloads/day | 50 |

### 7.2 Export Restrictions

| Export Type | Permitted |
|-------------|-----------|
| Timeline JSON | ✅ (sanitized) |
| ProofPack ZIP | ✅ (hash-verified) |
| Audit CSV | ✅ (limited fields) |
| Bulk export | ❌ |
| API data dump | ❌ |
| Raw database access | ❌ |

---

## 8. Audit Trail Requirements

### 8.1 All Observer Actions Logged

```json
{
  "observer_id": "obs-12345",
  "observer_org": "SEC",
  "observer_category": "OBSERVER_REG",
  "action": "proofpack:verify",
  "target": "pdo-67890",
  "timestamp": "2026-01-02T10:30:00Z",
  "ip_hash": "a1b2c3...",
  "session_id": "sess-abc123",
  "result": "success"
}
```

### 8.2 Logged Events

- Session start/end
- Every read operation
- Every verification attempt
- Every export request
- Every denied operation
- Session timeout
- Authentication failures

---

## 9. Kill-Switch Interaction

### 9.1 Observer Visibility

Observers can view:
- Current kill-switch state (ARMED, DISARMED, ENGAGED, COOLDOWN)
- Time of last state change
- Engagement reason (if engaged)
- Cooldown remaining (if in cooldown)

### 9.2 Observer Control

Observers have **ZERO** kill-switch control:
- Cannot arm
- Cannot engage
- Cannot disengage
- Cannot modify cooldown
- Cannot access control API

### 9.3 Kill-Switch Effect on Observers

When kill-switch is **ENGAGED**:
- Existing observer sessions **CONTINUE** (read-only unaffected)
- New observer sessions **BLOCKED**
- Observer visibility **UNCHANGED**

---

## 10. Failure Modes

### 10.1 Authentication Failure

```
Action: DENY ACCESS
Log: Authentication failure recorded
Alert: Security team notified (3+ failures)
```

### 10.2 Authorization Failure

```
Action: DENY OPERATION
Log: Unauthorized attempt recorded
Alert: Compliance team notified
Session: May be terminated on repeated violations
```

### 10.3 Rate Limit Exceeded

```
Action: THROTTLE
Response: HTTP 429
Retry-After: Specified in header
Log: Rate limit violation recorded
```

### 10.4 Session Timeout

```
Action: TERMINATE SESSION
Response: HTTP 401
Requirement: Re-authentication required
Log: Session timeout recorded
```

---

## 11. Governance Invariants

### INV-OBS-001: No Write Paths
Observer role has zero write paths to any system resource.

### INV-OBS-002: No Control Paths
Observer role has zero control paths to any operational function.

### INV-OBS-003: No Escalation Paths
Observer role cannot escalate to any other role within a session.

### INV-OBS-004: Complete Audit Trail
Every observer action is logged with immutable audit trail.

### INV-OBS-005: Production Isolation
Observer role has zero visibility into production data.

### INV-OBS-006: Session Bounded
Observer sessions are time-bounded with hard cutoffs.

---

## 12. Compliance Mapping

| Requirement | Implementation |
|-------------|----------------|
| SOC2 CC6.1 | Session controls, MFA |
| SOC2 CC6.2 | Role-based access |
| SOC2 CC6.3 | Audit logging |
| ISO 27001 A.9 | Access control policy |
| GDPR Art. 32 | Data protection |

---

## 13. Observer Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    OBSERVER LIFECYCLE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. PRE-AUTHORIZATION                                        │
│     └─ Organization approved                                 │
│     └─ Individual named                                      │
│     └─ Scope defined                                         │
│                                                              │
│  2. AUTHENTICATION                                           │
│     └─ MFA verified                                          │
│     └─ Token issued                                          │
│     └─ Session created                                       │
│                                                              │
│  3. ACTIVE SESSION                                           │
│     └─ Read operations permitted                             │
│     └─ All actions logged                                    │
│     └─ Rate limits enforced                                  │
│                                                              │
│  4. SESSION END                                              │
│     └─ Timeout or logout                                     │
│     └─ Session invalidated                                   │
│     └─ Final audit entry                                     │
│                                                              │
│  5. POST-SESSION                                             │
│     └─ Audit trail preserved                                 │
│     └─ Re-auth required for new session                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-02 | BENSON/DAN | Initial observer role definition |

---

**Document Authority:** PAC-JEFFREY-P45  
**Classification:** AUDIT-GRADE  
**Governance:** HARD / FAIL-CLOSED
