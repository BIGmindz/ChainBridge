# PAC-SEC-P819: Threat Model

## Executive Summary

This document provides security threat analysis for the hybrid ED25519 + ML-DSA-65 identity implementation. The goal is to identify attack surfaces and define mitigations before implementation.

---

## Threat Categories

### 1. Cryptographic Threats

| ID | Threat | Likelihood | Impact | Mitigation |
|----|--------|------------|--------|------------|
| T-CRYPTO-001 | Quantum computer breaks ED25519 | Medium (5-15 years) | Critical | Hybrid signatures - ML-DSA-65 remains secure |
| T-CRYPTO-002 | ML-DSA-65 implementation flaw | Low | Critical | Use audited library, test vectors validation |
| T-CRYPTO-003 | Weak randomness in keygen | Low | Critical | Use OS entropy via `secrets` module |
| T-CRYPTO-004 | Side-channel attack on signing | Medium | High | Note: `dilithium-py` not constant-time - document limitation |
| T-CRYPTO-005 | Signature malleability | Low | Medium | Both ED25519 and ML-DSA-65 have unique signatures |

### 2. Key Management Threats

| ID | Threat | Likelihood | Impact | Mitigation |
|----|--------|------------|--------|------------|
| T-KEY-001 | Private key exposure in logs | Medium | Critical | Redact all key material in logging |
| T-KEY-002 | Private key in memory too long | Medium | High | Clear key bytes after use where possible |
| T-KEY-003 | Weak file permissions | Medium | High | Enforce 0o600 on key files |
| T-KEY-004 | Key material in error messages | Medium | High | Sanitize exceptions before logging |
| T-KEY-005 | Key backup without encryption | Low | High | Document secure backup procedures |

### 3. Protocol Threats

| ID | Threat | Likelihood | Impact | Mitigation |
|----|--------|------------|--------|------------|
| T-PROTO-001 | Signature replay attack | Medium | High | Include timestamp/nonce in signed data |
| T-PROTO-002 | Challenge-response replay | Medium | High | Time-bound challenges with nonce |
| T-PROTO-003 | Downgrade to ED25519-only | Medium | High | Enforce minimum signature mode |
| T-PROTO-004 | Node ID collision | Very Low | High | SHA256 collision resistant |
| T-PROTO-005 | Federation ID spoofing | Low | Medium | Sign federation membership claims |

### 4. Implementation Threats

| ID | Threat | Likelihood | Impact | Mitigation |
|----|--------|------------|--------|------------|
| T-IMPL-001 | Deserialization of malformed keys | Medium | High | Strict validation on load |
| T-IMPL-002 | Buffer overflow (signature size) | Low | High | Python memory-safe, but validate sizes |
| T-IMPL-003 | Exception leaks sensitive data | Medium | Medium | Custom exception hierarchy |
| T-IMPL-004 | Timing oracle on verify | Medium | Medium | Note: Python timing variable - document |
| T-IMPL-005 | Dependency confusion attack | Low | Critical | Pin exact versions in requirements |

---

## Attack Surface Analysis

### External Attack Surface

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL ATTACKERS                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      NETWORK BOUNDARY                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Attack Vectors:                                               │  │
│  │   • Malformed signature payloads                             │  │
│  │   • Oversized key/signature data (DoS)                       │  │
│  │   • Challenge-response manipulation                          │  │
│  │   • Replay of captured signatures                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      IDENTITY MODULE                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Entry Points:                                                 │  │
│  │   • verify(message, signature)                               │  │
│  │   • verify_challenge_response(challenge, response)            │  │
│  │   • from_public_key(public_key_bytes, name)                  │  │
│  │   • load(path)                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Internal Attack Surface

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRIVILEGED ATTACKERS                           │
│  (compromised process, malicious insider)                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      INTERNAL ASSETS                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ High-Value Targets:                                           │  │
│  │   • Private key bytes in memory                              │  │
│  │   • Private key file on disk                                 │  │
│  │   • Signing operation (timing analysis)                      │  │
│  │   • Log files with potential key leakage                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Security Controls

### Control Matrix

| Control ID | Control | Threats Mitigated | Implementation |
|------------|---------|-------------------|----------------|
| C-001 | Key material redaction in logs | T-KEY-001, T-KEY-004 | `observability/logging.py` |
| C-002 | Strict input validation | T-IMPL-001, T-IMPL-002 | `validation.py` |
| C-003 | File permission enforcement | T-KEY-003 | `save()` method |
| C-004 | Timestamp/nonce in signatures | T-PROTO-001, T-PROTO-002 | Protocol layer |
| C-005 | Minimum signature mode policy | T-PROTO-003 | `constants.py` config |
| C-006 | Dependency pinning | T-IMPL-005 | `requirements-pqc.txt` |
| C-007 | Custom exception hierarchy | T-IMPL-003 | `errors.py` |
| C-008 | Size validation on deserialize | T-IMPL-001 | `serialization.py` |

---

## Known Limitations

### 1. Timing Side Channels

**Issue:** `dilithium-py` is a pure Python implementation and is NOT constant-time.

**Risk Level:** Medium

**Mitigation:** 
- Document this limitation clearly
- For high-security deployments, recommend `liboqs` backend (P820 scope)
- Signing/verification times will vary based on input

### 2. Memory Safety

**Issue:** Python does not guarantee secure memory clearing.

**Risk Level:** Medium

**Mitigation:**
- Clear sensitive bytes with `del` and garbage collection hints
- Document that memory forensics could recover keys
- For high-security, recommend hardware security module (HSM)

### 3. No Hardware Binding

**Issue:** Keys are software-only, not bound to hardware.

**Risk Level:** Medium

**Mitigation:**
- Document secure key storage best practices
- Future: Support HSM/TPM integration (P821+ scope)

---

## Security Invariants

### INV-SEC-P819-001: No Private Key Logging

**Statement:** Private key material SHALL NEVER appear in any log output.

**Verification:** 
- Code review of all logging statements
- Test: Sign operations with debug logging enabled, grep for key patterns

### INV-SEC-P819-002: Signature Integrity

**Statement:** A signature created by `sign()` MUST verify with `verify()` using the corresponding public key.

**Verification:**
- 100% of test cases verify roundtrip integrity

### INV-SEC-P819-003: Invalid Signature Rejection

**Statement:** `verify()` MUST return False for any tampered message or wrong public key.

**Verification:**
- Explicit test cases for tampering scenarios
- Fuzz testing with malformed signatures

### INV-SEC-P819-004: Key File Permissions

**Statement:** Identity files containing private keys MUST have mode 0o600.

**Verification:**
- Post-save permission check in tests

### INV-SEC-P819-005: Version Tagging

**Statement:** All serialized identity data MUST include a version tag.

**Verification:**
- Schema validation on load

---

## Recommendations

### Pre-Implementation

1. **Pin dilithium-py==1.4.0** - Exact version for reproducibility
2. **Create test vectors** - Capture known-good signatures for regression
3. **Define error codes** - Consistent error handling

### Implementation

1. **Input validation first** - Validate all external inputs before processing
2. **Fail secure** - On any error, deny rather than allow
3. **Minimize key exposure** - Load keys only when needed

### Post-Implementation

1. **Security review** - Sentinel (GID-03) audit of final code
2. **Penetration testing** - Attempt attack scenarios
3. **Dependency audit** - Verify no vulnerable transitive dependencies

---

## Threat Model Acceptance

| Residual Risk | Accepted | Rationale |
|---------------|----------|-----------|
| Timing side channels | Yes | Pure Python constraint; document for users |
| Memory forensics | Yes | Python constraint; document for users |
| Quantum threat to ED25519 | Yes | Mitigated by hybrid ML-DSA-65 |

---

## Phase 1 Deliverable Checklist

- [x] Threat categories identified
- [x] Attack surface analyzed
- [x] Security controls defined
- [x] Known limitations documented
- [x] Security invariants specified
- [x] Recommendations provided

**Threat Model Status: COMPLETE**

---

*Generated by Sentinel (GID-03) | PAC-SEC-P819 Phase 1*
