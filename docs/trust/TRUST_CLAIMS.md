# ChainBridge Trust Claims

**Document:** TRUST_CLAIMS.md
**Version:** 1.0.0
**Owner:** ALEX (GID-08), Governance & Alignment Engine
**PAC:** PAC-ALEX-03 — Trust Claims & Non-Claims Canonicalization
**Last Updated:** 2025-12-17

---

## Purpose

This document enumerates exactly what ChainBridge claims to do, with traceability to tests or artifacts.

**Every claim in this document is test-backed.** No opinions. No speculation. No marketing.

---

## 1. Identity Claims

### TC-ID-01: Agent Identity Validation

**Claim:** ChainBridge validates agent identity before processing requests.

| Aspect | Detail |
|--------|--------|
| Mechanism | GID format validation, ACM manifest lookup |
| Failure Behavior | Request denied with `GID_PARSE_FAILED` or `UNKNOWN_AGENT` |
| Evidence | `tests/governance/gameday/test_gameday_forged_gid.py` (13 tests) |

### TC-ID-02: Unknown Agent Rejection

**Claim:** Requests from unregistered agents are rejected.

| Aspect | Detail |
|--------|--------|
| Mechanism | ACM evaluator checks agent registry |
| Failure Behavior | `DECISION_DENIED` event emitted, no state mutation |
| Evidence | `tests/governance/test_acm_evaluator.py` (24 tests) |

---

## 2. Authorization Claims

### TC-AUTH-01: Verb-Based Authorization

**Claim:** Agent actions are authorized against their declared capability manifest.

| Aspect | Detail |
|--------|--------|
| Mechanism | ACM manifest defines allowed verbs per agent |
| Failure Behavior | Unauthorized verb → denial, no execution |
| Evidence | `tests/governance/test_acm_evaluator.py`, `tests/governance/test_chain_of_command.py` |

### TC-AUTH-02: Forbidden Verb Enforcement

**Claim:** Certain verbs are explicitly forbidden for specific agents.

| Aspect | Detail |
|--------|--------|
| Mechanism | DIGGY_FORBIDDEN_VERBS = {EXECUTE, BLOCK, APPROVE} |
| Failure Behavior | `VerbNotPermittedError`, denial registered |
| Evidence | `tests/governance/gameday/test_gameday_diggi_forbidden_verb.py` (21 tests) |

### TC-AUTH-03: DRCP Escalation Routing

**Claim:** Denied requests are routed through the Denial Routing and Correction Protocol.

| Aspect | Detail |
|--------|--------|
| Mechanism | DRCP routes denials to correction pathways |
| Failure Behavior | Structured escalation with audit trail |
| Evidence | `tests/governance/test_drcp.py` (23 tests) |

---

## 3. Execution Binding Claims

### TC-EXEC-01: Tool Execution Requires Authorization

**Claim:** Tools execute only when explicitly authorized by a decision envelope.

| Aspect | Detail |
|--------|--------|
| Mechanism | Envelope validation before tool invocation |
| Failure Behavior | Missing/invalid envelope → `TOOL_EXECUTION_DENIED` |
| Evidence | `tests/governance/gameday/test_gameday_tool_without_envelope.py` (19 tests) |

### TC-EXEC-02: Fail-Closed Execution

**Claim:** On any authorization failure, execution is blocked rather than permitted.

| Aspect | Detail |
|--------|--------|
| Mechanism | Default-deny policy in all authorization paths |
| Failure Behavior | Exception raised, no side effects |
| Evidence | All gameday tests (109 tests total validate fail-closed) |

---

## 4. Integrity Claims

### TC-INT-01: Artifact Integrity Verification

**Claim:** Governed artifacts are hash-verified at boot.

| Aspect | Detail |
|--------|--------|
| Mechanism | SHA-256 hash comparison against manifest |
| Failure Behavior | Mismatch → `ArtifactIntegrityError`, boot blocked |
| Evidence | `tests/governance/gameday/test_gameday_artifact_mismatch.py` (14 tests) |

### TC-INT-02: Governance Fingerprint at Boot

**Claim:** Governance configuration is fingerprinted at startup.

| Aspect | Detail |
|--------|--------|
| Mechanism | Composite hash of governance root files |
| Failure Behavior | Missing files → `GovernanceBootError` |
| Evidence | `tests/governance/test_governance_fingerprint.py` (23 tests) |

### TC-INT-03: Governance Drift Detection

**Claim:** Runtime modification of governance files is detected.

| Aspect | Detail |
|--------|--------|
| Mechanism | Fingerprint recomputation on verification call |
| Failure Behavior | Mismatch → `GovernanceDriftError`, operation blocked |
| Evidence | `tests/governance/gameday/test_gameday_governance_drift.py` (12 tests) |

---

## 5. Scope Claims

### TC-SCOPE-01: Repository Scope Enforcement

**Claim:** Agents cannot access paths outside their declared scope.

| Aspect | Detail |
|--------|--------|
| Mechanism | Pattern matching against REPO_SCOPE_MANIFEST |
| Failure Behavior | Out-of-scope access → `ScopeViolationError` |
| Evidence | `tests/governance/gameday/test_gameday_scope_violation.py` (30 tests) |

### TC-SCOPE-02: Forbidden File Patterns

**Claim:** Files matching forbidden patterns are blocked.

| Aspect | Detail |
|--------|--------|
| Mechanism | Pattern blocklist: `*bot*.py`, `*trading*.py`, `*.backup`, `.env` |
| Failure Behavior | `SCOPE_VIOLATION` event, CI blocks merge |
| Evidence | `tests/governance/test_atlas_scope.py` (28 tests) |

---

## 6. Audit Claims

### TC-AUDIT-01: Event Emission on Governance Decisions

**Claim:** Every governance decision emits a structured event.

| Aspect | Detail |
|--------|--------|
| Mechanism | GovernanceEventEmitter with typed events |
| Failure Behavior | Event emission fails open (decision still logged) |
| Evidence | `tests/governance/test_governance_events.py` (42 tests) |

### TC-AUDIT-02: Audit Bundle Generation

**Claim:** Audit bundles can be generated for offline verification.

| Aspect | Detail |
|--------|--------|
| Mechanism | Bundle export with hash manifest |
| Failure Behavior | Export fails with explicit error |
| Evidence | `tests/governance/test_audit_export.py` (32 tests) |

### TC-AUDIT-03: Event Retention

**Claim:** Governance events are retained for audit periods.

| Aspect | Detail |
|--------|--------|
| Mechanism | Sink-based retention with configurable backends |
| Failure Behavior | Retention failure does not block operations |
| Evidence | `tests/governance/test_event_retention.py` (39 tests) |

---

## 7. Correction Claims

### TC-CORR-01: Diggi Correction Routing

**Claim:** Invalid requests can be routed to correction pathways.

| Aspect | Detail |
|--------|--------|
| Mechanism | Diggi envelope handler with correction templates |
| Failure Behavior | Correction fails → original denial stands |
| Evidence | `tests/governance/test_diggi_corrections.py` (28 tests), `tests/governance/test_diggi_envelope_handler.py` (30 tests) |

---

## Claim Summary

| Category | Claims | Total Tests |
|----------|--------|-------------|
| Identity | 2 | 37 |
| Authorization | 3 | 68 |
| Execution Binding | 2 | 128 |
| Integrity | 3 | 49 |
| Scope | 2 | 58 |
| Audit | 3 | 113 |
| Correction | 1 | 58 |
| **Total** | **16** | **511+** |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-17 | ALEX (GID-08) | Initial canonical claims |

---

**CANONICAL REFERENCE** — This document is the authoritative source for ChainBridge trust claims.
All UI copy, sales materials, and security questionnaires must reference this document.
