# Quantum-Safe Cryptography Boundaries

> **Security Document** — PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01  
> **Version:** 1.0.0  
> **Created:** 2025-12-26  
> **Authority:** SAM (GID-06) — Security & Threat Engineer  
> **Classification:** INTERNAL

---

## Executive Summary

This document defines the quantum-safe cryptography boundaries for ChainBridge governance attestation. As quantum computing advances threaten current cryptographic primitives, we establish migration paths and extensibility points for post-quantum algorithms.

---

## 1. Quantum Threat Timeline

### 1.1 Current Assessment (2025)

```yaml
Threat Level: PREPARING
Quantum Computing Status: "NISQ Era (Noisy Intermediate-Scale Quantum)"
Estimated Timeline to Cryptographic Threat:
  Conservative: 2030-2035
  Aggressive: 2027-2030
  
Current Vulnerable Algorithms:
  - RSA (all key sizes)
  - ECDSA (all curves)
  - ECDH (key exchange)
  - DSA
  
Currently Safe:
  - AES-256 (reduced to 128-bit security)
  - SHA-256 (reduced but sufficient)
  - SHA-3 (designed with quantum in mind)
```

### 1.2 NIST Post-Quantum Standardization

| Algorithm | Type | FIPS | Status | ChainBridge Readiness |
|-----------|------|------|--------|----------------------|
| CRYSTALS-Kyber | KEM | 203 | Standardized | STUB |
| CRYSTALS-Dilithium | Signature | 204 | Standardized | STUB |
| SPHINCS+ | Signature | 205 | Standardized | STUB |
| FALCON | Signature | Draft | Pending | NOT STARTED |

---

## 2. ChainBridge Cryptographic Inventory

### 2.1 Current Implementation

```yaml
Hash Algorithms:
  Primary: SHA-256 (FIPS 180-4)
  Alternative: SHA-3-256 (FIPS 202)
  Chain Hashing: SHA-256
  Status: QUANTUM-RESISTANT (Grover's reduces to 128-bit)

Message Authentication:
  Algorithm: HMAC-SHA256
  Status: QUANTUM-RESISTANT

Random Generation:
  Source: secrets module (CSPRNG)
  Status: QUANTUM-RESISTANT

Digital Signatures:
  Current: NONE (human authority)
  Future: CRYSTALS-Dilithium or SPHINCS+
  Status: MIGRATION PLANNED
```

### 2.2 Quantum Vulnerability Assessment

| Component | Algorithm | Vulnerability | Migration Priority |
|-----------|-----------|---------------|-------------------|
| Content Hash | SHA-256 | LOW (128-bit effective) | LOW |
| Chain Hash | SHA-256 | LOW (128-bit effective) | LOW |
| Ledger Integrity | SHA-256 | LOW (128-bit effective) | LOW |
| Attestation Signature | N/A | N/A (human signed) | MEDIUM |
| Blockchain Anchor | ECDSA | HIGH | HIGH |
| Key Derivation | HKDF-SHA256 | LOW | LOW |

---

## 3. Migration Architecture

### 3.1 Crypto Agility Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ATTESTATION PROVIDER LAYER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  Hash Provider   │  │ Signature Prov.  │  │   KEM Provider   │         │
│  │  (Abstraction)   │  │  (Abstraction)   │  │  (Abstraction)   │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│           │                     │                     │                    │
│  ┌────────┴─────────────────────┴─────────────────────┴─────────┐         │
│  │                    CRYPTO AGILITY LAYER                       │         │
│  │  - Algorithm registry                                         │         │
│  │  - Version negotiation                                        │         │
│  │  - Migration support                                          │         │
│  └───────────────────────────────────────────────────────────────┘         │
│           │                     │                     │                    │
│  ┌────────┴─────────┐  ┌────────┴─────────┐  ┌────────┴─────────┐         │
│  │ Classical Algos  │  │  Hybrid Algos    │  │ Post-Quantum     │         │
│  │ - SHA-256        │  │ - ECDSA+Dilithium│  │ - CRYSTALS-Dil.  │         │
│  │ - SHA-3          │  │ - RSA+Kyber      │  │ - SPHINCS+       │         │
│  │ - ECDSA          │  │                  │  │ - CRYSTALS-Kyber │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Algorithm Identifier Scheme

```yaml
Algorithm Identifiers:
  # Hash algorithms
  hash.sha256:        "HASH-SHA256-V1"
  hash.sha3_256:      "HASH-SHA3-256-V1"
  hash.sha512:        "HASH-SHA512-V1"
  hash.shake256:      "HASH-SHAKE256-V1"
  
  # Classical signatures
  sig.ecdsa_p256:     "SIG-ECDSA-P256-V1"
  sig.ed25519:        "SIG-ED25519-V1"
  sig.rsa_pss:        "SIG-RSA-PSS-V1"
  
  # Post-quantum signatures
  sig.dilithium2:     "SIG-DILITHIUM2-V1"
  sig.dilithium3:     "SIG-DILITHIUM3-V1"
  sig.dilithium5:     "SIG-DILITHIUM5-V1"
  sig.sphincs_sha2:   "SIG-SPHINCS-SHA2-V1"
  sig.sphincs_shake:  "SIG-SPHINCS-SHAKE-V1"
  
  # Hybrid signatures
  sig.ecdsa_dilithium: "SIG-HYBRID-ECDSA-DILITHIUM-V1"
  
  # Key encapsulation
  kem.kyber512:       "KEM-KYBER512-V1"
  kem.kyber768:       "KEM-KYBER768-V1"
  kem.kyber1024:      "KEM-KYBER1024-V1"
```

### 3.3 Attestation Schema with Algorithm Binding

```json
{
  "attestation_v2": {
    "attestation_id": "ATT-xxx",
    "artifact_hash": {
      "algorithm": "HASH-SHA256-V1",
      "value": "abc123...",
      "fallback_algorithm": "HASH-SHA3-256-V1",
      "fallback_value": "def456..."
    },
    "signature": {
      "algorithm": "SIG-HYBRID-ECDSA-DILITHIUM-V1",
      "classical": {
        "algorithm": "SIG-ECDSA-P256-V1",
        "value": "sig1..."
      },
      "post_quantum": {
        "algorithm": "SIG-DILITHIUM3-V1",
        "value": "sig2..."
      }
    },
    "timestamp": "2025-12-26T00:00:00Z",
    "chain_reference": {
      "type": "merkle_root",
      "value": "root123..."
    }
  }
}
```

---

## 4. Migration Phases

### Phase 1: Preparation (Current)

```yaml
Status: IN PROGRESS
Timeline: 2025 Q1-Q2

Actions:
  - Define crypto agility interfaces ✅
  - Implement algorithm abstraction ✅
  - Create stub implementations ✅
  - Document migration boundaries ✅
  
Deliverables:
  - AttestationProvider protocol
  - CryptoAlgorithm enum
  - Algorithm identifier scheme
  - Quantum-safe boundaries document
```

### Phase 2: Hybrid Implementation (2025 Q3-Q4)

```yaml
Status: PLANNED
Timeline: 2025 Q3-Q4

Actions:
  - Integrate liboqs or pqcrypto library
  - Implement CRYSTALS-Dilithium signatures
  - Implement hybrid signature scheme
  - Add algorithm negotiation
  
Deliverables:
  - Working Dilithium implementation
  - Hybrid ECDSA+Dilithium attestation
  - Algorithm version negotiation
  - Performance benchmarks
```

### Phase 3: Transition (2026)

```yaml
Status: PLANNED
Timeline: 2026

Actions:
  - Default to hybrid signatures
  - Phase out classical-only paths
  - Implement key rotation
  - Update blockchain anchoring
  
Deliverables:
  - Hybrid-default attestation
  - Key migration procedures
  - Updated threat model
  - Compliance documentation
```

### Phase 4: Post-Quantum Default (2027+)

```yaml
Status: FUTURE
Timeline: 2027+

Actions:
  - Default to post-quantum only
  - Deprecate classical algorithms
  - Full key rotation
  - Archive classical attestations
  
Deliverables:
  - Post-quantum default
  - Classical deprecation
  - Migration completion report
```

---

## 5. Implementation Boundaries

### 5.1 Stable Interfaces (Do Not Change)

```python
# These interfaces are stable and MUST remain backward compatible

class AttestationProvider(Protocol):
    """Stable provider interface."""
    
    def attest(
        self,
        artifact_id: str,
        artifact_type: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttestationResult:
        ...
    
    def verify(
        self,
        attestation_id: str,
        expected_hash: Optional[str] = None,
    ) -> AttestationResult:
        ...

@dataclass(frozen=True)
class AttestationResult:
    """Stable result structure."""
    attestation_id: str
    artifact_hash: str
    status: AttestationStatus
    timestamp: datetime
    provider_type: str
    # ... stable fields
```

### 5.2 Extension Points

```python
# These are designated extension points for quantum migration

class CryptoProvider(Protocol):
    """Extension point for cryptographic operations."""
    
    @property
    def algorithm_id(self) -> str:
        """Algorithm identifier (e.g., 'SIG-DILITHIUM3-V1')."""
        ...
    
    @property
    def is_post_quantum(self) -> bool:
        """True if algorithm is quantum-resistant."""
        ...

class HashProvider(CryptoProvider):
    """Extension point for hash algorithms."""
    
    def hash(self, data: bytes) -> bytes:
        ...

class SignatureProvider(CryptoProvider):
    """Extension point for signature algorithms."""
    
    def sign(self, data: bytes, private_key: bytes) -> bytes:
        ...
    
    def verify(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        ...

class KEMProvider(CryptoProvider):
    """Extension point for key encapsulation."""
    
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Returns (ciphertext, shared_secret)."""
        ...
    
    def decapsulate(self, ciphertext: bytes, private_key: bytes) -> bytes:
        """Returns shared_secret."""
        ...
```

### 5.3 Forbidden Changes

```yaml
Forbidden Changes (Breaking):
  - Removing attestation_id from AttestationResult
  - Changing hash output format
  - Removing backward compatibility
  - Silent algorithm substitution
  - Weakening security guarantees

Required for Changes:
  - New PAC with security review
  - Migration plan documentation
  - Backward compatibility layer
  - Version bump in algorithm ID
```

---

## 6. Security Considerations

### 6.1 Harvest Now, Decrypt Later (HNDL)

```yaml
Threat: Adversary records attestations today, breaks with future quantum computer
Severity: MEDIUM (signatures/KEMs) / LOW (hashes)

Mitigations:
  - Use hybrid signatures NOW for high-value attestations
  - Avoid long-term secrets in attestations
  - Plan for re-attestation after migration
  - Document attestation dates for audit
```

### 6.2 Implementation Risks

```yaml
Risks:
  - Side-channel attacks on PQ implementations
  - Implementation bugs in new algorithms
  - Performance degradation
  - Compatibility issues

Mitigations:
  - Use vetted libraries (liboqs, pqcrypto)
  - Extensive testing before production
  - Performance benchmarking
  - Fallback mechanisms
```

### 6.3 Algorithm Agility Risks

```yaml
Risks:
  - Downgrade attacks
  - Algorithm confusion
  - Version negotiation vulnerabilities

Mitigations:
  - Minimum algorithm version enforcement
  - Clear algorithm negotiation protocol
  - Signature over algorithm choice
```

---

## 7. Compliance Considerations

| Framework | Requirement | PQ Impact | Action |
|-----------|-------------|-----------|--------|
| SOX | Integrity | LOW | Document migration plan |
| SOC 2 | Cryptographic controls | MEDIUM | Update control descriptions |
| NIST | Algorithm compliance | HIGH | Follow FIPS 203/204/205 |
| ISO 27001 | Crypto policy | MEDIUM | Update crypto policy |
| PCI-DSS | Strong cryptography | HIGH | Monitor PCI PQ guidance |

---

## 8. Recommendations

### Immediate Actions

1. **Complete crypto agility implementation** — ensure all cryptographic operations go through abstraction layer
2. **Monitor NIST updates** — track FIPS 203/204/205 finalization
3. **Evaluate PQ libraries** — assess liboqs, pqcrypto, BoringSSL PQ

### Short-Term (6 months)

1. **Implement Dilithium signatures** — start with hybrid mode
2. **Benchmark performance** — ensure acceptable latency
3. **Update threat model** — include PQ considerations

### Long-Term (12+ months)

1. **Default to hybrid** — ECDSA+Dilithium for all new attestations
2. **Plan classical deprecation** — establish timeline
3. **Archive migration** — re-attest historical records if needed

---

🔴 **SAM (GID-06)** — Security & Threat Engineer  
📋 **PAC:** PAC-SAM-P01-ATTESTATION-PROVIDER-READINESS-01  
🔒 **Classification:** INTERNAL
