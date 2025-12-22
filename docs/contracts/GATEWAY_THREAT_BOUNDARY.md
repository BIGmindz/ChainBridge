# ChainBridge Gateway Threat Boundary Contract

**Document:** GATEWAY_THREAT_BOUNDARY.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Security Boundary Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GATEWAY-CONTRACT-01
**Effective Date:** 2025-12-18
**Alignment:** TRUST_NON_CLAIMS.md (PAC-ALEX-03)

---

## 1. Purpose

This document defines the **threat boundary** for the ChainBridge Gateway:

- What attacks the Gateway defends against
- What attacks the Gateway does NOT defend against
- Trust boundaries between actors
- Failure containment guarantees

**This is a contract, not a threat model.** Every statement maps to enforcement mechanism or explicit non-defense.

---

## 2. Threat Boundary Definition

### 2.1 Gateway Defense Perimeter

The Gateway defends the **authorization chokepoint**. It does not defend infrastructure, network, or application layers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    OUT OF SCOPE (Not Defended)                  │
│   Network Security │ OS Security │ Cloud Security │ Physical   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GATEWAY DEFENSE PERIMETER                      │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │ Unauthorized │  │ Scope      │  │ Governance  │             │
│   │ Execution   │  │ Violation  │  │ Bypass      │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUT OF SCOPE (Not Defended)                  │
│   Application Logic │ Data Correctness │ Business Rules        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Attacks Gateway Defends Against

### 3.1 Authorization Attacks

| Attack Class | Defense Mechanism | Enforcement |
|--------------|-------------------|-------------|
| **Unauthorized execution** | PDO Gate | `require_pdo()` blocks execution without approved PDO |
| **Scope violation** | ACM evaluation | `TARGET_NOT_IN_SCOPE` denial |
| **Capability escalation** | ACM evaluation | `VERB_NOT_PERMITTED` denial |
| **Chain-of-command bypass** | DRCP enforcement | `CHAIN_OF_COMMAND_VIOLATION` denial |

### 3.2 Governance Bypass Attacks

| Attack Class | Defense Mechanism | Enforcement |
|--------------|-------------------|-------------|
| **Skip ALEX evaluation** | Middleware chokepoint | All intents route through `ALEXMiddleware` |
| **Forge decision envelope** | Immutable envelope | `@dataclass(frozen=True)` + audit_ref binding |
| **Retry after denial** | Denial registry | `RETRY_AFTER_DENY_FORBIDDEN` denial |
| **Diggy forbidden verbs** | DRCP rules | `DIGGY_*_FORBIDDEN` denials |

### 3.3 Domain Boundary Attacks

| Attack Class | Defense Mechanism | Enforcement |
|--------------|-------------------|-------------|
| **Atlas runtime code modification** | Atlas scope lock | `ATLAS_DOMAIN_VIOLATION` denial |
| **Unknown agent access** | ACM loader | `UNKNOWN_AGENT` denial |
| **Unloaded ACM access** | ACM validation | `ACM_NOT_LOADED` denial |

### 3.4 State Manipulation Attacks

| Attack Class | Defense Mechanism | Enforcement |
|--------------|-------------------|-------------|
| **Invalid state transition** | FSM validator | `InvalidTransitionError` |
| **Terminal state bypass** | PDO Gate | PDO must be in `DECIDED` state |
| **Outcome manipulation** | PDO immutability | PDO fields frozen after creation |

---

## 4. Attacks Gateway Does NOT Defend Against

### 4.1 Infrastructure Attacks (Out of Scope)

| Attack Class | Why Not Defended | Responsibility |
|--------------|------------------|----------------|
| **Network intrusion** | Gateway operates at application layer | Network security team |
| **Cloud provider breach** | Infrastructure security | Cloud provider + DevOps |
| **OS-level compromise** | Operating system security | Platform team |
| **Container escape** | Container runtime security | Platform team |
| **DDoS** | Edge protection | CDN / Edge security |

**Implication:** If infrastructure is compromised, Gateway controls can be bypassed.

### 4.2 Credential Attacks (Out of Scope)

| Attack Class | Why Not Defended | Responsibility |
|--------------|------------------|----------------|
| **Credential theft** | Secret management | Vault / IAM |
| **API key compromise** | Key rotation | Security operations |
| **Session hijacking** | Session management | Application layer |
| **Token replay** | Token validation | Authentication service |

**Implication:** Gateway trusts that authenticated requests are legitimate.

### 4.3 Application Logic Attacks (Out of Scope)

| Attack Class | Why Not Defended | Responsibility |
|--------------|------------------|----------------|
| **Business logic flaws** | Gateway enforces governance, not logic | Application developers |
| **Data validation bypass** | Gateway validates schema, not data | Application layer |
| **SQL injection** | Gateway does not interact with databases | Application layer |
| **Input sanitization** | Gateway passes inputs without transformation | Application layer |

**Implication:** Malicious inputs that pass schema validation reach downstream systems.

### 4.4 Social Engineering Attacks (Out of Scope)

| Attack Class | Why Not Defended | Responsibility |
|--------------|------------------|----------------|
| **Phishing** | Human factor | Security awareness |
| **Insider threat (intent)** | Gateway governs capability, not intent | HR / Legal |
| **Pretexting** | Human factor | Security awareness |

**Implication:** Authorized users acting maliciously are not blocked by Gateway.

### 4.5 Supply Chain Attacks (Out of Scope)

| Attack Class | Why Not Defended | Responsibility |
|--------------|------------------|----------------|
| **Dependency poisoning** | Package management | DevSecOps |
| **Build pipeline compromise** | CI/CD security | Platform team |
| **Malicious package update** | Dependency scanning | Security tooling |

**Implication:** Malicious code in dependencies executes within Gateway's trust boundary.

---

## 5. Trust Boundaries

### 5.1 Trust Hierarchy

| Actor | Trust Level | Gateway Trust |
|-------|-------------|---------------|
| **ALEX (GID-08)** | Governance authority | Full — ALEX decisions are final |
| **ACM Manifests** | Configuration authority | Full — ACM defines capability |
| **Authenticated requests** | Conditional | Trusted for identity, not intent |
| **Model outputs** | Conditional | Governed by ACM, not trusted for correctness |
| **Human operators** | Conditional | Governed by ACM, trusted for authorization |
| **External systems** | Untrusted | All inputs validated; no implicit trust |

### 5.2 Trust Boundary Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         TRUSTED ZONE                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │    ALEX     │    │     ACM     │    │   Checklist │         │
│   │  (GID-08)   │    │  Manifests  │    │    Rules    │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
└──────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │     GATEWAY       │
                    │   (Chokepoint)    │
                    └─────────┬─────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                      CONDITIONAL TRUST ZONE                      │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │   Agents    │    │   Models    │    │   Humans    │         │
│   │ (GID-01-11) │    │   (LLMs)    │    │ (Operators) │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                  │
│   Trust = ACM capability check passed                            │
│   Distrust = Intent correctness, business logic                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                        UNTRUSTED ZONE                            │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │  External   │    │   Network   │    │  Malicious  │         │
│   │   Systems   │    │   Traffic   │    │   Inputs    │         │
│   └─────────────┘    └─────────────┘    └─────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Failure Containment Guarantees

### 6.1 Fail-Closed Guarantees

| Failure Mode | Containment | Evidence |
|--------------|-------------|----------|
| Missing PDO | Execution blocked | `PDOGateError` raised |
| Invalid envelope | Execution blocked | `ToolExecutionDenied` raised |
| Unknown agent | Evaluation denied | `UNKNOWN_AGENT` denial code |
| Missing checklist | Boot refused | `ChecklistNotFoundError` |
| Missing ACM | Evaluation denied | `ACM_NOT_LOADED` denial code |

### 6.2 Audit Trail Guarantees

| Event | Audit Guarantee | Evidence |
|-------|-----------------|----------|
| Every evaluation | Logged before return | `GovernanceAuditLogger.log_decision()` |
| Every denial | Logged with denial code | Denial record in audit log |
| Every tool execution | Telemetry emitted | `emit_tool_execution()` |
| Every governance event | Event ID generated | `governance_event_id` in context |

### 6.3 Blast Radius Containment

| Failure | Blast Radius | Containment Mechanism |
|---------|--------------|------------------------|
| Single intent failure | Single request | Exception raised; no cascade |
| ACM evaluation failure | Single agent | Other agents unaffected |
| Envelope corruption | Single envelope | Other envelopes unaffected |
| Checklist failure | System boot | System refuses to start |

---

## 7. Containment Non-Guarantees

### 7.1 What Gateway Cannot Contain

| Failure | Why Not Contained | Implication |
|---------|-------------------|-------------|
| Infrastructure failure | Out of scope | Gateway unavailable |
| Dependency failure | Out of scope | Gateway may fail unpredictably |
| Memory corruption | Out of scope | Undefined behavior |
| Disk failure | Out of scope | Audit trail may be lost |

### 7.2 Cascading Failure Scenarios

| Scenario | Gateway Behavior | Mitigation |
|----------|------------------|------------|
| ALEX unavailable | All evaluations fail | External health monitoring |
| ACM files corrupted | Boot fails | File integrity monitoring |
| Audit storage full | Audit writes fail | Storage alerting |

---

## 8. Mitigation Claims (Explicit Limits)

### 8.1 What Gateway Mitigates

| Threat | Mitigation | Limitation |
|--------|------------|------------|
| Unauthorized execution | PDO Gate enforcement | Authorized users can still execute |
| Scope creep | ACM capability enforcement | ACM scope defines boundary |
| Governance bypass | Chokepoint enforcement | Infrastructure bypass not covered |
| Audit gap | Mandatory logging | Storage/retention not covered |

### 8.2 What Gateway Does NOT Mitigate

| Threat | Why Not Mitigated | Alternative |
|--------|-------------------|-------------|
| Zero-day attacks | Unknown threat class | Defense-in-depth |
| Novel attack vectors | Not in threat model | Continuous threat modeling |
| Physical access | Out of scope | Physical security |
| Social engineering | Human factor | Security awareness |

---

## 9. Threat Boundary Summary

| Category | Defended | Not Defended |
|----------|----------|--------------|
| Authorization | ✓ | |
| Governance Bypass | ✓ | |
| Domain Boundary | ✓ | |
| State Manipulation | ✓ | |
| Infrastructure | | ✗ |
| Credentials | | ✗ |
| Application Logic | | ✗ |
| Social Engineering | | ✗ |
| Supply Chain | | ✗ |

---

## 10. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **SAM (Security)** for threat model updates

All changes require:
- PAC with explicit rationale
- Security review for threat boundary changes
- Cross-reference to TRUST_NON_CLAIMS.md

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
