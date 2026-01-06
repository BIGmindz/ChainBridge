# Regulator Claim Registry

**PAC Reference:** PAC-JEFFREY-P45  
**Classification:** AUDIT-GRADE / READ-ONLY  
**Governance Mode:** HARD / FAIL-CLOSED  
**Enforcement Agent:** ALEX (GID-08)  
**Version:** 1.0.0  
**Date:** 2026-01-02

---

## 1. Overview

This registry defines **permitted and forbidden claims** when communicating with regulators, auditors, and compliance bodies about ChainBridge's capabilities, certifications, and operational status.

### Core Principle

> **Audit access must be cheaper than compliance.**

We provide complete transparency to observers. We make zero claims we cannot prove.

---

## 2. Forbidden Claims (HARD BLOCK)

These claims are **ABSOLUTELY FORBIDDEN** in any regulator-facing communication.

### 2.1 Certification Claims

| ID | Forbidden Claim | Reason | Violation Level |
|----|-----------------|--------|-----------------|
| FC-REG-001 | "ChainBridge is SOC2 certified" | No certification obtained | CRITICAL |
| FC-REG-002 | "ChainBridge is ISO 27001 certified" | No certification obtained | CRITICAL |
| FC-REG-003 | "ChainBridge is PCI-DSS compliant" | No certification obtained | CRITICAL |
| FC-REG-004 | "ChainBridge has passed regulatory audit" | No formal audit completed | CRITICAL |
| FC-REG-005 | "ChainBridge is auditor-approved" | No approval obtained | CRITICAL |

### 2.2 Authority Claims

| ID | Forbidden Claim | Reason | Violation Level |
|----|-----------------|--------|-----------------|
| FC-REG-006 | "ChainBridge makes compliance decisions" | No decision authority | CRITICAL |
| FC-REG-007 | "ChainBridge replaces compliance officers" | Human oversight required | CRITICAL |
| FC-REG-008 | "ChainBridge provides legal opinions" | Not a legal service | CRITICAL |
| FC-REG-009 | "ChainBridge ensures regulatory compliance" | Cannot guarantee | HIGH |
| FC-REG-010 | "ChainBridge eliminates compliance risk" | Risk cannot be eliminated | HIGH |

### 2.3 Autonomy Claims

| ID | Forbidden Claim | Reason | Violation Level |
|----|-----------------|--------|-----------------|
| FC-REG-011 | "ChainBridge operates autonomously" | Human oversight required | CRITICAL |
| FC-REG-012 | "ChainBridge makes independent decisions" | Agents are advisory | HIGH |
| FC-REG-013 | "AI agents have decision authority" | No autonomous authority | CRITICAL |
| FC-REG-014 | "ChainBridge auto-approves transactions" | Human approval required | CRITICAL |
| FC-REG-015 | "No human intervention required" | Always required | CRITICAL |

### 2.4 Production Claims

| ID | Forbidden Claim | Reason | Violation Level |
|----|-----------------|--------|-----------------|
| FC-REG-016 | "ChainBridge is production-ready" | Currently pilot phase | HIGH |
| FC-REG-017 | "ChainBridge processes real transactions" | Shadow data only | CRITICAL |
| FC-REG-018 | "ChainBridge handles real money" | No settlement authority | CRITICAL |
| FC-REG-019 | "ChainBridge is in production use" | Pilot only | HIGH |
| FC-REG-020 | "ChainBridge has production customers" | No production deployment | HIGH |

### 2.5 Data Claims

| ID | Forbidden Claim | Reason | Violation Level |
|----|-----------------|--------|-----------------|
| FC-REG-021 | "Observer data is production data" | SHADOW classification only | CRITICAL |
| FC-REG-022 | "Data shown represents real transactions" | Synthetic/test data | CRITICAL |
| FC-REG-023 | "All data is visible to observers" | Production data hidden | HIGH |
| FC-REG-024 | "No data is masked or redacted" | PII is sanitized | HIGH |

---

## 3. Required Disclaimers

These disclaimers **MUST** accompany any regulator-facing communication.

### 3.1 Platform Status Disclaimer

```
PLATFORM STATUS DISCLAIMER

ChainBridge is currently operating in PILOT MODE.

- This is NOT a production system
- Data shown is SHADOW/TEST classification only
- No real financial transactions are processed
- No settlement authority is claimed
- All decisions require human operator approval

ChainBridge is an operator assistance platform, not a decision-making authority.
```

### 3.2 Certification Disclaimer

```
CERTIFICATION DISCLAIMER

ChainBridge has NOT obtained the following certifications:
- SOC2 Type I or Type II
- ISO 27001
- PCI-DSS
- Any regulatory certification

ChainBridge is designed WITH REFERENCE TO these standards but makes
no claim of compliance or certification.
```

### 3.3 Observer Access Disclaimer

```
OBSERVER ACCESS DISCLAIMER

Observer access provides READ-ONLY visibility into ChainBridge operations.

- Observers have NO write capability
- Observers have NO control capability
- Observers have NO decision authority
- Observers view SHADOW data only
- All observer actions are logged

Observer access does not constitute endorsement, approval, or certification.
```

### 3.4 AI/Agent Disclaimer

```
AI/AGENT DISCLAIMER

ChainBridge utilizes AI agents for ADVISORY purposes only.

- Agents do NOT have autonomous decision authority
- Agents do NOT execute without human oversight
- Agents do NOT replace compliance personnel
- All agent outputs require human verification
- Kill-switch allows immediate agent halt

Human operators retain full control and accountability.
```

---

## 4. Permitted Claims

These claims ARE permitted when supported by evidence.

### 4.1 Transparency Claims

| ID | Permitted Claim | Evidence Required |
|----|-----------------|-------------------|
| PC-REG-001 | "ChainBridge provides audit trail visibility" | Observer access demo |
| PC-REG-002 | "ChainBridge logs all decisions" | Audit log export |
| PC-REG-003 | "ChainBridge generates proof artifacts" | ProofPack verification |
| PC-REG-004 | "ChainBridge supports read-only observer access" | Observer session |
| PC-REG-005 | "ChainBridge implements kill-switch controls" | Kill-switch validation |

### 4.2 Design Claims

| ID | Permitted Claim | Evidence Required |
|----|-----------------|-------------------|
| PC-REG-006 | "ChainBridge is designed with SOC2 principles" | Design documentation |
| PC-REG-007 | "ChainBridge implements role-based access" | Permission lattice |
| PC-REG-008 | "ChainBridge provides hash verification" | Verification demo |
| PC-REG-009 | "ChainBridge supports audit exports" | Export functionality |
| PC-REG-010 | "ChainBridge implements rate limiting" | Rate limit config |

### 4.3 Operational Claims

| ID | Permitted Claim | Evidence Required |
|----|-----------------|-------------------|
| PC-REG-011 | "ChainBridge is in pilot testing" | Pilot status docs |
| PC-REG-012 | "ChainBridge uses test/shadow data" | Data classification |
| PC-REG-013 | "ChainBridge requires human approval" | Workflow documentation |
| PC-REG-014 | "ChainBridge can be halted by operators" | Kill-switch demo |
| PC-REG-015 | "ChainBridge agents are advisory" | Agent governance docs |

---

## 5. Communication Templates

### 5.1 Initial Regulator Introduction

```
Subject: ChainBridge Platform - Pilot Observation Access

Dear [Regulator Name],

We are pleased to offer READ-ONLY observer access to the ChainBridge 
operator assistance platform for evaluation purposes.

KEY POINTS:
- ChainBridge is currently in PILOT PHASE
- Observer access is READ-ONLY with no control capability
- All data visible is SHADOW/TEST classification
- No production transactions are processed
- Human operators retain full decision authority

DISCLAIMERS:
[Include all required disclaimers from Section 3]

We welcome the opportunity to demonstrate our transparency and 
audit capabilities. Please note this access does not constitute 
any form of certification or approval.

[Signature]
```

### 5.2 Capability Overview

```
Subject: ChainBridge Capability Overview for Regulatory Review

WHAT CHAINBRIDGE IS:
- An operator assistance platform
- A decision support system
- An audit trail generator
- A proofpack creator

WHAT CHAINBRIDGE IS NOT:
- An autonomous decision system
- A certified compliance platform
- A production settlement system
- A replacement for compliance officers

CURRENT STATUS: PILOT PHASE
DATA CLASSIFICATION: SHADOW/TEST ONLY
OBSERVER ACCESS: READ-ONLY

[Include all required disclaimers]
```

### 5.3 Response to Compliance Inquiry

```
Subject: RE: ChainBridge Compliance Status

Thank you for your inquiry regarding ChainBridge's compliance status.

CERTIFICATION STATUS:
ChainBridge has NOT obtained SOC2, ISO 27001, PCI-DSS, or any 
regulatory certification.

DESIGN PHILOSOPHY:
ChainBridge is designed WITH REFERENCE TO industry security standards 
but makes no claim of compliance or certification.

AUDIT ACCESS:
We offer read-only observer access for your evaluation. This access:
- Is limited to SHADOW/TEST data
- Provides no control capability
- Does not constitute certification
- Includes full audit logging of your actions

[Include all required disclaimers]
```

---

## 6. Claim Verification Process

### 6.1 Pre-Communication Review

Before any regulator communication:

1. **ALEX Review** — All claims checked against forbidden list
2. **Evidence Link** — All permitted claims linked to proof
3. **Disclaimer Check** — All required disclaimers included
4. **Approval Gate** — Human approval required

### 6.2 Forbidden Claim Detection

```python
FORBIDDEN_REGULATOR_CLAIMS = [
    r"SOC\s*2\s*(type\s*[12])?\s*certified",
    r"ISO\s*27001\s*certified",
    r"PCI[\-\s]*DSS\s*(compliant|certified)",
    r"regulatory\s*(audit|approval)\s*(passed|obtained)",
    r"auditor[\-\s]*(approved|certified)",
    r"compliance\s*decisions?",
    r"replaces?\s*compliance\s*(officer|team)",
    r"legal\s*opinions?",
    r"ensures?\s*regulatory\s*compliance",
    r"eliminates?\s*compliance\s*risk",
    r"operat(es?|ing)\s*autonomous",
    r"independent\s*decisions?",
    r"AI\s*(agents?)?\s*(have|has)\s*(decision)?\s*authority",
    r"auto[\-\s]?approv",
    r"no\s*human\s*intervention",
    r"production[\-\s]?ready",
    r"(processes?|handles?)\s*real\s*(transactions?|money)",
    r"production\s*(use|customers?|deployment)",
]
```

### 6.3 Violation Response

| Violation Level | Response |
|-----------------|----------|
| CRITICAL | Immediate halt, escalation to CTO |
| HIGH | Communication blocked pending review |
| MEDIUM | Warning issued, modification required |
| LOW | Advisory logged |

---

## 7. Evidence Requirements

### 7.1 Evidence Types

| Claim Type | Evidence Required |
|------------|-------------------|
| Capability claim | Live demonstration |
| Design claim | Documentation + code |
| Operational claim | Audit logs |
| Status claim | Official records |

### 7.2 Evidence Retention

- All regulator communications: 7 years
- Supporting evidence: 7 years
- Observer session logs: 7 years
- Claim verifications: 7 years

---

## 8. Governance Invariants

### INV-REG-001: No False Certification Claims
Zero certification claims without certification evidence.

### INV-REG-002: No Authority Claims
Zero claims of autonomous decision authority.

### INV-REG-003: No Production Claims
Zero claims of production status during pilot phase.

### INV-REG-004: Disclaimer Presence
All required disclaimers present in regulator communications.

### INV-REG-005: ALEX Enforcement
All claims verified by ALEX before transmission.

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-02 | BENSON/ALEX | Initial regulator claim registry |

---

**Document Authority:** PAC-JEFFREY-P45  
**Enforcement Agent:** ALEX (GID-08)  
**Classification:** AUDIT-GRADE  
**Governance:** HARD / FAIL-CLOSED
