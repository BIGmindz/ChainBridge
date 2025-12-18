# ChainBridge Canonical Invariant Set

**Document:** CANONICAL_INVARIANTS.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Root Trust Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-INVARIANT-LOCK-01
**Effective Date:** 2025-12-18
**Source Snapshot:** ChainBridge-exec-snapshot_2025-12-18.zip

---

## 1. Purpose

This document is the **root trust contract** for ChainBridge. It defines the non-negotiable system invariants that:

- MUST be enforced at all times
- MUST NOT be relaxed without new PAC approval
- MUST be provable from code or contract

**Every invariant is enforceable, auditable, and teachable to agents.**

---

## 2. Invariant Domains

| Domain | ID Prefix | Scope |
|--------|-----------|-------|
| PDO Immutability | INV-PDO | Proof Decision Object records |
| ProofPack Integrity | INV-PP | Evidence bundle structure |
| Verification Semantics | SEM-VER | Pass/fail verification rules |
| Governance Boundaries | INV-GOV | Agent scope and sensitive domains |
| Trust Non-Claims | INV-TNC | Explicit non-guarantees |

---

## 3. PDO Immutability Invariants

### INV-PDO-001: Field Immutability
**All PDORecord fields are immutable after write.**

| Enforcement | Location |
|-------------|----------|
| Pydantic `frozen=True` | `core/occ/schemas/pdo.py:66` |
| PDOStore.update() raises | `core/occ/store/pdo_store.py:436` |
| Test coverage | `tests/occ/test_pdo_immutability.py:TestPDOUpdateBlocked` |

**Failure Condition:** TypeError on mutation attempt; PDOImmutabilityError on store operation.

---

### INV-PDO-002: Hash Determinism
**PDO hash computation is deterministic and reproducible.**

| Enforcement | Location |
|-------------|----------|
| compute_hash() method | `core/occ/schemas/pdo.py:192-229` |
| Canonical JSON serialization | `sort_keys=True, separators=(",", ":")` |
| Test coverage | `tests/occ/test_pdo_immutability.py:TestPDOHashSealing` |

**Failure Condition:** Hash mismatch on recomputation.

---

### INV-PDO-003: Hash Algorithm
**Hash algorithm is SHA-256 with canonical JSON serialization.**

| Enforcement | Location |
|-------------|----------|
| hashlib.sha256() | `core/occ/schemas/pdo.py:227` |
| hash_algorithm field | `core/occ/schemas/pdo.py:161` default="sha256" |
| Contract doc | `docs/contracts/PDO_INVARIANTS.md:Section 4.2` |

**Failure Condition:** Non-SHA256 hash detected.

---

### INV-PDO-004: Append-Only Operations
**The only permitted write operation is CREATE (append).**

| Enforcement | Location |
|-------------|----------|
| create() method only | `core/occ/store/pdo_store.py:199-260` |
| update() blocked | `core/occ/store/pdo_store.py:436-444` |
| delete() blocked | `core/occ/store/pdo_store.py:446-454` |
| Test coverage | `tests/occ/test_pdo_immutability.py:TestPDOUpdateBlocked` |

**Failure Condition:** PDOImmutabilityError raised on any mutation attempt.

---

### INV-PDO-005: No Update Schema
**No PDOUpdate schema exists or will be created.**

| Enforcement | Location |
|-------------|----------|
| Absence by design | `core/occ/schemas/pdo.py` (schema does not exist) |
| Contract doc | `docs/contracts/PDO_INVARIANTS.md:Section 5.2` |

**Failure Condition:** Presence of PDOUpdate class in codebase.

---

### INV-PDO-006: Hash Verification on Read
**PDO hash is verified on read by default.**

| Enforcement | Location |
|-------------|----------|
| get() verify_integrity=True | `core/occ/store/pdo_store.py:276-290` |
| PDOTamperDetectedError | `core/occ/schemas/pdo.py:341-355` |
| Test coverage | `tests/occ/test_pdo_immutability.py:TestPDOTamperDetection` |

**Failure Condition:** PDOTamperDetectedError raised on hash mismatch.

---

### INV-PDO-007: Hash Verification on Load
**All PDOs are verified on store initialization.**

| Enforcement | Location |
|-------------|----------|
| _load() verification loop | `core/occ/store/pdo_store.py:86-107` |
| Halt on tamper detection | Raises PDOTamperDetectedError, halts load |
| Test coverage | `tests/occ/test_pdo_immutability.py:test_tamper_detection_on_read` |

**Failure Condition:** Store fails to initialize; PDOTamperDetectedError raised.

---

### INV-PDO-008: Atomic Persistence
**PDO writes are atomic.**

| Enforcement | Location |
|-------------|----------|
| Temp file + rename pattern | `core/occ/store/pdo_store.py:120-148` |
| Test coverage | `tests/occ/test_pdo_immutability.py:TestPDOPersistence` |

**Failure Condition:** Partial write (prevented by atomic rename).

---

### INV-PDO-009: Thread Safety
**All PDOStore operations are thread-safe.**

| Enforcement | Location |
|-------------|----------|
| threading.Lock | `core/occ/store/pdo_store.py:62` |
| Lock acquisition | All public methods acquire lock |

**Failure Condition:** Race condition (blocked by mutex).

---

### INV-PDO-010: UTC Timestamps
**All timestamps are UTC with timezone suffix.**

| Enforcement | Location |
|-------------|----------|
| datetime.now(timezone.utc) | `core/occ/store/pdo_store.py:208` |
| Contract doc | `docs/contracts/PDO_INVARIANTS.md:Section 9` |

**Failure Condition:** Non-UTC timestamp rejected by validation.

---

## 4. ProofPack Integrity Invariants

### INV-PP-001: Fixed Artifact Set
**The ProofPack artifact set is fixed and cannot be extended.**

| Enforcement | Location |
|-------------|----------|
| Generator artifact structure | `core/occ/proofpack/generator.py` |
| Contract doc | `docs/contracts/PROOFPACK_INVARIANTS.md:Section 2` |
| Verification step order | `core/occ/proofpack/verifier.py:78-140` |

**Failure Condition:** Verification fails on unknown artifact type.

---

### INV-PP-002: Canonical JSON Serialization
**JSON serialization uses compact format with specific separators.**

| Enforcement | Location |
|-------------|----------|
| separators=(",", ":") | `core/occ/proofpack/schemas.py:canonical_json()` |
| sort_keys=True | All JSON operations |
| Contract doc | `docs/contracts/PROOFPACK_INVARIANTS.md:Section 4.1` |

**Failure Condition:** Hash mismatch due to serialization difference.

---

### INV-PP-003: Manifest Hash Binding
**All manifest hashes must match computed hashes of referenced files.**

| Enforcement | Location |
|-------------|----------|
| Verifier step 2 | `core/occ/proofpack/verifier.py:_verify_artifact_hashes()` |
| Test coverage | `tests/occ/test_proofpack_verification.py:TestTamperDetection` |

**Failure Condition:** VerificationOutcome.INVALID_ARTIFACT_HASH returned.

---

### INV-PP-004: Offline Verification
**Verification must be possible without network access.**

| Enforcement | Location |
|-------------|----------|
| Verifier requires only | SHA-256, JSON parser, UTF-8, ProofPack contents |
| Contract doc | `docs/contracts/PROOFPACK_INVARIANTS.md:Section 6.3` |
| Test coverage | `tests/occ/test_proofpack_verification.py:test_offline_verification` |

**Failure Condition:** Verification requires external system access.

---

### INV-PP-005: One ProofPack = One PDO
**ProofPacks do not aggregate multiple PDOs.**

| Enforcement | Location |
|-------------|----------|
| Generator design | `core/occ/proofpack/generator.py:generate()` |
| Contract doc | `docs/contracts/PROOFPACK_INVARIANTS.md:Section 10.3` |

**Failure Condition:** ProofPack contains multiple root PDOs.

---

## 5. Verification Semantics Invariants

### SEM-VER-001: Binary Outcomes Only
**Verification produces exactly two outcomes: PASS or FAIL.**

| Enforcement | Location |
|-------------|----------|
| VerificationOutcome enum | `core/occ/proofpack/schemas.py` |
| Contract doc | `docs/contracts/VERIFICATION_SEMANTICS.md:Section 2` |

**Failure Condition:** Non-PASS/FAIL outcome returned.

---

### SEM-VER-002: Fail-Fast Behavior
**Verification halts on first failure.**

| Enforcement | Location |
|-------------|----------|
| Verifier step logic | `core/occ/proofpack/verifier.py:78-140` |
| Contract doc | `docs/contracts/VERIFICATION_SEMANTICS.md:Section 2.3` |

**Failure Condition:** Verification continues after failure.

---

### SEM-VER-003: Tamper Detection Halts Processing
**Any tamper detection must halt downstream processing.**

| Enforcement | Location |
|-------------|----------|
| PDOTamperDetectedError | `core/occ/schemas/pdo.py:341-355` |
| Store load halt | `core/occ/store/pdo_store.py:95-102` |
| Contract doc | `docs/contracts/VERIFICATION_SEMANTICS.md:Section 6` |

**Failure Condition:** Processing continues after tamper detection.

---

## 6. Governance Boundary Invariants

### INV-GOV-001: Sensitive Domain Classification
**Defined domains require strict pre-commit discipline.**

| Enforcement | Location |
|-------------|----------|
| GATE-001 domain list | `docs/governance/SENSITIVE_DOMAIN_GATEWAY.md:Section 2` |
| Path detection rules | `docs/governance/SENSITIVE_DOMAIN_GATEWAY.md:GATE-002` |

**Failure Condition:** Sensitive domain code merged without gateway review.

---

### INV-GOV-002: Forbidden Language Patterns
**Marketing and probabilistic language forbidden in sensitive domains.**

| Enforcement | Location |
|-------------|----------|
| GATE-003 forbidden terms | `docs/governance/SENSITIVE_DOMAIN_GATEWAY.md:Section 3.1` |
| GATE-004 probabilistic | `docs/governance/SENSITIVE_DOMAIN_GATEWAY.md:Section 3.2` |
| GATE-005 future guarantees | `docs/governance/SENSITIVE_DOMAIN_GATEWAY.md:Section 3.3` |

**Failure Condition:** Forbidden language detected in sensitive domain output.

---

## 7. Trust Non-Claims Invariants

### INV-TNC-001: Explicit Non-Guarantees
**ChainBridge makes explicit non-claims documented in TRUST_NON_CLAIMS.md.**

| Enforcement | Location |
|-------------|----------|
| TNC-SEC-* | `docs/trust/TRUST_NON_CLAIMS.md:Section 1` |
| TNC-COMP-* | `docs/trust/TRUST_NON_CLAIMS.md:Section 2` |
| TNC-CORR-* | `docs/trust/TRUST_NON_CLAIMS.md:Section 3` |
| TNC-CERT-* | `docs/trust/TRUST_NON_CLAIMS.md:Section 4` |
| TNC-ATK-* | `docs/trust/TRUST_NON_CLAIMS.md:Section 6` |

**Failure Condition:** Trust Center UI or documentation makes excluded claims.

---

## 8. Invariant Mapping Table

| Invariant ID | Code Location | Contract Document | Test Coverage |
|--------------|---------------|-------------------|---------------|
| INV-PDO-001 | `pdo.py:66` | PDO_INVARIANTS.md §3.1 | test_pdo_immutability.py |
| INV-PDO-002 | `pdo.py:192-229` | PDO_INVARIANTS.md §4.1 | test_pdo_immutability.py |
| INV-PDO-003 | `pdo.py:227` | PDO_INVARIANTS.md §4.2 | test_pdo_immutability.py |
| INV-PDO-004 | `pdo_store.py:199-260` | PDO_INVARIANTS.md §5.1 | test_pdo_immutability.py |
| INV-PDO-005 | (absence) | PDO_INVARIANTS.md §5.2 | (by construction) |
| INV-PDO-006 | `pdo_store.py:276-290` | PDO_INVARIANTS.md §7.2 | test_pdo_immutability.py |
| INV-PDO-007 | `pdo_store.py:86-107` | PDO_INVARIANTS.md §7.3 | test_pdo_immutability.py |
| INV-PDO-008 | `pdo_store.py:120-148` | PDO_INVARIANTS.md §7.1 | test_pdo_immutability.py |
| INV-PDO-009 | `pdo_store.py:62` | PDO_INVARIANTS.md §7.4 | (by construction) |
| INV-PDO-010 | `pdo_store.py:208` | PDO_INVARIANTS.md §9 | test_pdo_immutability.py |
| INV-PP-001 | `generator.py` | PROOFPACK_INVARIANTS.md §2 | test_proofpack_verification.py |
| INV-PP-002 | `schemas.py:canonical_json()` | PROOFPACK_INVARIANTS.md §4.1 | test_proofpack_verification.py |
| INV-PP-003 | `verifier.py` | PROOFPACK_INVARIANTS.md §5.6 | test_proofpack_verification.py |
| INV-PP-004 | `verifier.py` | PROOFPACK_INVARIANTS.md §6.3 | test_proofpack_verification.py |
| INV-PP-005 | `generator.py` | PROOFPACK_INVARIANTS.md §10.3 | (by construction) |
| SEM-VER-001 | `schemas.py:VerificationOutcome` | VERIFICATION_SEMANTICS.md §2 | (by construction) |
| SEM-VER-002 | `verifier.py:78-140` | VERIFICATION_SEMANTICS.md §2.3 | test_proofpack_verification.py |
| SEM-VER-003 | `pdo.py:341-355` | VERIFICATION_SEMANTICS.md §6 | test_pdo_immutability.py |
| INV-GOV-001 | (doc only) | SENSITIVE_DOMAIN_GATEWAY.md §2 | (manual review) |
| INV-GOV-002 | (doc only) | SENSITIVE_DOMAIN_GATEWAY.md §3 | (manual review) |
| INV-TNC-001 | (doc only) | TRUST_NON_CLAIMS.md | (manual review) |

---

## 9. Identified Gaps

| Gap | Description | Recommendation |
|-----|-------------|----------------|
| GAP-001 | Thread safety test coverage is implicit | Add explicit concurrent access tests |
| GAP-002 | Governance language enforcement is manual | Consider automated lint rule |
| GAP-003 | INV-PDO-009 (thread safety) lacks dedicated test | Add test_thread_safety.py |
| GAP-004 | INV-PP-005 (single PDO) not explicitly tested | Add negative test for multi-PDO |

---

## 10. Next Hardening PAC Recommendation

**PAC-CODY-INVARIANT-ENFORCEMENT-01**: Automated Invariant Enforcement

Scope:
1. Add explicit thread safety tests for PDOStore
2. Add automated lint rule for forbidden language patterns
3. Add negative test for multi-PDO ProofPack rejection
4. Add invariant violation logging with structured telemetry

Priority: Medium
Assigned: CODY (GID-01)

---

## 11. Document Control

| Field | Value |
|-------|-------|
| Contract Owner | BENSON (GID-00) |
| Created | 2025-12-18 |
| Status | LOCKED |
| PAC | PAC-BENSON-INVARIANT-LOCK-01 |
| Source Snapshot | ChainBridge-exec-snapshot_2025-12-18.zip |
| Review Required | Any modification requires PAC approval |

---

**END OF CONTRACT — CANONICAL_INVARIANTS.md**
