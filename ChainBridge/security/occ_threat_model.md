# OCC Threat Model v1.0

**PAC Reference:** PAC-OCC-P02  
**Constitutional Authority:** OCC_CONSTITUTION_v1.0, Article VII  
**Document Classification:** SECURITY  
**Author:** BENSON (GID-00)  
**Reviewed By:** ALEX (GID-08), Lex  
**Effective Date:** 2025-01-05  

---

## 1. Executive Summary

This document defines the threat model for the Operator Control Center (OCC) v1.0. The OCC is the human authority layer governing all AI orchestration within ChainBridge. Given its constitutional authority to override automated decisions, the OCC represents a critical security boundary that must be protected against both external attacks and insider threats.

**Threat Surface Classification:** CRITICAL

---

## 2. System Overview

### 2.1 Components in Scope

| Component | Description | Criticality |
|-----------|-------------|-------------|
| `occ_queue.py` | Priority-ordered action queue | HIGH |
| `occ_actions.py` | Action executor with tier enforcement | CRITICAL |
| `pdo_state_machine.py` | PDO state management | HIGH |
| `occ_audit_log.py` | Immutable audit trail | CRITICAL |
| `pdo_replay_engine.py` | Deterministic state replay | MEDIUM |

### 2.2 Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNTRUSTED ZONE                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Browser    │  │ API Client   │  │  External    │          │
│  │   (Human)    │  │ (Automated)  │  │  Systems     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼───────────────────┘
          │                 │                 │
    ══════╪═════════════════╪═════════════════╪════════════════════
          │    AUTHENTICATION BOUNDARY        │
    ══════╪═════════════════╪═════════════════╪════════════════════
          │                 │                 │
┌─────────┼─────────────────┼─────────────────┼───────────────────┐
│         ▼                 ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 OCC API Gateway                          │   │
│  │           (Identity + MFA Verification)                  │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│    ════════════════════════╪════════════════════════════════   │
│           TIER ENFORCEMENT BOUNDARY (INV-OCC-005)              │
│    ════════════════════════╪════════════════════════════════   │
│                            │                                    │
│  ┌─────────────────────────┼───────────────────────────────┐   │
│  │                         ▼                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │  OCC Queue   │──│ OCC Actions  │──│ PDO State    │  │   │
│  │  │              │  │              │  │   Machine    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  │                         │                               │   │
│  │  ┌──────────────────────┼──────────────────────────┐   │   │
│  │  │                      ▼                          │   │   │
│  │  │  ┌──────────────┐  ┌──────────────┐            │   │   │
│  │  │  │ Audit Log    │  │ Replay       │            │   │   │
│  │  │  │ (Immutable)  │  │ Engine       │            │   │   │
│  │  │  └──────────────┘  └──────────────┘            │   │   │
│  │  │                 AUDIT ZONE                      │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                     ENFORCEMENT ZONE                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                        TRUSTED ZONE                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Threat Categories

### 3.1 Authentication & Identity Threats

#### T-AUTH-001: Session Hijacking
- **Description:** Attacker steals valid operator session token
- **Severity:** CRITICAL
- **Mitigations:**
  - Short session timeout (15 minutes idle)
  - Session binding to IP + User-Agent
  - MFA required for override actions
  - Session invalidation on suspicious activity

#### T-AUTH-002: Credential Stuffing
- **Description:** Attacker uses leaked credentials from other services
- **Severity:** HIGH
- **Mitigations:**
  - MFA mandatory for all operators
  - Rate limiting on authentication attempts
  - Breached password detection
  - Account lockout after failed attempts

#### T-AUTH-003: MFA Bypass
- **Description:** Attacker bypasses MFA through social engineering or technical means
- **Severity:** CRITICAL
- **Mitigations:**
  - Hardware security keys preferred
  - No SMS-based MFA (SIM swapping risk)
  - MFA re-verification for override actions
  - Phishing-resistant MFA (WebAuthn)

#### T-AUTH-004: Insider Credential Sharing
- **Description:** Operators share credentials with unauthorized individuals
- **Severity:** HIGH
- **Mitigations:**
  - Credential sharing detection (multiple IPs)
  - Personal accountability tied to identity
  - Regular credential rotation
  - Behavioral analytics on login patterns

### 3.2 Authorization & Access Control Threats

#### T-AUTHZ-001: Tier Escalation
- **Description:** Lower-tier operator attempts actions requiring higher tier
- **Severity:** CRITICAL
- **Mitigations:**
  - Invariant INV-OCC-005 (Tier Enforcement)
  - Server-side tier verification on every action
  - No client-side tier checks
  - Audit logging of all tier violations

#### T-AUTHZ-002: Self-Override Abuse
- **Description:** Operator overrides their own prior decisions
- **Severity:** HIGH
- **Mitigations:**
  - Invariant INV-OVR-010 (No Self-Override)
  - Exception only for T5 emergency with incident ID
  - Audit trail tracks original decision author

#### T-AUTHZ-003: Value Limit Bypass
- **Description:** Operator attempts override exceeding tier value limit
- **Severity:** HIGH
- **Mitigations:**
  - Invariant INV-OVR-008 (Override Scope Limits)
  - T4 limit: $10M
  - T5/T6 unlimited (but heavily audited)
  - Real-time value verification

#### T-AUTHZ-004: Role Confusion
- **Description:** Operator performs actions outside their role scope
- **Severity:** MEDIUM
- **Mitigations:**
  - Clear tier definitions in OCC_AUTHORITY_MODEL.yaml
  - Action-to-tier mapping enforced in code
  - Regular access reviews

### 3.3 Data Integrity Threats

#### T-INTEG-001: Audit Log Tampering
- **Description:** Attacker modifies or deletes audit records
- **Severity:** CRITICAL
- **Mitigations:**
  - Invariant INV-OCC-002 (Override Audit Immutability)
  - Invariant INV-OVR-003 (Override Immutability)
  - Hash-chained audit records
  - No UPDATE/DELETE operations allowed
  - Append-only log files
  - Periodic integrity verification

#### T-INTEG-002: Hash Chain Break
- **Description:** Attacker attempts to forge hash chain
- **Severity:** CRITICAL
- **Mitigations:**
  - SHA-256 hashing
  - Chain verification on read operations
  - External backup with independent hash computation
  - Alerting on chain integrity failures

#### T-INTEG-003: PDO State Corruption
- **Description:** Attacker manipulates PDO state outside state machine
- **Severity:** HIGH
- **Mitigations:**
  - All state changes via state machine only
  - Invalid transition rejection
  - Override markers permanent (INV-OVR-006)
  - Replay engine can detect inconsistencies

#### T-INTEG-004: Replay Attack
- **Description:** Attacker replays valid action to execute it again
- **Severity:** HIGH
- **Mitigations:**
  - Unique action IDs with timestamps
  - Sequence number tracking in queue
  - Duplicate detection in ingress validation
  - Nonce/token per request

### 3.4 Availability Threats

#### T-AVAIL-001: Queue Flooding
- **Description:** Attacker floods queue with low-priority actions
- **Severity:** MEDIUM
- **Mitigations:**
  - Queue capacity limit (10,000 items)
  - Per-operator rate limiting
  - Priority-based processing
  - Emergency escalation bypasses queue

#### T-AVAIL-002: State Machine Deadlock
- **Description:** PDO enters state preventing further transitions
- **Severity:** MEDIUM
- **Mitigations:**
  - Well-defined transition matrix
  - No cycles in terminal states
  - Timeout-based expiration
  - T5 emergency override capability

#### T-AVAIL-003: Audit Log Disk Exhaustion
- **Description:** Log files fill disk, causing system failure
- **Severity:** HIGH
- **Mitigations:**
  - Log rotation with archival
  - Disk space monitoring
  - Alert on 80% capacity
  - Off-host log shipping

#### T-AVAIL-004: Denial of Service via Validation
- **Description:** Crafted inputs cause expensive validation operations
- **Severity:** MEDIUM
- **Mitigations:**
  - Input size limits
  - Validation timeout
  - Request rate limiting
  - Async validation where possible

### 3.5 Insider Threats

#### T-INSIDER-001: Malicious T4 Operator
- **Description:** Compromised or malicious T4 operator abuses override power
- **Severity:** CRITICAL
- **Mitigations:**
  - T4 override limit: $10M
  - All overrides permanently logged
  - Justification requirement (INV-OVR-002)
  - Post-hoc audit review
  - Behavioral anomaly detection

#### T-INSIDER-002: Malicious T5 Executive
- **Description:** Compromised T5 executive with elevated privileges
- **Severity:** CRITICAL
- **Mitigations:**
  - No single T5 can modify audit log
  - All T5 actions heavily logged
  - Regular T5 access review
  - Separation of duties where possible

#### T-INSIDER-003: Collusion Attack
- **Description:** Multiple operators collude to approve fraudulent transaction
- **Severity:** HIGH
- **Mitigations:**
  - INV-OVR-010 prevents self-approval
  - Audit trail shows all participants
  - Pattern detection for coordinated approvals
  - Independent audit review

#### T-INSIDER-004: Boilerplate Justification
- **Description:** Operator uses templated justifications to bypass review
- **Severity:** MEDIUM
- **Mitigations:**
  - INV-OVR-002 blocks known templates
  - Minimum 50 character justification
  - Machine learning on justification quality
  - Sample audit of justifications

---

## 4. Attack Trees

### 4.1 Unauthorized Override Attack Tree

```
GOAL: Execute unauthorized override
├── 1. Bypass Authentication
│   ├── 1.1 Steal session token [T-AUTH-001]
│   ├── 1.2 Credential stuffing [T-AUTH-002]
│   └── 1.3 Bypass MFA [T-AUTH-003]
├── 2. Bypass Authorization
│   ├── 2.1 Escalate tier [T-AUTHZ-001]
│   ├── 2.2 Self-override [T-AUTHZ-002]
│   └── 2.3 Exceed value limit [T-AUTHZ-003]
├── 3. Corrupt Data
│   ├── 3.1 Tamper audit log [T-INTEG-001]
│   ├── 3.2 Break hash chain [T-INTEG-002]
│   └── 3.3 Corrupt PDO state [T-INTEG-003]
└── 4. Insider Abuse
    ├── 4.1 Malicious operator [T-INSIDER-001]
    ├── 4.2 Compromised executive [T-INSIDER-002]
    └── 4.3 Collusion [T-INSIDER-003]
```

### 4.2 Audit Evasion Attack Tree

```
GOAL: Perform action without audit record
├── 1. Delete Audit Records
│   ├── 1.1 Direct DB access → BLOCKED by immutability
│   ├── 1.2 Log file deletion → Detected by hash chain
│   └── 1.3 Truncate operation → BLOCKED by code
├── 2. Modify Audit Records
│   ├── 2.1 Update operation → BLOCKED by code
│   ├── 2.2 Memory corruption → Detected by hash verification
│   └── 2.3 Forge hash chain → Computationally infeasible
├── 3. Bypass Audit System
│   ├── 3.1 Direct state change → BLOCKED by state machine
│   ├── 3.2 Race condition → Mitigated by locking
│   └── 3.3 Inject before audit → Audit is synchronous
└── 4. Deny Attribution
    ├── 4.1 Share credentials → Detected by behavioral analytics
    ├── 4.2 Anonymous action → BLOCKED by INV-OCC-004
    └── 4.3 Spoof identity → Blocked by MFA + session binding
```

---

## 5. Security Controls Summary

### 5.1 Preventive Controls

| Control | Threats Mitigated | Implementation |
|---------|-------------------|----------------|
| MFA Requirement | T-AUTH-001, T-AUTH-002, T-AUTH-003 | `occ_actions.py` |
| Tier Enforcement | T-AUTHZ-001, T-AUTHZ-003 | `occ_actions.py`, INV-OCC-005 |
| Self-Override Block | T-AUTHZ-002, T-INSIDER-003 | `occ_actions.py`, INV-OVR-010 |
| Immutable Audit | T-INTEG-001, T-INTEG-002 | `occ_audit_log.py`, INV-OCC-002 |
| Hash Chain | T-INTEG-001, T-INTEG-002, T-INTEG-004 | All components |
| Queue Limits | T-AVAIL-001 | `occ_queue.py` |
| Template Detection | T-INSIDER-004 | `occ_actions.py`, INV-OVR-002 |

### 5.2 Detective Controls

| Control | Threats Detected | Implementation |
|---------|------------------|----------------|
| Hash Chain Verification | T-INTEG-001, T-INTEG-002 | `occ_audit_log.py::verify_chain_integrity()` |
| Replay Validation | T-INTEG-003, T-INTEG-004 | `pdo_replay_engine.py` |
| Behavioral Analytics | T-AUTH-004, T-INSIDER-001 | External SIEM integration |
| Audit Review | T-INSIDER-001, T-INSIDER-003 | Manual process |
| Anomaly Detection | T-INSIDER-001, T-INSIDER-003 | External ML system |

### 5.3 Responsive Controls

| Control | Response To | Implementation |
|---------|-------------|----------------|
| Fail-Closed | Any error condition | All components |
| Account Lockout | T-AUTH-002 | Authentication layer |
| Session Invalidation | T-AUTH-001, T-AUTH-003 | Session management |
| Incident Escalation | T-INSIDER-001, T-INSIDER-002 | Alerting system |
| Kill Switch | Systemic compromise | T6 emergency action |

---

## 6. Residual Risks

### 6.1 Accepted Risks

| Risk | Severity | Justification |
|------|----------|---------------|
| T5 Executive Abuse | CRITICAL | Mitigated by audit + separation of duties; full prevention would eliminate human oversight capability |
| Sophisticated Collusion | HIGH | Multi-party collusion difficult to prevent; detected through audit review |
| Zero-Day in Dependencies | MEDIUM | Standard security practice; mitigated by dependency scanning |

### 6.2 Risk Mitigation Gaps

| Gap | Required Mitigation | Status |
|-----|---------------------|--------|
| Hardware Security Key Integration | Implement WebAuthn | PLANNED |
| Real-time Anomaly Detection | Deploy ML-based detection | PLANNED |
| Cross-Service Audit Correlation | Implement SIEM integration | PLANNED |

---

## 7. Compliance Mapping

| Requirement | Standard | OCC Control |
|-------------|----------|-------------|
| Access Control | SOC 2 CC6.1 | Tier enforcement, MFA |
| Audit Logging | SOC 2 CC7.2 | Immutable audit log |
| Data Integrity | SOC 2 CC6.7 | Hash chain, state machine |
| Incident Response | SOC 2 CC7.4 | Kill switch, fail-closed |

---

## 8. Review Schedule

- **Quarterly:** Threat model review
- **Monthly:** Access review for T4+ operators
- **Weekly:** Audit log integrity verification
- **Daily:** Automated anomaly detection
- **Continuous:** Real-time invariant enforcement

---

## 9. Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-05 | BENSON | Initial threat model |

---

**ATTESTATION**

This threat model is complete and accurate as of the effective date. All identified threats have corresponding mitigations implemented or planned. The residual risks are documented and accepted per organizational risk appetite.

**BENSON (GID-00)** — Author  
**ALEX (GID-08)** — Governance Review  
**Lex** — Security Review
