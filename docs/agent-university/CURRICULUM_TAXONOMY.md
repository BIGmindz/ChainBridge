# CURRICULUM_TAXONOMY.md
## Agent University — Curriculum Tag Taxonomy v1

| Field | Value |
|-------|-------|
| **Taxonomy Version** | 1.0.0 |
| **Status** | LOCKED |
| **Authority** | ALEX (GID-08) — Governance & Alignment Engine |
| **Effective Date** | 2025-12-22 |

---

## 1. PURPOSE

This document defines the canonical taxonomy for curriculum tags used in Training Signal Blocks (TSBs). Consistent tagging enables:

- **Aggregation** — Group related training signals
- **Search** — Find training by competency
- **Gap Analysis** — Identify missing curriculum areas
- **Agent Profiles** — Track what each agent has learned

---

## 2. TAG FORMAT

### 2.1 Structure

```
AGENT-U / {DOMAIN} / {SUBDOMAIN} / {TOPIC} / {LEVEL}
```

### 2.2 Rules

| Rule | Specification |
|------|---------------|
| Separator | ` / ` (space-slash-space) |
| Case | UPPER-KEBAB-CASE |
| Prefix | Always starts with `AGENT-U` |
| Depth | Minimum 3 levels, maximum 5 levels |
| Level Suffix | Must end with `L0`, `L1`, or `L2` |

### 2.3 Examples

```
AGENT-U / GOVERNANCE / TRAINING-SIGNALS / DRIFT-CONTROL / L2
AGENT-U / EXECUTION / API-INTEGRATION / HEDERA / L1
AGENT-U / SECURITY / PDO-ENFORCEMENT / SIGNATURE-VALIDATION / L2
AGENT-U / EXPERIMENTAL / AUCTION-MECHANICS / DUTCH-ENGINE / L0
```

---

## 3. DOMAIN TAXONOMY

### 3.1 Top-Level Domains

| Domain | Code | Description |
|--------|------|-------------|
| **Governance** | `GOVERNANCE` | Rules, enforcement, compliance, process |
| **Execution** | `EXECUTION` | Implementation, integration, delivery |
| **Security** | `SECURITY` | PDO, signing, access control, validation |
| **Architecture** | `ARCHITECTURE` | System design, patterns, structure |
| **Testing** | `TESTING` | Verification, validation, QA |
| **Documentation** | `DOCUMENTATION` | Specs, contracts, knowledge capture |
| **Experimental** | `EXPERIMENTAL` | Spikes, prototypes, research |
| **Operations** | `OPERATIONS` | Deployment, monitoring, infrastructure |

---

### 3.2 Subdomain Breakdown

#### GOVERNANCE

| Subdomain | Topics |
|-----------|--------|
| `TRAINING-SIGNALS` | `DRIFT-CONTROL`, `CURRICULUM-DESIGN`, `SIGNAL-EXTRACTION` |
| `PAC-COMPLIANCE` | `VALIDATION`, `REJECTION`, `RE-ISSUANCE` |
| `AGENT-ALIGNMENT` | `ROLE-DEFINITION`, `BOUNDARY-ENFORCEMENT`, `HANDOFF-PROTOCOL` |
| `PRECEDENT` | `LOCKING`, `OVERRIDE`, `AUDIT` |

#### EXECUTION

| Subdomain | Topics |
|-----------|--------|
| `API-INTEGRATION` | `HEDERA`, `SXT`, `EXTERNAL-SERVICES` |
| `DATA-PROCESSING` | `PARSING`, `TRANSFORMATION`, `VALIDATION` |
| `UI-IMPLEMENTATION` | `COMPONENTS`, `STATE-MANAGEMENT`, `ROUTING` |
| `SERVICE-LAYER` | `BUSINESS-LOGIC`, `ORCHESTRATION`, `ERROR-HANDLING` |

#### SECURITY

| Subdomain | Topics |
|-----------|--------|
| `PDO-ENFORCEMENT` | `SIGNATURE-VALIDATION`, `AUTHORITY-CHECK`, `MULTI-SIG` |
| `ACCESS-CONTROL` | `AUTHENTICATION`, `AUTHORIZATION`, `RBAC` |
| `CRYPTOGRAPHY` | `HASHING`, `SIGNING`, `KEY-MANAGEMENT` |
| `AUDIT` | `LOGGING`, `TRAIL`, `FORENSICS` |

#### ARCHITECTURE

| Subdomain | Topics |
|-----------|--------|
| `SYSTEM-DESIGN` | `LAYERING`, `BOUNDARIES`, `INTERFACES` |
| `PATTERNS` | `EVENT-DRIVEN`, `CQRS`, `MICROSERVICES` |
| `DATA-MODEL` | `SCHEMA`, `RELATIONSHIPS`, `MIGRATIONS` |

#### TESTING

| Subdomain | Topics |
|-----------|--------|
| `UNIT-TESTING` | `ISOLATION`, `MOCKING`, `ASSERTIONS` |
| `INTEGRATION-TESTING` | `E2E`, `CONTRACT`, `SMOKE` |
| `VALIDATION` | `SCHEMA`, `BOUNDARY`, `REGRESSION` |

#### DOCUMENTATION

| Subdomain | Topics |
|-----------|--------|
| `SPECIFICATIONS` | `API-SPEC`, `DATA-SPEC`, `PROTOCOL-SPEC` |
| `CONTRACTS` | `REPO-CONTRACT`, `INTERFACE-CONTRACT`, `SLA` |
| `KNOWLEDGE` | `RUNBOOKS`, `DECISION-LOGS`, `ARCHITECTURE-DOCS` |

#### EXPERIMENTAL

| Subdomain | Topics |
|-----------|--------|
| `PROTOTYPES` | `POC`, `SPIKE`, `FEASIBILITY` |
| `RESEARCH` | `ANALYSIS`, `BENCHMARKING`, `EXPLORATION` |
| `AUCTION-MECHANICS` | `DUTCH-ENGINE`, `PRICING`, `SETTLEMENT` |

#### OPERATIONS

| Subdomain | Topics |
|-----------|--------|
| `DEPLOYMENT` | `CI-CD`, `CONTAINERIZATION`, `RELEASE` |
| `MONITORING` | `METRICS`, `ALERTING`, `LOGGING` |
| `INFRASTRUCTURE` | `K8S`, `DOCKER`, `CLOUD` |

---

## 4. AGENT-SPECIFIC TAGS

### 4.1 Agent Role Tags

| Agent | GID | Primary Domains |
|-------|-----|-----------------|
| **ALEX** | 08 | `GOVERNANCE`, `ARCHITECTURE` |
| **Atlas** | 01 | `EXECUTION`, `ARCHITECTURE` |
| **Sonny** | 02 | `EXECUTION`, `API-INTEGRATION` |
| **Cody** | 03 | `EXECUTION`, `TESTING` |
| **Sam** | 04 | `SECURITY`, `PDO-ENFORCEMENT` |
| **Dan** | 05 | `DOCUMENTATION`, `SPECIFICATIONS` |
| **Ruby** | TBD | `UI-IMPLEMENTATION`, `EXECUTION` |
| **Tina** | TBD | `TESTING`, `VALIDATION` |

### 4.2 Cross-Agent Tags

For training that applies to multiple agents:

```
AGENT-U / CROSS-AGENT / {TOPIC} / {LEVEL}
```

Examples:
```
AGENT-U / CROSS-AGENT / PAC-STRUCTURE / L1
AGENT-U / CROSS-AGENT / HANDOFF-PROTOCOL / L2
AGENT-U / CROSS-AGENT / ERROR-RECOVERY / L1
```

---

## 5. TAG VALIDATION

### 5.1 Valid Tag Checklist

```
✔ Starts with AGENT-U
✔ Uses UPPER-KEBAB-CASE
✔ Minimum 3 segments
✔ Maximum 5 segments
✔ Ends with L0, L1, or L2
✔ Domain exists in taxonomy
✔ Subdomain exists under domain
```

### 5.2 Invalid Tag Examples

| Invalid Tag | Reason |
|-------------|--------|
| `GOVERNANCE / TRAINING / L1` | Missing `AGENT-U` prefix |
| `AGENT-U / governance / training / L1` | Not UPPER-KEBAB-CASE |
| `AGENT-U / GOVERNANCE` | Missing level suffix |
| `AGENT-U / GOVERNANCE / L1` | Too shallow (need subdomain) |
| `AGENT-U / UNKNOWN / TOPIC / L1` | Domain not in taxonomy |

### 5.3 Validation Regex

```regex
^AGENT-U\s*\/\s*[A-Z][A-Z0-9-]*(\s*\/\s*[A-Z][A-Z0-9-]*){1,3}\s*\/\s*L[012]$
```

---

## 6. EXTENDING THE TAXONOMY

### 6.1 Adding New Domains

Requires governance PAC with:
- Justification for new domain
- At least 3 subdomains defined
- No overlap with existing domains

### 6.2 Adding New Subdomains/Topics

May be added by any agent if:
- Parent domain exists
- No duplicate naming
- Documented in PAC TSB first use

### 6.3 Deprecation

Tags are never deleted, only deprecated:
```
AGENT-U / DEPRECATED / {OLD-TAG} / {LEVEL}
```

---

## 7. VERSIONING

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2025-12-22 | Initial taxonomy — LOCKED |

---

## 8. QUICK REFERENCE — COMMON TAGS

```
# Governance
AGENT-U / GOVERNANCE / TRAINING-SIGNALS / DRIFT-CONTROL / L2
AGENT-U / GOVERNANCE / PAC-COMPLIANCE / VALIDATION / L2
AGENT-U / GOVERNANCE / AGENT-ALIGNMENT / ROLE-DEFINITION / L2

# Execution
AGENT-U / EXECUTION / API-INTEGRATION / HEDERA / L1
AGENT-U / EXECUTION / SERVICE-LAYER / BUSINESS-LOGIC / L1
AGENT-U / EXECUTION / UI-IMPLEMENTATION / COMPONENTS / L1

# Security
AGENT-U / SECURITY / PDO-ENFORCEMENT / SIGNATURE-VALIDATION / L2
AGENT-U / SECURITY / ACCESS-CONTROL / AUTHORIZATION / L2

# Testing
AGENT-U / TESTING / UNIT-TESTING / ISOLATION / L1
AGENT-U / TESTING / INTEGRATION-TESTING / E2E / L1

# Cross-Agent
AGENT-U / CROSS-AGENT / PAC-STRUCTURE / L1
AGENT-U / CROSS-AGENT / HANDOFF-PROTOCOL / L2
```

---

*Taxonomy Authority: ALEX (GID-08) — Governance & Alignment Engine*
*Status: LOCKED — Extensions allowed per Section 6 rules*
