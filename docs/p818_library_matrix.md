# PAC-SEC-P818: PQC Library Compatibility Matrix
## ML-DSA-65 (FIPS 204) Python Library Evaluation

**Evaluation Date:** 2026-01-12
**Environment:** Python 3.11.13, macOS ARM64
**Baseline:** cryptography==46.0.1

---

## Executive Summary

**RECOMMENDED LIBRARY: `pqcrypto==0.3.4`**

| Criteria | Status |
|----------|--------|
| ML-DSA-65 Support | ✅ PASS |
| Python 3.11+ Compatibility | ✅ PASS |
| cryptography==46.0.1 Compatibility | ✅ PASS (no conflicts) |
| License | Apache 2.0 / MIT |
| Native Wheels | ✅ Available (macOS ARM64, Linux x86_64) |
| Sign/Verify Tests | ✅ ALL PASS |

---

## Library Evaluation

### 1. pqcrypto (RECOMMENDED)

| Attribute | Value |
|-----------|-------|
| Package | `pqcrypto` |
| Version | 0.3.4 |
| PyPI | https://pypi.org/project/pqcrypto/ |
| License | Apache 2.0 |
| ML-DSA-65 Support | ✅ YES (`pqcrypto.sign.ml_dsa_65`) |
| Python Compatibility | 3.8+ |
| Native Wheels | macOS (ARM64, x86_64), Linux (x86_64, ARM64), Windows |
| Conflicts | NONE |

**API:**
```python
from pqcrypto.sign import ml_dsa_65

# Key generation
public_key, secret_key = ml_dsa_65.generate_keypair()

# Signing
signature = ml_dsa_65.sign(secret_key, message)

# Verification (returns bool)
is_valid = ml_dsa_65.verify(public_key, message, signature)
```

**Key Sizes (ML-DSA-65):**
- Public Key: 1952 bytes
- Secret Key: 4032 bytes
- Signature: 3309 bytes

**Available Algorithms:**
- `ml_dsa_44` (ML-DSA-44 / Dilithium2)
- `ml_dsa_65` (ML-DSA-65 / Dilithium3) ⭐ TARGET
- `ml_dsa_87` (ML-DSA-87 / Dilithium5)
- `falcon_512`, `falcon_1024`
- `sphincs_*` variants

**VERDICT: ✅ APPROVED FOR USE**

---

### 2. liboqs-python

| Attribute | Value |
|-----------|-------|
| Package | `liboqs-python` |
| Version | 0.14.1 |
| PyPI | https://pypi.org/project/liboqs-python/ |
| License | MIT |
| ML-DSA-65 Support | ✅ YES (via liboqs native library) |
| Python Compatibility | 3.7+ |
| Native Library Required | ❌ YES (liboqs must be installed separately) |

**ISSUE:** Requires separate installation of native `liboqs` library. Auto-install failed with:
```
Error: No oqs shared libraries found
```

**VERDICT: ⚠️ NOT RECOMMENDED (complex native dependency)**

---

### 3. cryptography (Native PQC)

| Attribute | Value |
|-----------|-------|
| Package | `cryptography` |
| Version | 46.0.1 |
| ML-DSA-65 Support | ❌ NO (as of 46.0.1) |

**Test:**
```python
from cryptography.hazmat.primitives.asymmetric import ml_dsa
# ImportError: cannot import name 'ml_dsa'
```

**VERDICT: ❌ NO NATIVE PQC SUPPORT YET**

---

### 4. oqs (PyPI)

| Attribute | Value |
|-----------|-------|
| Package | `oqs` |
| Version | 0.10.2 |
| Purpose | Query language (NOT cryptographic!) |

**VERDICT: ❌ WRONG PACKAGE (naming collision)**

---

### 5. pqcryptography

| Attribute | Value |
|-----------|-------|
| Package | `pqcryptography` |
| Version | 0.0.3 |
| Status | Early development |

**VERDICT: ⚠️ NOT EVALUATED (insufficient maturity)**

---

## Compatibility Matrix

| Package | Version | Python 3.11 | cryptography 46.0.1 | ML-DSA-65 | Recommendation |
|---------|---------|-------------|---------------------|-----------|----------------|
| pqcrypto | 0.3.4 | ✅ | ✅ | ✅ | **USE THIS** |
| liboqs-python | 0.14.1 | ✅ | ✅ | ✅ | Complex setup |
| cryptography | 46.0.1 | ✅ | N/A | ❌ | No PQC yet |
| oqs | 0.10.2 | ✅ | ✅ | ❌ | Wrong package |

---

## Test Results Summary

### pqcrypto==0.3.4 ML-DSA-65 Tests

| Test | Result | Details |
|------|--------|---------|
| Keygen | ✅ PASS | Public: 1952 bytes, Secret: 4032 bytes |
| Sign | ✅ PASS | Signature: 3309 bytes |
| Verify (valid) | ✅ PASS | Returns `True` |
| Verify (invalid) | ✅ PASS | Returns `False` (correct rejection) |

---

## Security Considerations

1. **FIPS 204 Compliance:** `pqcrypto` implements ML-DSA per FIPS 204 draft
2. **Algorithm Selection:** ML-DSA-65 provides NIST Security Level 3 (equivalent to AES-192)
3. **Migration Path:** Direct replacement for ED25519 signatures in `modules/mesh/identity.py`
4. **Key Size Impact:** ML-DSA-65 keys are significantly larger than ED25519:
   - ED25519 Public Key: 32 bytes → ML-DSA-65: 1952 bytes (61x larger)
   - ED25519 Secret Key: 64 bytes → ML-DSA-65: 4032 bytes (63x larger)
   - ED25519 Signature: 64 bytes → ML-DSA-65: 3309 bytes (52x larger)

---

## Conclusion

**Library Selection: `pqcrypto==0.3.4`**

Reasons:
1. Native Python wheels (no complex native library setup)
2. Full ML-DSA-65 support per FIPS 204
3. Zero conflicts with existing cryptography==46.0.1
4. Active maintenance
5. Compatible license (Apache 2.0)
6. Proven sign/verify cycle in test environment

**P818 Invariant Status:**
- INV-PQC-001 (FIPS 204 ML-DSA-65): ✅ SATISFIED
- INV-PQC-002 (Python 3.11+ install): ✅ SATISFIED
- INV-PQC-003 (No cryptography conflict): ✅ SATISFIED
- INV-PQC-004 (Sign/verify test): ✅ SATISFIED
- INV-PQC-005 (Documentation): ✅ SATISFIED

**VERDICT: P818 → PASS**
