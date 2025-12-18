# Trust Claims Index — Binding Layer

**Document:** TRUST_CLAIMS_INDEX.md
**Version:** 1.0.0
**Owner:** ALEX (GID-08), Governance & Alignment Engine
**PAC:** PAC-ALEX-03 — Trust Claims & Non-Claims Canonicalization
**Last Updated:** 2025-12-17

---

## Purpose

This document binds claims to their allowed usage contexts.

**Rule:** A claim may only appear where this index permits. Any claim appearing outside its allowed contexts is a compliance violation.

---

## Binding Table

| Claim ID | Claim Statement | Trust Center UI | Trust API | Sales/Questionnaire | Audit Bundle | Forbidden Contexts |
|----------|-----------------|-----------------|-----------|---------------------|--------------|-------------------|
| CLAIM-01 | Unauthorized agents cannot execute tools | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "prevents all unauthorized access" |
| CLAIM-02 | Unknown agent requests are rejected | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "prevents impersonation" |
| CLAIM-03 | Agent actions are authorized against capability manifests | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "prevents privilege escalation" |
| CLAIM-04 | Certain verbs are forbidden for specific agents | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "all privilege escalation blocked" |
| CLAIM-05 | Denied requests are routed through DRCP | ❌ | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not expose DRCP internals to customers |
| CLAIM-06 | Tools execute only when explicitly authorized | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "prevents all unauthorized execution" |
| CLAIM-07 | Authorization failures block execution (fail-closed) | ✅ Section D | `GET /trust/gameday` | ✅ | `events.jsonl` | Do not imply "no false negatives" |
| CLAIM-08 | Governed artifacts are hash-verified at boot | ✅ Section B | `GET /trust/coverage` | ✅ | `fingerprint.json` | Do not imply "prevents all tampering" |
| CLAIM-09 | Governance configuration is fingerprinted at startup | ✅ Section A | `GET /trust/fingerprint` | ✅ | `fingerprint.json` | Do not imply "tamper-proof" |
| CLAIM-10 | Runtime modification of governance files is detected | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "prevents runtime attacks" |
| CLAIM-11 | Agents cannot access paths outside declared scope | ✅ Section B | `GET /trust/coverage` | ✅ | `events.jsonl` | Do not imply "prevents all data access" |
| CLAIM-12 | Files matching forbidden patterns are blocked | ❌ | `GET /trust/coverage` | ✅ | `events.jsonl` | Internal control — not customer-facing |
| CLAIM-13 | Every governance decision emits a structured event | ✅ Section C | `GET /trust/audit/latest` | ✅ | `events.jsonl` | Do not imply "complete audit trail" |
| CLAIM-14 | Audit bundles can be generated for offline verification | ✅ Section C | `GET /trust/audit/latest` | ✅ | `bundle.zip` | Do not imply "certified audit" |
| CLAIM-15 | Governance events are retained for audit periods | ❌ | `GET /trust/audit/latest` | ✅ | `events.jsonl` | Retention period is configuration-dependent |
| CLAIM-16 | Invalid requests can be routed to correction pathways | ❌ | ❌ | ✅ (limited) | `events.jsonl` | Internal mechanism — limited external disclosure |

---

## Section Mapping (Trust Center UI)

| UI Section | Claims Allowed | Claims Forbidden |
|------------|----------------|------------------|
| **Section A: Governance Fingerprint** | CLAIM-09 | All others |
| **Section B: Governance Coverage** | CLAIM-01, 02, 03, 04, 06, 08, 10, 11 | CLAIM-05, 12, 15, 16 |
| **Section C: Audit Bundle** | CLAIM-13, 14 | All others |
| **Section D: Adversarial Testing** | CLAIM-07 | All others |
| **Section E: Non-Claims** | None (disclaimers only) | All claims |

---

## API Endpoint Mapping

| Endpoint | Claims Surfaced | Response Fields |
|----------|-----------------|-----------------|
| `GET /trust/fingerprint` | CLAIM-09 | `fingerprint_hash`, `timestamp`, `schema_version` |
| `GET /trust/coverage` | CLAIM-01, 02, 03, 04, 06, 08, 10, 11 | `coverage[]` with boolean `present` |
| `GET /trust/audit/latest` | CLAIM-13, 14 | `bundle_id`, `bundle_hash`, `status` |
| `GET /trust/gameday` | CLAIM-07 | `scenarios_tested`, `silent_failures`, `fail_closed_all` |

---

## Sales & Security Questionnaire Usage

### Allowed Statements

| Context | Claim IDs | Pre-Approved Language |
|---------|-----------|----------------------|
| Security Questionnaire | ALL (1-16) | "ChainBridge implements governance controls at the agent intent layer. Controls include identity validation (CLAIM-01, 02), verb-based authorization (CLAIM-03, 04), fail-closed execution binding (CLAIM-06, 07), artifact integrity verification (CLAIM-08, 09, 10), scope enforcement (CLAIM-11), and structured audit emission (CLAIM-13, 14). All controls are test-backed." |
| Sales Deck | CLAIM-01, 02, 03, 06, 07, 08, 13, 14 | "ChainBridge enforces documented governance controls with fail-closed behavior. Every claim is test-backed. The Trust Center provides read-only evidence." |
| Executive Summary | CLAIM-07, 09, 13, 14 | "ChainBridge provides deterministic governance with cryptographically verifiable audit bundles." |
| RFP Response | ALL (1-16) | Reference TRUST_CLAIMS.md directly with evidence links |

### Forbidden Patterns

| ❌ Never Say | Why | Claim Violated |
|-------------|-----|----------------|
| "ChainBridge prevents fraud" | Over-claim — we mitigate, not prevent | CLAIM-01-16 |
| "ChainBridge is secure" | Ambiguous — must qualify scope | ALL |
| "ChainBridge guarantees safety" | Over-claim — no absolute guarantee | ALL |
| "100% coverage" | False — coverage is documented, not total | CLAIM-07 |
| "Certified secure" | False — no external certification | CLAIM-14 |
| "Prevents all attacks" | Over-claim — we address documented threats | ALL |
| "Tamper-proof" | Over-claim — we detect, not prevent | CLAIM-08, 10 |
| "No vulnerabilities" | Over-claim — impossible | ALL |

---

## Audit Bundle Artifact Mapping

| Artifact File | Claims Proven | Verification Command |
|---------------|---------------|---------------------|
| `fingerprint.json` | CLAIM-08, 09 | `sha256sum fingerprint.json` |
| `events.jsonl` | CLAIM-01-07, 10-16 | `python verify_audit_bundle.py --events` |
| `bundle_manifest.json` | CLAIM-13, 14 | `python verify_audit_bundle.py --manifest` |
| `test_results.json` | CLAIM-01-16 | `pytest --json-report` |

---

## Evidence Traceability

### CLAIM-01: Unauthorized agents cannot execute tools

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_forged_gid.py` |
| Event Type | `GovernanceEventType.DECISION_DENIED` |
| Audit Artifact | `governance_events/events.jsonl` |
| Scope | ChainBridge governance boundary only |

### CLAIM-02: Unknown agent requests are rejected

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_forged_gid.py` |
| Unit Test | `tests/governance/test_acm_evaluator.py` |
| Event Type | `GovernanceEventType.GID_PARSE_FAILED` |
| Scope | ChainBridge governance boundary only |

### CLAIM-03: Agent actions are authorized against capability manifests

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_acm_evaluator.py` |
| Unit Test | `tests/governance/test_chain_of_command.py` |
| Manifest Files | `manifests/*.yaml` |
| Scope | ChainBridge governance boundary only |

### CLAIM-04: Certain verbs are forbidden for specific agents

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_diggi_forbidden_verb.py` |
| Unit Test | `tests/governance/test_diggi_corrections.py` |
| Constant | `DIGGY_FORBIDDEN_VERBS = {"EXECUTE", "BLOCK", "APPROVE"}` |
| Scope | Diggi agent (GID-00) |

### CLAIM-05: Denied requests are routed through DRCP

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_drcp.py` |
| Module | `core/governance/drcp.py` |
| Scope | Internal routing — not customer-facing |

### CLAIM-06: Tools execute only when explicitly authorized

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_tool_without_envelope.py` |
| Unit Test | `tests/governance/test_diggi_envelope_handler.py` |
| Event Type | `GovernanceEventType.TOOL_EXECUTION_DENIED` |
| Scope | ChainBridge governance boundary only |

### CLAIM-07: Authorization failures block execution (fail-closed)

| Evidence Type | Path |
|---------------|------|
| Gameday Suite | `tests/governance/gameday/` (109+ tests) |
| Unit Test | `tests/governance/test_boot_checks.py` |
| Behavior | All gameday tests validate fail-closed invariant |
| Scope | ChainBridge governance boundary only |

### CLAIM-08: Governed artifacts are hash-verified at boot

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_artifact_mismatch.py` |
| Module | `scripts/ci/artifact_verifier.py` |
| Error Type | `ArtifactIntegrityError` |
| Scope | Artifacts listed in manifest |

### CLAIM-09: Governance configuration is fingerprinted at startup

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_governance_fingerprint.py` |
| Unit Test | `tests/governance/test_boot_checks.py` |
| Class | `GovernanceFingerprintEngine` |
| Scope | Governance root files only |

### CLAIM-10: Runtime modification of governance files is detected

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_governance_drift.py` |
| Error Type | `GovernanceDriftError` |
| Event Type | `GovernanceEventType.GOVERNANCE_DRIFT_DETECTED` |
| Scope | Governance root files only |

### CLAIM-11: Agents cannot access paths outside declared scope

| Evidence Type | Path |
|---------------|------|
| Gameday Test | `tests/governance/gameday/test_gameday_scope_violation.py` |
| Unit Test | `tests/governance/test_atlas_scope.py` |
| Event Type | `GovernanceEventType.SCOPE_VIOLATION` |
| Scope | Repository scope manifest |

### CLAIM-12: Files matching forbidden patterns are blocked

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_atlas_scope.py` |
| Module | `scripts/ci/check_repo_scope.py` |
| Patterns | `*bot*.py`, `*trading*.py`, `*.backup`, `.env` |
| Scope | CI enforcement |

### CLAIM-13: Every governance decision emits a structured event

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_governance_events.py` |
| Module | `core/governance/events.py` |
| Module | `core/governance/event_sink.py` |
| Scope | All governance decisions |

### CLAIM-14: Audit bundles can be generated for offline verification

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_audit_export.py` |
| Module | `core/governance/audit_export.py` |
| Artifact | `proofpacks/*.json` |
| Scope | On-demand export |

### CLAIM-15: Governance events are retained for audit periods

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_event_retention.py` |
| Module | `core/governance/event_sink.py` |
| Scope | Configuration-dependent |

### CLAIM-16: Invalid requests can be routed to correction pathways

| Evidence Type | Path |
|---------------|------|
| Unit Test | `tests/governance/test_diggi_corrections.py` |
| Unit Test | `tests/governance/test_diggi_envelope_handler.py` |
| Module | `core/governance/diggi_corrections.py` |
| Scope | Correction-eligible requests only |

---

## Drift Detection Rules

### Automatic Checks

| Check | Trigger | Action |
|-------|---------|--------|
| New claim added | PR modifies TRUST_CLAIMS.md | Require evidence link |
| Claim removed | PR modifies TRUST_CLAIMS.md | Require justification |
| UI copy changed | PR modifies Trust UI components | Cross-reference this index |
| API response changed | PR modifies trust endpoints | Cross-reference this index |
| Test removed | PR removes gameday/governance test | Flag claim validity |

### Manual Review Required

| Scenario | Reviewer |
|----------|----------|
| New claim proposed | ALEX (GID-08) |
| Non-claim modification | Legal review recommended |
| Sales language change | Cross-check forbidden patterns |
| External audit request | Reference this index + evidence |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-17 | ALEX (GID-08) | Initial claims index |

---

**CANONICAL REFERENCE** — This document is the authoritative binding layer for all ChainBridge trust claims.
Claims may only appear in contexts permitted by this index.
