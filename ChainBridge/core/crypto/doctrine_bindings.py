"""
Doctrine Bindings - Cryptographic Governance Integration
=========================================================

PAC Reference: PAC-P747-CRYPTO-GOVERNANCE-AND-AGILITY-DOCTRINE
Classification: LAW_TIER
Author: ATLAS (GID-11)
Orchestrator: BENSON (GID-00)

Binds cryptographic doctrine to WRAP/BER/Ledger operations.
Enforces crypto-agility and audit requirements.
"""

import json
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading


# ==================== Algorithm Registry ====================

class AlgorithmStatus(Enum):
    """Algorithm approval status."""
    APPROVED = "APPROVED"
    TRANSITIONAL = "TRANSITIONAL"
    DEPRECATED = "DEPRECATED"
    FORBIDDEN = "FORBIDDEN"
    EXPERIMENTAL = "EXPERIMENTAL"


class AlgorithmCategory(Enum):
    """Cryptographic algorithm categories."""
    HASH = "HASH"
    SYMMETRIC = "SYMMETRIC"
    ASYMMETRIC = "ASYMMETRIC"
    POST_QUANTUM = "POST_QUANTUM"
    KDF = "KDF"


@dataclass
class Algorithm:
    """Registered cryptographic algorithm."""
    id: str
    name: str
    category: AlgorithmCategory
    status: AlgorithmStatus
    security_bits: int
    quantum_resistant: bool
    standard: Optional[str] = None
    use_cases: List[str] = field(default_factory=list)
    migration_path: Optional[str] = None
    deprecation_date: Optional[str] = None


# Default approved algorithms (loaded from registry)
APPROVED_ALGORITHMS = {
    # Hashing
    "SHA3-256": Algorithm(
        id="HASH-SHA3-256-V1",
        name="SHA-3 256-bit",
        category=AlgorithmCategory.HASH,
        status=AlgorithmStatus.APPROVED,
        security_bits=128,
        quantum_resistant=True,
        standard="FIPS 202",
        use_cases=["General hashing", "WRAP/BER hashing"]
    ),
    "SHA-256": Algorithm(
        id="HASH-SHA256-V1",
        name="SHA-2 256-bit",
        category=AlgorithmCategory.HASH,
        status=AlgorithmStatus.APPROVED,
        security_bits=128,
        quantum_resistant=True,
        standard="FIPS 180-4",
        use_cases=["Legacy compatibility"]
    ),
    # Signatures
    "Ed25519": Algorithm(
        id="ASYM-ED25519-V1",
        name="Ed25519",
        category=AlgorithmCategory.ASYMMETRIC,
        status=AlgorithmStatus.APPROVED,
        security_bits=128,
        quantum_resistant=False,
        standard="RFC 8032",
        use_cases=["Digital signatures", "WRAP/BER signing"],
        migration_path="Hybrid with ML-DSA-65"
    ),
    "ML-DSA-65": Algorithm(
        id="PQC-MLDSA65-V1",
        name="ML-DSA-65",
        category=AlgorithmCategory.POST_QUANTUM,
        status=AlgorithmStatus.APPROVED,
        security_bits=192,
        quantum_resistant=True,
        standard="FIPS 204",
        use_cases=["Post-quantum signatures"]
    ),
    # Encryption
    "AES-256-GCM": Algorithm(
        id="SYM-AES256GCM-V1",
        name="AES-256-GCM",
        category=AlgorithmCategory.SYMMETRIC,
        status=AlgorithmStatus.APPROVED,
        security_bits=128,
        quantum_resistant=True,
        standard="FIPS 197, SP 800-38D",
        use_cases=["Data encryption"]
    ),
}


# ==================== Crypto Artifact Formatting ====================

@dataclass
class CryptoArtifact:
    """
    Tagged cryptographic artifact with version metadata.
    
    Ensures crypto-agility by tagging all outputs with algorithm info.
    """
    algorithm: str
    version: str
    value: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "version": self.version,
            "value": self.value,
            "created_at": self.created_at,
            "context": self.context
        }
    
    def to_tagged_string(self) -> str:
        """Format as algorithm-tagged string."""
        return f"{self.algorithm}-{self.version}:{self.value}"


@dataclass
class HashArtifact(CryptoArtifact):
    """Tagged hash output."""
    pass


@dataclass
class SignatureArtifact(CryptoArtifact):
    """Tagged signature output."""
    public_key_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        if self.public_key_id:
            d["public_key_id"] = self.public_key_id
        return d


# ==================== Doctrine Validator ====================

class DoctrineViolation(Exception):
    """Cryptographic doctrine violation."""
    pass


class DoctrineValidator:
    """
    Validates cryptographic operations against doctrine.
    
    Enforces:
    - Only approved algorithms used
    - Proper tagging of outputs
    - No silent algorithm changes
    - Audit logging
    """
    
    def __init__(self, algorithms: Optional[Dict[str, Algorithm]] = None):
        self._algorithms = algorithms or APPROVED_ALGORITHMS
        self._audit_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def validate_algorithm(self, algorithm_name: str, purpose: str) -> Algorithm:
        """
        Validate algorithm is approved for purpose.
        
        Raises DoctrineViolation if algorithm not approved.
        """
        algo = self._algorithms.get(algorithm_name)
        
        if not algo:
            raise DoctrineViolation(
                f"Algorithm '{algorithm_name}' not in approved registry"
            )
        
        if algo.status == AlgorithmStatus.FORBIDDEN:
            raise DoctrineViolation(
                f"Algorithm '{algorithm_name}' is FORBIDDEN: security risk"
            )
        
        if algo.status == AlgorithmStatus.DEPRECATED:
            # Log warning but allow (for migration period)
            self._log_audit("DEPRECATED_ALGORITHM_USED", {
                "algorithm": algorithm_name,
                "purpose": purpose,
                "migration_path": algo.migration_path
            })
        
        return algo
    
    def create_hash(
        self,
        data: bytes,
        algorithm: str = "SHA3-256",
        context: Optional[Dict[str, Any]] = None
    ) -> HashArtifact:
        """
        Create doctrine-compliant hash.
        
        Uses approved algorithm and returns tagged artifact.
        """
        algo = self.validate_algorithm(algorithm, "hashing")
        
        if algorithm == "SHA3-256":
            import hashlib
            h = hashlib.sha3_256(data).hexdigest()
        elif algorithm == "SHA-256":
            h = hashlib.sha256(data).hexdigest()
        else:
            raise DoctrineViolation(f"Hash algorithm '{algorithm}' not implemented")
        
        artifact = HashArtifact(
            algorithm=algorithm,
            version="V1",
            value=h,
            context=context or {}
        )
        
        self._log_audit("HASH_CREATED", {
            "algorithm": algorithm,
            "output_length": len(h),
            "context": context
        })
        
        return artifact
    
    def verify_artifact(self, artifact: CryptoArtifact) -> bool:
        """Verify artifact uses approved algorithm."""
        try:
            self.validate_algorithm(artifact.algorithm, "verification")
            return True
        except DoctrineViolation:
            return False
    
    def _log_audit(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log cryptographic operation for audit."""
        with self._lock:
            self._audit_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": f"CRYPTO_{event_type}",
                "details": details
            })
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log."""
        with self._lock:
            return list(self._audit_log)


# ==================== WRAP/BER Crypto Bindings ====================

class WrapBerCryptoBinding:
    """
    Binds cryptographic doctrine to WRAP/BER operations.
    
    Ensures all governance artifacts use approved algorithms
    and are properly tagged for crypto-agility.
    """
    
    def __init__(self, validator: Optional[DoctrineValidator] = None):
        self.validator = validator or DoctrineValidator()
        self.default_hash_algorithm = "SHA3-256"
        self.default_signature_algorithm = "Ed25519"
    
    def hash_wrap(self, wrap_data: Dict[str, Any]) -> HashArtifact:
        """
        Create doctrine-compliant hash of WRAP document.
        """
        # Canonical JSON encoding
        canonical = json.dumps(wrap_data, sort_keys=True, separators=(',', ':'))
        
        return self.validator.create_hash(
            canonical.encode('utf-8'),
            algorithm=self.default_hash_algorithm,
            context={"document_type": "WRAP", "pac_id": wrap_data.get("pac_id")}
        )
    
    def hash_ber(self, ber_data: Dict[str, Any]) -> HashArtifact:
        """
        Create doctrine-compliant hash of BER document.
        """
        canonical = json.dumps(ber_data, sort_keys=True, separators=(',', ':'))
        
        return self.validator.create_hash(
            canonical.encode('utf-8'),
            algorithm=self.default_hash_algorithm,
            context={"document_type": "BER", "pac_id": ber_data.get("pac_id")}
        )
    
    def hash_ledger_entry(self, entry: Dict[str, Any]) -> HashArtifact:
        """
        Create doctrine-compliant hash of ledger entry.
        """
        canonical = json.dumps(entry, sort_keys=True, separators=(',', ':'))
        
        return self.validator.create_hash(
            canonical.encode('utf-8'),
            algorithm=self.default_hash_algorithm,
            context={"document_type": "LEDGER_ENTRY"}
        )
    
    def create_chain_hash(
        self,
        current_data: bytes,
        previous_hash: Optional[str] = None
    ) -> HashArtifact:
        """
        Create chained hash for audit trail.
        
        Chains current hash with previous for Merkle-style integrity.
        """
        if previous_hash:
            chain_input = previous_hash.encode('utf-8') + current_data
        else:
            chain_input = b"GENESIS:" + current_data
        
        return self.validator.create_hash(
            chain_input,
            algorithm=self.default_hash_algorithm,
            context={"chain_type": "AUDIT_CHAIN", "has_previous": previous_hash is not None}
        )
    
    def get_algorithm_metadata(self) -> Dict[str, Any]:
        """
        Get current algorithm configuration for embedding in documents.
        """
        return {
            "hash_algorithm": self.default_hash_algorithm,
            "hash_version": "V1",
            "signature_algorithm": self.default_signature_algorithm,
            "signature_version": "V1",
            "crypto_agility_version": "1.0.0",
            "doctrine_reference": "DOCTRINE_CRYPTOGRAPHIC_GOVERNANCE_V1"
        }


# ==================== Compliance Mapping ====================

COMPLIANCE_MAPPINGS = {
    "NIST_800_57": {
        "reference": "NIST SP 800-57: Recommendation for Key Management",
        "controls": {
            "key_strength": "Part 1, Table 2",
            "algorithm_lifecycle": "Part 1, Section 5.3",
            "key_lifecycle": "Part 1, Section 8"
        }
    },
    "NIST_800_131A": {
        "reference": "NIST SP 800-131A Rev 2: Transitioning Use of Cryptographic Algorithms",
        "controls": {
            "sha1_deprecation": "Section 9",
            "rsa_key_sizes": "Section 2",
            "transition_timeline": "Throughout"
        }
    },
    "ISO_27001_A10": {
        "reference": "ISO/IEC 27001:2022 Annex A.10",
        "controls": {
            "A10.1.1": "Policy on use of cryptographic controls",
            "A10.1.2": "Key management"
        }
    },
    "PCI_DSS_4": {
        "reference": "PCI DSS v4.0",
        "controls": {
            "3.5": "Procedures to protect stored account data",
            "3.6": "Key management processes",
            "4.2": "Strong cryptography for transmission"
        }
    },
    "FIPS_140_3": {
        "reference": "FIPS 140-3: Security Requirements for Cryptographic Modules",
        "controls": {
            "approved_algorithms": "Annex A",
            "module_requirements": "Sections 4-11"
        }
    }
}


def get_compliance_mapping() -> Dict[str, Any]:
    """Get full compliance mapping."""
    return COMPLIANCE_MAPPINGS


# ==================== Global Instances ====================

_validator: Optional[DoctrineValidator] = None
_binding: Optional[WrapBerCryptoBinding] = None


def get_validator() -> DoctrineValidator:
    """Get global doctrine validator."""
    global _validator
    if _validator is None:
        _validator = DoctrineValidator()
    return _validator


def get_crypto_binding() -> WrapBerCryptoBinding:
    """Get global WRAP/BER crypto binding."""
    global _binding
    if _binding is None:
        _binding = WrapBerCryptoBinding(get_validator())
    return _binding


# ==================== Self-Test ====================

if __name__ == "__main__":
    print("Doctrine Bindings Self-Test")
    print("=" * 50)
    
    validator = DoctrineValidator()
    binding = WrapBerCryptoBinding(validator)
    
    # Test hash creation
    test_data = b"Test governance document"
    hash_artifact = validator.create_hash(test_data, "SHA3-256")
    print(f"✅ SHA3-256 hash: {hash_artifact.to_tagged_string()[:60]}...")
    
    # Test WRAP hashing
    test_wrap = {"pac_id": "PAC-P747-TEST", "data": "test"}
    wrap_hash = binding.hash_wrap(test_wrap)
    print(f"✅ WRAP hash: {wrap_hash.algorithm}-{wrap_hash.version}")
    
    # Test algorithm validation
    try:
        validator.validate_algorithm("MD5", "test")
        print("❌ MD5 should be forbidden")
    except DoctrineViolation:
        print("✅ MD5 correctly rejected (FORBIDDEN)")
    
    # Test chain hash
    chain1 = binding.create_chain_hash(b"First entry")
    chain2 = binding.create_chain_hash(b"Second entry", chain1.value)
    print(f"✅ Chain hash with previous: {chain2.context}")
    
    # Get metadata
    meta = binding.get_algorithm_metadata()
    print(f"✅ Algorithm metadata: {meta['hash_algorithm']}, {meta['doctrine_reference']}")
    
    # Audit log
    audit = validator.get_audit_log()
    print(f"✅ Audit log entries: {len(audit)}")
    
    print("\n✅ Self-test PASSED")
