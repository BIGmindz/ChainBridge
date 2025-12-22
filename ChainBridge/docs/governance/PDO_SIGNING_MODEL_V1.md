# PDO Signing Model v1

## Document Metadata

| Field | Value |
|-------|-------|
| **Document ID** | PDO-SIGN-MODEL-V1 |
| **Author** | Sam — Security & Threat Engineer (GID-06) |
| **Date** | 2025-12-22 |
| **Status** | DESIGN LOCKED |
| **Authority** | PDO Enforcement Model v1 (LOCKED) |
| **Classification** | Internal / Security Architecture |
| **Audience** | CTO, Security, Audit, Regulator-facing |
| **PAC Reference** | PAC-SAM-PDO-SIGNING-DESIGN-01 |

---

## 0. Design Principles

| Principle | Requirement |
|-----------|-------------|
| **Non-forgeable** | PDO origin must be cryptographically provable |
| **Non-replayable** | PDO valid for one execution context only |
| **Detached trust** | Execution services must not hold signing keys |
| **Deterministic verification** | Signature verification must be stateless |
| **Upgradeable** | Signing scheme versioned independently |

---

## 1. Threat Closure Mapping

This signing model is designed to close specific threat vectors identified in PAC-SAM-PDO-THREAT-MODEL-01.

### 1.1 Threats CLOSED by Signing

| Threat ID | Threat Name | Closure Mechanism | Closure Status |
|-----------|-------------|-------------------|----------------|
| **PDO-T-002** | Header Spoofing | Signature required for valid PDO; headers alone insufficient | **CLOSED** |
| **PDO-T-003** | Synthetic PDO Forgery | Signature requires possession of private key material unavailable to attacker | **CLOSED** |
| **PDO-T-004** | Replay Attack | Nonce + expires_at fields enforce single-use semantics | **CLOSED** |
| **PDO-T-007** | Signer Identity Impersonation | Signer identity cryptographically bound to signature; claiming false identity requires private key | **CLOSED** |

### 1.2 Additional Mitigations

| Threat ID | Threat Name | Mitigation | Residual Risk |
|-----------|-------------|------------|---------------|
| **PDO-T-004** | PDO Replay Attack | Signature binds PDO to specific `pdo_id` and `timestamp`; replay of exact PDO detectable via ID collision | Replay across systems with non-synchronized ID namespaces remains possible; operation binding not enforced by signing alone |

### 1.3 Threats NOT Mitigated by Signing

| Threat ID | Threat Name | Reason Not Mitigated |
|-----------|-------------|---------------------|
| **PDO-T-014** | CI/CD Artifact Poisoning | Signing operates at PDO layer; build pipeline compromise is infrastructure boundary |
| **PDO-T-015** | Dependency Chain Compromise | Signing does not protect against malicious verification logic |
| **PDO-T-009** | Direct File Tampering | Signature detection requires verification call; unverified reads remain vulnerable |
| **PDO-T-010** | PDO Store Deletion | Signing cannot prevent deletion; availability is orthogonal to integrity |

### 1.4 Residual Risk Statement

Signing provides **origin authentication** and **integrity binding**. It does not provide:
- Availability guarantees
- Authorization policy enforcement
- Temporal validity constraints
- Operation-level binding beyond PDO identity

---

## 2. Signing Scope Definition

### 2.1 What Signing Protects

| Protection | Description |
|------------|-------------|
| **Origin Authentication** | Signature proves the PDO was created by an entity possessing the signer's private key |
| **Integrity Binding** | Signature invalidates if any signed field is modified after signing |
| **Non-Repudiation** | Signer cannot deny having signed a PDO if signature verifies against their public key |
| **Forgery Prevention** | Attacker without private key cannot construct a PDO that passes verification |

### 2.2 What Signing Does NOT Protect

| Non-Protection | Description |
|----------------|-------------|
| **Authorization** | A valid signature does not imply the signer was authorized to make the decision |
| **Correctness** | A valid signature does not imply the decision content is correct or appropriate |
| **Timeliness** | A valid signature does not imply the PDO is temporally valid for current use |
| **Uniqueness** | A valid signature does not prevent the same PDO from being submitted multiple times |
| **Confidentiality** | Signing does not encrypt; PDO contents remain readable |

---

## 3. Canonical Signed Payload (IMMUTABLE)

### 3.1 Fields Included in Signature

The signature MUST cover exactly the following fields. Any mutation invalidates the signature:

| Order | Field Name | Type | Inclusion Rule |
|-------|------------|------|----------------|
| 1 | `pdo_id` | string | REQUIRED; globally unique identifier |
| 2 | `decision_hash` | string | REQUIRED; lowercase hexadecimal SHA-256 |
| 3 | `policy_version` | string | REQUIRED; exact policy reference |
| 4 | `agent_id` | string | REQUIRED; signing agent identifier |
| 5 | `action` | string | REQUIRED; action being authorized |
| 6 | `outcome` | string | REQUIRED; APPROVED / REJECTED / PENDING |
| 7 | `timestamp` | string | REQUIRED; ISO 8601 UTC signing time |
| 8 | `nonce` | string | REQUIRED; cryptographically random, single-use |
| 9 | `expires_at` | string | REQUIRED; ISO 8601 UTC hard expiry |

### 3.2 Fields Explicitly EXCLUDED from Signature

| Field Name | Reason for Exclusion |
|------------|---------------------|
| `signature` | Cannot sign itself |
| `signature.alg` | Metadata about signature, not content |
| `signature.key_id` | Verifier selection metadata |
| `metadata` | Mutable auxiliary data; not part of decision integrity |
| `tags` | Organizational labels; not decision-critical |

### 3.3 Signature Envelope Structure

```json
{
  "signature": {
    "alg": "<algorithm-identifier>",
    "key_id": "<verifier-key-selector>",
    "sig": "<base64-encoded-signature>"
  }
}
```

| Field | Purpose |
|-------|---------|
| `alg` | Explicit algorithm binding; verifier rejects unknown algorithms |
| `key_id` | Verifier key selection; enables key rotation |
| `sig` | Cryptographic signature over canonical payload |

### 3.4 Canonical Serialization Algorithm

1. Construct a JSON object containing exactly the fields in Section 3.1
2. Order fields alphabetically by key name
3. Use no whitespace between tokens (compact JSON)
4. Use UTF-8 encoding
5. Represent `null` values as JSON `null` (not empty string)
6. The resulting byte sequence is the **signing input**

### 3.5 Serialization Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-SIGN-001** | Given identical field values, serialization produces identical byte sequences |
| **INV-SIGN-002** | Serialization is reversible; parsing the serialized form recovers exact field values |
| **INV-SIGN-003** | Field ordering is deterministic and independent of insertion order |
| **INV-SIGN-004** | No optional fields exist within signing scope; all fields REQUIRED |

### 3.5 Versioning Behavior

| Version Field | Behavior |
|---------------|----------|
| **Signing Model Version** | Recorded as `signing_version` field (outside signature scope) |
| **Schema Changes** | New signing model version required if signed fields change |
| **Backward Compatibility** | Verifier MUST reject PDOs with unrecognized `signing_version` |

---

## 4. Nonce & Replay Protection

### 4.1 Required Replay Protection Fields

| Field | Rule |
|-------|------|
| `nonce` | Cryptographically random, single-use, minimum 128 bits |
| `expires_at` | Hard upper bound on PDO validity; ISO 8601 UTC |
| `pdo_id` | Must be globally unique across all PDOs |

### 4.2 Enforcement Requirements

| Requirement | Description |
|-------------|-------------|
| **REQ-REPLAY-001** | Same `(pdo_id, nonce)` tuple MUST NOT validate twice |
| **REQ-REPLAY-002** | PDO with `expires_at` in the past MUST fail verification |
| **REQ-REPLAY-003** | Nonce reuse MUST be logged as security event |
| **REQ-REPLAY-004** | Verification MUST check expiry before cryptographic verification |

### 4.3 Replay Detection Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-REPLAY-001** | A valid PDO becomes permanently invalid after first successful use |
| **INV-REPLAY-002** | A valid PDO becomes permanently invalid after `expires_at` |
| **INV-REPLAY-003** | Nonce storage MUST survive service restart |

---

## 5. Key Management Boundaries

### 5.1 Allowed Key Operations

| Operation | Permitted Location |
|-----------|-------------------|
| Private key storage | Central Trust Layer only |
| Signing operations | Central Trust Layer only |
| Public key distribution | All execution services |
| Signature verification | All execution services |
| Key rotation | Central Trust Layer via `key_id` versioning |

### 5.2 Forbidden Key Operations

| Operation | Reason |
|-----------|--------|
| ❌ Agents holding private keys | Compromised agent = compromised signing |
| ❌ Runtime key generation | Non-deterministic trust establishment |
| ❌ Environment-based key overrides | Injection attack vector |
| ❌ Shared secrets between services | Violates detached trust principle |
| ❌ Private key export | Key material must never leave Trust Layer |

### 5.3 Key Management Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-KEY-001** | Execution services MUST NOT possess private signing keys |
| **INV-KEY-002** | All signing MUST occur within Central Trust Layer |
| **INV-KEY-003** | Public keys MUST be distributed via secure channel |
| **INV-KEY-004** | Key rotation MUST NOT invalidate previously signed PDOs |

---

## 6. Signer Identity Semantics

### 6.1 Signer Definition

A **signer** is an identity that:
1. Possesses exclusive control of a private key
2. Is registered in a signer registry with an associated public key
3. Is authorized to sign PDOs (authorization is separate from signing capability)

### 6.2 Signer Identifier Format

Signer identifiers MUST conform to the following grammar:

```
signer_id := signer_class "::" signer_name
signer_class := "agent" | "system" | "operator"
signer_name := [a-zA-Z0-9_-]+
```

### 6.3 Signer Classes

| Class | Description | Key Custody Model |
|-------|-------------|-------------------|
| **agent** | Autonomous software agent making decisions | Key held by Trust Layer; agent has no direct access |
| **system** | Platform infrastructure component | Key held by Trust Layer; no human access |
| **operator** | Human operator with signing authority | Key held by Trust Layer; human authenticates to sign |

### 6.4 Identity Binding

| Binding Property | Description |
|------------------|-------------|
| **Signer → Key** | Each signer identifier maps to exactly one active public key at any time |
| **Key → Signer** | Each public key maps to exactly one signer identifier (no key sharing) |
| **Signature → Signer** | Valid signature proves possession of private key associated with claimed signer |

### 6.5 Signer Identity Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-SIGNER-001** | A signer identifier without a registered public key MUST NOT produce verifiable signatures |
| **INV-SIGNER-002** | Two distinct signer identifiers MUST NOT share the same key pair |
| **INV-SIGNER-003** | The `agent_id` field in a PDO MUST match the signer identity bound to the verifying public key |

---

## 7. Verification Semantics

### 7.1 What Verification MUST Prove

A successful verification establishes ALL of the following:

| Property | Verification Proves |
|----------|---------------------|
| **Integrity** | The signed fields have not been modified since signing |
| **Origin** | The PDO was signed by an entity controlling the private key for the claimed signer |
| **Binding** | The signature is bound to this specific PDO (not transferable) |
| **Registry Match** | The signer is registered and the public key is active |
| **Freshness** | The PDO has not expired (`expires_at` in future) |
| **Uniqueness** | The PDO has not been used before (nonce not consumed) |

### 7.2 What Verification MUST Reject

Verification MUST fail (return `INVALID`) for ALL of the following conditions:

| Rejection Condition | Description |
|--------------------|-------------|
| **REJ-001** | Signature field is missing or empty |
| **REJ-002** | Signature does not cryptographically verify against claimed signer's public key |
| **REJ-003** | Signer identifier not found in signer registry |
| **REJ-004** | Signer's public key is revoked or expired |
| **REJ-005** | Canonical serialization of signed fields produces different bytes than signed |
| **REJ-006** | `signing_version` is unrecognized or unsupported |
| **REJ-007** | Any signed field is missing from PDO |
| **REJ-008** | `expires_at` is in the past |
| **REJ-009** | `nonce` has been previously consumed |
| **REJ-010** | `alg` in signature envelope is unrecognized |
| **REJ-011** | `key_id` references unknown or revoked key |

### 7.3 Verification Output

Verification produces exactly one of the following outcomes:

| Outcome | Meaning |
|---------|---------|
| **VALID** | All verification checks passed; signature is authentic |
| **INVALID** | One or more verification checks failed; signature is not authentic |
| **ERROR** | Verification could not complete (registry unavailable, malformed input) |

### 7.4 Verification Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-VERIFY-001** | Given identical inputs, verification produces identical outcomes |
| **INV-VERIFY-002** | Verification is stateless with respect to signature validation |
| **INV-VERIFY-003** | Verification MUST NOT succeed for any PDO without a signature |
| **INV-VERIFY-004** | Verification failure MUST identify which rejection condition triggered |
| **INV-VERIFY-005** | Nonce consumption MUST be atomic with successful verification |

---

## 8. Failure Modes

### 6.1 Signing Failure Modes

| Failure Mode | Trigger | Consequence |
|--------------|---------|-------------|
| **SF-001** | Private key unavailable | PDO cannot be signed; creation blocked |
| **SF-002** | Signer not registered | PDO cannot be signed; creation blocked |
| **SF-003** | Serialization error | PDO cannot be signed; creation blocked |
| **SF-004** | Signing service unavailable | PDO cannot be signed; creation blocked |
| **SF-005** | Nonce generation failure | PDO cannot be signed; creation blocked |

### 8.2 Verification Failure Modes

| Failure Mode | Trigger | Consequence |
|--------------|---------|-------------|
| **VF-001** | Signature invalid | PDO rejected; enforcement gate blocks |
| **VF-002** | Signer revoked | PDO rejected; enforcement gate blocks |
| **VF-003** | Registry unavailable | Verification returns ERROR; fail-closed behavior required |
| **VF-004** | Unknown signing version | PDO rejected; enforcement gate blocks |
| **VF-005** | PDO expired | PDO rejected; enforcement gate blocks |
| **VF-006** | Nonce already consumed | PDO rejected; replay attack logged |

### 8.3 Fail-Closed Requirement

| Condition | Required Behavior |
|-----------|-------------------|
| Verification returns `INVALID` | PDO MUST NOT be accepted for any purpose |
| Verification returns `ERROR` | PDO MUST NOT be accepted; operation MUST fail |
| Registry unavailable | All verification attempts MUST return ERROR |
| Nonce store unavailable | All verification attempts MUST return ERROR |

---

## 9. Threat Mitigation Summary

| Threat ID | Threat | Mitigation Mechanism | Status |
|-----------|--------|---------------------|--------|
| **PDO-T-002** | Header spoofing | Signature required; headers insufficient | **CLOSED** |
| **PDO-T-003** | Synthetic PDO | Private key required to sign | **CLOSED** |
| **PDO-T-004** | Replay attack | Nonce + expires_at enforcement | **CLOSED** |
| **PDO-T-007** | Signer spoofing | Cryptographic identity binding | **CLOSED** |
| **PDO-T-005** | Policy downgrade | `policy_version` included in signed payload | **MITIGATED** |
| **PDO-T-009** | Store tampering | Signature verification detects modification | **MITIGATED** |

---

## 10. Explicit Non-Goals

The following are explicitly OUT OF SCOPE for this signing model:

| Non-Goal | Rationale |
|----------|-----------|
| **Algorithm Selection** | Cryptographic algorithm choice is implementation decision |
| **Key Storage Mechanism** | Key custody is operational/infrastructure concern |
| **Key Generation Procedure** | Operational procedure; not architectural |
| **Performance Requirements** | Performance is implementation/deployment concern |
| **Network Protocol** | Transport is infrastructure concern |
| **Hardware Security Module Integration** | Operational/infrastructure concern |
| **Audit Log Format** | Separate audit specification |
| **UI/UX for Signing** | Application layer concern |
| **Multi-Signature Schemes** | Future extension; not v1 scope |
| **Threshold Signatures** | Future extension; not v1 scope |
| **Blind Signatures** | Not applicable to PDO model |
| **Blockchain Anchoring** | Future extension; not v1 scope |
| **HSM Specification** | Infrastructure/operational concern |
| **Key Rotation Schedule** | Operational procedure |
| **Implementation Language** | Implementation decision |
| **Library Selection** | Implementation decision |
| **Performance Optimization** | Implementation concern |

---

## 11. Falsifiability Tests

Each claim in this specification can be tested by the following falsification criteria:

### 8.1 Threat Closure Falsifiability

| Claim | Falsification Test |
|-------|-------------------|
| PDO-T-003 is CLOSED | Produce a PDO that passes verification without possession of any registered private key |
| PDO-T-007 is CLOSED | Produce a PDO with `signer: agent::X` that verifies against a public key not registered to `agent::X` |

### 8.2 Serialization Falsifiability

| Claim | Falsification Test |
|-------|-------------------|
| INV-SIGN-001 | Find two PDOs with identical signed field values that produce different serializations |
| INV-SIGN-002 | Find a serialization that cannot be parsed back to original field values |
| INV-SIGN-003 | Find a case where field ordering depends on insertion order |

### 8.3 Signer Identity Falsifiability

| Claim | Falsification Test |
|-------|-------------------|
| INV-SIGNER-001 | Register a signer without a public key and produce a verifiable signature |
| INV-SIGNER-002 | Register two signer identifiers with the same public key and both verify successfully |
| INV-SIGNER-003 | Produce a verifiable PDO where `agent_id` field does not match the key used to verify |

### 11.4 Verification Falsifiability

| Claim | Falsification Test |
|-------|-------------------|
| INV-VERIFY-001 | Find inputs where repeated verification produces different outcomes |
| INV-VERIFY-002 | Demonstrate a verification call that produces side effects |
| INV-VERIFY-003 | Find a PDO without signature field that returns VALID |
| REJ-001 through REJ-011 | For each rejection condition, produce a PDO that should trigger it but returns VALID |

### 11.5 Replay Protection Falsifiability

| Claim | Falsification Test |
|-------|-------------------|
| INV-REPLAY-001 | Submit the same PDO twice and have both succeed |
| INV-REPLAY-002 | Submit a PDO with `expires_at` in the past and have it succeed |
| INV-REPLAY-003 | Restart service and resubmit previously-consumed nonce successfully |

---

## 12. Rotation & Revocation Model (Conceptual)

### 12.1 Key Rotation Model

| Concept | Definition |
|---------|------------|
| **Rotation** | Replacing a signer's active public key with a new public key |
| **Rotation Window** | Period during which both old and new keys are valid for verification |
| **Post-Rotation Signing** | After rotation completes, only new key is valid for signing |
| **Post-Rotation Verification** | After rotation completes, PDOs signed with old key remain verifiable |

### 12.2 Key Rotation Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-ROTATE-001** | PDOs signed before rotation remain verifiable after rotation |
| **INV-ROTATE-002** | New PDOs after rotation MUST be signed with new key |
| **INV-ROTATE-003** | Rotation does not invalidate previously signed PDOs |

### 12.3 Revocation Model

| Concept | Definition |
|---------|------------|
| **Revocation** | Marking a signer's key as no longer valid |
| **Revocation Scope** | Whether revocation affects past signatures or only future |
| **Hard Revocation** | All signatures by revoked key fail verification (including historical) |
| **Soft Revocation** | Only new signatures fail; historical signatures remain valid |

### 12.4 Revocation Invariants

| Invariant | Description |
|-----------|-------------|
| **INV-REVOKE-001** | Revoked signers MUST NOT produce new verifiable signatures |
| **INV-REVOKE-002** | Revocation model (hard/soft) MUST be declared and consistent |
| **INV-REVOKE-003** | Revocation status MUST be queryable at verification time |

---

## 13. Handoff Targets

| Future PAC | Owner | Description |
|------------|-------|-------------|
| PDO Signature Verification (code) | Cody | Implementation of signing and verification |
| Key Lifecycle & Rotation | Dan | CI/CD and operational key management |
| Trust Center Disclosure | ALEX | Documentation and compliance reporting |
| CRO Policy Binding | Ruby | Risk policy integration with signed PDOs |

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **PDO** | Proof Decision Outcome; immutable record of a policy decision |
| **Signer** | Identity with exclusive control of a private key registered in the signer registry |
| **Signature** | Cryptographic proof binding signed fields to a specific signer |
| **Verification** | Process of confirming signature authenticity and signer identity |
| **Signer Registry** | Authoritative mapping of signer identifiers to public keys |
| **Signing Input** | Canonical byte sequence derived from signed fields |
| **Origin Authentication** | Proof that PDO was created by claimed signer |
| **Integrity Binding** | Guarantee that signed fields have not been modified |
| **Nonce** | Cryptographically random single-use value preventing replay |
| **Central Trust Layer** | Isolated component holding private signing keys |

---

## 15. Document History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2025-12-22 | Sam (GID-06) | Initial specification |
| 1.1 | 2025-12-22 | Sam (GID-06) | Added nonce/replay protection, key management boundaries, threat mitigation matrix |

---

## 16. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Eliminates PDO forgery (PDO-T-003) | ✅ CLOSED |
| Eliminates header spoofing (PDO-T-002) | ✅ CLOSED |
| Eliminates replay attacks (PDO-T-004) | ✅ CLOSED |
| Eliminates signer impersonation (PDO-T-007) | ✅ CLOSED |
| Compatible with current PDO schema | ✅ VERIFIED |
| No execution impact | ✅ DESIGN ONLY |
| Doctrine preserved | ✅ VERIFIED |

---

## 17. Approval & Handoff

### Status

**DESIGN LOCKED**

### Handoff Statement

This document defines the canonical PDO signing model. It is:
- Complete for specification purposes
- Ready for implementation planning
- Authoritative for threat closure claims

### Implementation Marker

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ✅ READY FOR CODY IMPLEMENTATION                            ║
║                                                               ║
║   This specification is complete and authoritative.           ║
║   Implementation PAC may now be issued.                       ║
║                                                               ║
║   PAC Reference: PAC-SAM-PDO-SIGNING-DESIGN-01                ║
║   Status: DESIGN COMPLETE / READY FOR LOCK                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

**END OF DOCUMENT**
