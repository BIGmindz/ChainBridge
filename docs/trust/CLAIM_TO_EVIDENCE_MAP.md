# Claim-to-Evidence Map

**Document:** CLAIM_TO_EVIDENCE_MAP.md
**Version:** 1.0.0
**Owner:** ALEX (GID-08), Governance & Alignment Engine
**PAC:** PAC-ALEX-03 — Trust Claims & Non-Claims Canonicalization
**Last Updated:** 2025-12-17

---

## Purpose

This document provides explicit traceability from every claim to its supporting evidence.

**Rule:** If a claim cannot map to a test or artifact, it is not a valid claim.

---

## Evidence Categories

| Type | Description | Verification |
|------|-------------|--------------|
| **Test** | Automated test in `tests/` directory | `pytest -v <path>` |
| **Artifact** | Generated file with hash | `sha256sum <file>` |
| **Schema** | Type definition or validation schema | Code inspection |
| **Module** | Source code implementation | Code inspection |

---

## Identity Claims → Evidence

### TC-ID-01: Agent Identity Validation

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_forged_gid.py` | `pytest tests/governance/gameday/test_gameday_forged_gid.py -v` |
| Unit Test | `tests/governance/test_acm_evaluator.py` | `pytest tests/governance/test_acm_evaluator.py -v` |
| Module | `core/governance/acm_evaluator.py` | Code inspection |
| Schema | `core/governance/intent_schema.py::GID_PATTERN` | Regex: `^GID-\d{2}$` |

**Test Count:** 37 tests
**Last Verified:** 2025-12-17

### TC-ID-02: Unknown Agent Rejection

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_forged_gid.py::TestUnknownGIDRejection` | `pytest -k "TestUnknownGIDRejection" -v` |
| Unit Test | `tests/governance/test_acm_loader.py` | `pytest tests/governance/test_acm_loader.py -v` |
| Module | `core/governance/acm_loader.py` | Code inspection |

**Test Count:** 30 tests
**Last Verified:** 2025-12-17

---

## Authorization Claims → Evidence

### TC-AUTH-01: Verb-Based Authorization

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_acm_evaluator.py` | `pytest tests/governance/test_acm_evaluator.py -v` |
| Unit Test | `tests/governance/test_chain_of_command.py` | `pytest tests/governance/test_chain_of_command.py -v` |
| Module | `core/governance/acm_evaluator.py` | Code inspection |
| Schema | `manifests/*.yaml` | ACM manifest files |

**Test Count:** 35 tests
**Last Verified:** 2025-12-17

### TC-AUTH-02: Forbidden Verb Enforcement

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_diggi_forbidden_verb.py` | `pytest tests/governance/gameday/test_gameday_diggi_forbidden_verb.py -v` |
| Unit Test | `tests/governance/test_diggi_corrections.py` | `pytest tests/governance/test_diggi_corrections.py -v` |
| Module | `core/governance/diggi_corrections.py` | Code inspection |
| Constant | `DIGGY_FORBIDDEN_VERBS = {"EXECUTE", "BLOCK", "APPROVE"}` | Code inspection |

**Test Count:** 49 tests
**Last Verified:** 2025-12-17

### TC-AUTH-03: DRCP Escalation Routing

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_drcp.py` | `pytest tests/governance/test_drcp.py -v` |
| Module | `core/governance/drcp.py` | Code inspection |

**Test Count:** 23 tests
**Last Verified:** 2025-12-17

---

## Execution Binding Claims → Evidence

### TC-EXEC-01: Tool Execution Requires Authorization

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_tool_without_envelope.py` | `pytest tests/governance/gameday/test_gameday_tool_without_envelope.py -v` |
| Unit Test | `tests/governance/test_diggi_envelope_handler.py` | `pytest tests/governance/test_diggi_envelope_handler.py -v` |
| Module | `core/governance/diggi_envelope_handler.py` | Code inspection |

**Test Count:** 49 tests
**Last Verified:** 2025-12-17

### TC-EXEC-02: Fail-Closed Execution

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Suite | `tests/governance/gameday/` | `pytest tests/governance/gameday/ -v` |
| Unit Test | `tests/governance/test_boot_checks.py` | `pytest tests/governance/test_boot_checks.py -v` |

**Test Count:** 109+ tests (all gameday tests validate fail-closed)
**Last Verified:** 2025-12-17

---

## Integrity Claims → Evidence

### TC-INT-01: Artifact Integrity Verification

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_artifact_mismatch.py` | `pytest tests/governance/gameday/test_gameday_artifact_mismatch.py -v` |
| Module | `scripts/ci/artifact_verifier.py` | Code inspection |
| Error Class | `ArtifactIntegrityError` | Exception raised on mismatch |

**Test Count:** 14 tests
**Last Verified:** 2025-12-17

### TC-INT-02: Governance Fingerprint at Boot

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_governance_fingerprint.py` | `pytest tests/governance/test_governance_fingerprint.py -v` |
| Unit Test | `tests/governance/test_boot_checks.py` | `pytest tests/governance/test_boot_checks.py -v` |
| Module | `core/governance/governance_fingerprint.py` | Code inspection |
| Class | `GovernanceFingerprintEngine` | Compute + verify methods |

**Test Count:** 52 tests
**Last Verified:** 2025-12-17

### TC-INT-03: Governance Drift Detection

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_governance_drift.py` | `pytest tests/governance/gameday/test_gameday_governance_drift.py -v` |
| Unit Test | `tests/governance/test_governance_fingerprint.py` | `pytest tests/governance/test_governance_fingerprint.py -v` |
| Error Class | `GovernanceDriftError` | Exception raised on drift |

**Test Count:** 35 tests
**Last Verified:** 2025-12-17

---

## Scope Claims → Evidence

### TC-SCOPE-01: Repository Scope Enforcement

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_scope_violation.py` | `pytest tests/governance/gameday/test_gameday_scope_violation.py -v` |
| Unit Test | `tests/governance/test_atlas_scope.py` | `pytest tests/governance/test_atlas_scope.py -v` |
| Module | `scripts/ci/check_repo_scope.py` | Code inspection |
| Manifest | `docs/governance/REPO_SCOPE_MANIFEST.md` | Pattern definitions |

**Test Count:** 58 tests
**Last Verified:** 2025-12-17

### TC-SCOPE-02: Forbidden File Patterns

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Gameday Test | `tests/governance/gameday/test_gameday_scope_violation.py::TestForbiddenPatterns` | `pytest -k "TestForbiddenPatterns" -v` |
| Unit Test | `tests/governance/test_atlas_scope.py` | `pytest tests/governance/test_atlas_scope.py -v` |
| Constant | `FORBIDDEN_PATTERNS` in check_repo_scope.py | Code inspection |

**Test Count:** 58 tests
**Last Verified:** 2025-12-17

---

## Audit Claims → Evidence

### TC-AUDIT-01: Event Emission on Governance Decisions

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_governance_events.py` | `pytest tests/governance/test_governance_events.py -v` |
| Module | `core/governance/events.py` | Event factory functions |
| Module | `core/governance/event_sink.py` | Emitter + sinks |
| Schema | `GovernanceEventType` enum | Event type definitions |

**Test Count:** 42 tests
**Last Verified:** 2025-12-17

### TC-AUDIT-02: Audit Bundle Generation

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_audit_export.py` | `pytest tests/governance/test_audit_export.py -v` |
| Module | `core/governance/audit_export.py` | Bundle generation |
| Artifact | `proofpacks/*.json` | Offline-verifiable bundles |

**Test Count:** 32 tests
**Last Verified:** 2025-12-17

### TC-AUDIT-03: Event Retention

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_event_retention.py` | `pytest tests/governance/test_event_retention.py -v` |
| Module | `core/governance/event_sink.py` | Retention configuration |

**Test Count:** 39 tests
**Last Verified:** 2025-12-17

---

## Correction Claims → Evidence

### TC-CORR-01: Diggi Correction Routing

| Evidence Type | Path | Verification Command |
|---------------|------|----------------------|
| Unit Test | `tests/governance/test_diggi_corrections.py` | `pytest tests/governance/test_diggi_corrections.py -v` |
| Unit Test | `tests/governance/test_diggi_envelope_handler.py` | `pytest tests/governance/test_diggi_envelope_handler.py -v` |
| Module | `core/governance/diggi_corrections.py` | Correction logic |
| Module | `core/governance/diggi_envelope_handler.py` | Envelope handling |

**Test Count:** 58 tests
**Last Verified:** 2025-12-17

---

## Evidence Summary

| Category | Claims | Test Files | Total Tests |
|----------|--------|------------|-------------|
| Identity | 2 | 3 | 37 |
| Authorization | 3 | 4 | 107 |
| Execution Binding | 2 | 3 | 158 |
| Integrity | 3 | 3 | 101 |
| Scope | 2 | 2 | 58 |
| Audit | 3 | 3 | 113 |
| Correction | 1 | 2 | 58 |

---

## Verification Commands

### Run All Evidence Tests

```bash
# Full governance test suite
pytest tests/governance/ -v

# Gameday adversarial tests only
pytest tests/governance/gameday/ -v

# Quick validation
pytest tests/governance/ -q
```

### Verify Specific Claim

```bash
# Example: Verify TC-INT-03 (Governance Drift Detection)
pytest tests/governance/gameday/test_gameday_governance_drift.py -v
pytest tests/governance/test_governance_fingerprint.py -v
```

---

## Approved Language Blocks

The following text blocks are pre-approved for external use:

### For Trust Center UI

> **Identity Control:** Every request is validated against a registered agent identity. Unknown agents are rejected.

> **Authorization Control:** Agent actions are authorized against capability manifests. Unauthorized verbs are denied.

> **Execution Binding:** Tools execute only when explicitly authorized. Missing authorization blocks execution.

> **Integrity Verification:** Governance files are hash-verified at startup. Tampering blocks boot.

> **Scope Enforcement:** Agents operate within declared boundaries. Out-of-scope access is blocked.

> **Audit Trail:** Every governance decision emits a structured event. Bundles are offline-verifiable.

### For Security Questionnaires

> ChainBridge implements governance controls at the agent intent layer. Controls include identity validation, verb-based authorization, fail-closed execution binding, artifact integrity verification, scope enforcement, and structured audit emission. All controls are test-backed. Evidence is available in the Trust Center.

### For Sales Materials

> ChainBridge enforces documented governance controls with fail-closed behavior. Every claim is test-backed. The Trust Center provides read-only evidence. No security guarantees are implied beyond documented controls.

---

## Forbidden Phrases

The following phrases must **never** appear in external communications:

| ❌ Forbidden | Reason |
|-------------|--------|
| "prevents fraud" | Over-claim — we mitigate, not prevent |
| "guarantees security" | Over-claim — no absolute guarantee |
| "secure" (standalone) | Ambiguous — must qualify |
| "best-in-class" | Marketing — not test-backed |
| "enterprise-grade" | Marketing — not test-backed |
| "military-grade" | Marketing — not test-backed |
| "hack-proof" | Over-claim — impossible |
| "bulletproof" | Over-claim — impossible |
| "zero vulnerabilities" | Over-claim — impossible |
| "complete protection" | Over-claim — coverage is documented |
| "certified secure" | False — no external certification |
| "compliant" (standalone) | Ambiguous — must specify standard |
| "AI-powered security" | Misleading — governance is rule-based |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-17 | ALEX (GID-08) | Initial claim-to-evidence map |

---

**CANONICAL REFERENCE** — This document provides traceability for all ChainBridge trust claims.
Any claim without evidence in this map is not a valid claim.
