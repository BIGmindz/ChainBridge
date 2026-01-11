#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          AEGIS - CRYPTOGRAPHIC SEALING                        ║
║                          PAC-SEC-P777-TITAN-PROTOCOL                          ║
║                                                                              ║
║  "Data without a valid Seal is treated as noise/attack."                     ║
║                                                                              ║
║  Aegis provides:                                                             ║
║    1. HMAC-SHA256 sealing for data integrity                                 ║
║    2. Fail-closed verification (panic on invalid seal)                       ║
║    3. Key rotation support                                                   ║
║    4. Bit-flip detection                                                     ║
║                                                                              ║
║  Invariant Enforced:                                                         ║
║    INV-SEC-013 (Cryptographic Integrity): Unsealed data is REJECTED          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union


# ══════════════════════════════════════════════════════════════════════════════
# SEALED DATA ENVELOPE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SealedEnvelope:
    """
    Cryptographically sealed data envelope.
    
    Contains:
      - payload: The serialized data (JSON bytes)
      - seal: HMAC-SHA256 signature
      - timestamp: When the seal was created
      - key_id: Identifier of the key used (for rotation)
      - nonce: Random value to prevent replay attacks
    """
    
    payload: bytes
    seal: bytes
    timestamp: float
    key_id: str
    nonce: bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize envelope to dictionary."""
        return {
            "payload": self.payload.hex(),
            "seal": self.seal.hex(),
            "timestamp": self.timestamp,
            "key_id": self.key_id,
            "nonce": self.nonce.hex()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SealedEnvelope":
        """Deserialize envelope from dictionary."""
        return cls(
            payload=bytes.fromhex(data["payload"]),
            seal=bytes.fromhex(data["seal"]),
            timestamp=data["timestamp"],
            key_id=data["key_id"],
            nonce=bytes.fromhex(data["nonce"])
        )
        
    def to_bytes(self) -> bytes:
        """Serialize envelope to bytes."""
        return json.dumps(self.to_dict()).encode('utf-8')
        
    @classmethod
    def from_bytes(cls, data: bytes) -> "SealedEnvelope":
        """Deserialize envelope from bytes."""
        return cls.from_dict(json.loads(data.decode('utf-8')))


# ══════════════════════════════════════════════════════════════════════════════
# AEGIS - THE CRYPTOGRAPHIC SHIELD
# ══════════════════════════════════════════════════════════════════════════════

class Aegis:
    """
    Cryptographic sealing service using HMAC-SHA256.
    
    INV-SEC-013: All data must be sealed. Unsealed data is rejected.
    
    Usage:
        aegis = Aegis()  # Generates random key
        # or
        aegis = Aegis(key=b'your-256-bit-key...')
        
        # Seal data
        envelope = aegis.seal({"transaction": "payment", "amount": 1000})
        
        # Verify and unseal (raises AegisError if invalid)
        data = aegis.unseal(envelope)
        
        # Verify only (returns bool)
        is_valid = aegis.verify(envelope)
    """
    
    # Key length: 256 bits (32 bytes)
    KEY_LENGTH = 32
    
    # Nonce length: 128 bits (16 bytes)
    NONCE_LENGTH = 16
    
    # Maximum age for sealed data (default: 1 hour)
    MAX_AGE_SECONDS = 3600
    
    def __init__(
        self,
        key: Optional[bytes] = None,
        key_id: Optional[str] = None,
        max_age: Optional[int] = None
    ):
        """
        Initialize Aegis with a secret key.
        
        Args:
            key: 256-bit secret key (generated if not provided)
            key_id: Identifier for key rotation tracking
            max_age: Maximum age for sealed data in seconds
        """
        if key is None:
            key = secrets.token_bytes(self.KEY_LENGTH)
            
        if len(key) < self.KEY_LENGTH:
            raise AegisError(f"Key must be at least {self.KEY_LENGTH} bytes")
            
        self._key = key[:self.KEY_LENGTH]
        self._key_id = key_id or self._derive_key_id(self._key)
        self._max_age = max_age or self.MAX_AGE_SECONDS
        
        # Statistics
        self._seals_created = 0
        self._seals_verified = 0
        self._seals_rejected = 0
        self._bit_flips_detected = 0
        
    def _derive_key_id(self, key: bytes) -> str:
        """Derive key ID from key (first 8 chars of SHA256)."""
        return hashlib.sha256(key).hexdigest()[:8]
        
    def _compute_hmac(self, data: bytes, nonce: bytes, timestamp: float) -> bytes:
        """Compute HMAC-SHA256 over data + nonce + timestamp."""
        # Construct message: nonce || timestamp || data
        message = nonce + str(timestamp).encode('utf-8') + data
        return hmac.new(self._key, message, hashlib.sha256).digest()
        
    def seal(self, data: Any) -> SealedEnvelope:
        """
        Seal data with HMAC-SHA256.
        
        Args:
            data: Any JSON-serializable data
            
        Returns:
            SealedEnvelope containing the protected data
        """
        # Serialize payload
        payload = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        # Generate nonce
        nonce = secrets.token_bytes(self.NONCE_LENGTH)
        
        # Timestamp
        timestamp = time.time()
        
        # Compute seal
        seal = self._compute_hmac(payload, nonce, timestamp)
        
        self._seals_created += 1
        
        return SealedEnvelope(
            payload=payload,
            seal=seal,
            timestamp=timestamp,
            key_id=self._key_id,
            nonce=nonce
        )
        
    def verify(self, envelope: SealedEnvelope, check_age: bool = True) -> bool:
        """
        Verify seal integrity without extracting data.
        
        Args:
            envelope: The sealed envelope to verify
            check_age: Whether to check timestamp freshness
            
        Returns:
            True if seal is valid, False otherwise
        """
        try:
            self._verify_envelope(envelope, check_age)
            return True
        except AegisError:
            return False
            
    def _verify_envelope(self, envelope: SealedEnvelope, check_age: bool = True) -> None:
        """
        Internal verification with exception on failure.
        
        INV-SEC-013: Fail-closed - any verification failure raises exception.
        """
        # Check key ID matches
        if envelope.key_id != self._key_id:
            self._seals_rejected += 1
            raise AegisError(
                f"Key ID mismatch: expected {self._key_id}, got {envelope.key_id}. "
                "Possible key rotation issue or attack."
            )
            
        # Check timestamp freshness
        if check_age:
            age = time.time() - envelope.timestamp
            if age > self._max_age:
                self._seals_rejected += 1
                raise AegisError(
                    f"Envelope too old: {age:.1f}s > {self._max_age}s. "
                    "Possible replay attack."
                )
            if age < -60:  # Allow 1 minute clock skew
                self._seals_rejected += 1
                raise AegisError(
                    f"Envelope from future: {-age:.1f}s ahead. "
                    "Possible clock manipulation."
                )
                
        # Recompute HMAC
        expected_seal = self._compute_hmac(
            envelope.payload,
            envelope.nonce,
            envelope.timestamp
        )
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(envelope.seal, expected_seal):
            self._seals_rejected += 1
            self._bit_flips_detected += 1
            raise AegisError(
                "SEAL VERIFICATION FAILED. "
                "Data integrity compromised - possible bit flip or tampering."
            )
            
        self._seals_verified += 1
        
    def unseal(self, envelope: SealedEnvelope, check_age: bool = True) -> Any:
        """
        Verify and extract data from sealed envelope.
        
        INV-SEC-013: Raises AegisError if seal is invalid (fail-closed).
        
        Args:
            envelope: The sealed envelope to unseal
            check_age: Whether to check timestamp freshness
            
        Returns:
            The original data
            
        Raises:
            AegisError: If verification fails
        """
        # Verify first (fail-closed)
        self._verify_envelope(envelope, check_age)
        
        # Extract payload
        return json.loads(envelope.payload.decode('utf-8'))
        
    def seal_bytes(self, data: bytes) -> SealedEnvelope:
        """Seal raw bytes (stored as base64 in JSON)."""
        import base64
        return self.seal({"__bytes__": base64.b64encode(data).decode('ascii')})
        
    def unseal_bytes(self, envelope: SealedEnvelope) -> bytes:
        """Unseal raw bytes."""
        import base64
        data = self.unseal(envelope)
        if isinstance(data, dict) and "__bytes__" in data:
            return base64.b64decode(data["__bytes__"])
        raise AegisError("Envelope does not contain bytes payload")
        
    def rotate_key(self, new_key: bytes) -> "Aegis":
        """
        Create new Aegis instance with rotated key.
        
        Returns new instance; original is unchanged for
        verifying old seals during transition period.
        """
        return Aegis(key=new_key)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get sealing statistics."""
        return {
            "key_id": self._key_id,
            "seals_created": self._seals_created,
            "seals_verified": self._seals_verified,
            "seals_rejected": self._seals_rejected,
            "bit_flips_detected": self._bit_flips_detected,
            "max_age_seconds": self._max_age
        }


class AegisError(Exception):
    """
    Aegis verification failure.
    
    INV-SEC-013: This exception indicates data integrity compromise.
    The system should treat this as a potential attack.
    """
    pass


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def generate_key() -> bytes:
    """Generate a new 256-bit cryptographic key."""
    return secrets.token_bytes(Aegis.KEY_LENGTH)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive key from password using PBKDF2."""
    import hashlib
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100_000,
        dklen=Aegis.KEY_LENGTH
    )


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> bool:
    """Self-test for Aegis cryptographic sealing."""
    
    print("\n" + "=" * 60)
    print("           AEGIS SELF-TEST")
    print("           Cryptographic Sealing")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic seal/unseal
    tests_total += 1
    print("\n[TEST 1] Basic Seal/Unseal...")
    try:
        aegis = Aegis()
        original_data = {"transaction_id": "TX001", "amount": 1000, "currency": "USD"}
        
        envelope = aegis.seal(original_data)
        recovered_data = aegis.unseal(envelope)
        
        assert recovered_data == original_data
        print(f"  Original: {original_data}")
        print(f"  Recovered: {recovered_data}")
        print("  ✅ PASSED: Data integrity preserved")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 2: Tamper detection (bit flip)
    tests_total += 1
    print("\n[TEST 2] Tamper Detection (Bit Flip)...")
    try:
        aegis = Aegis()
        envelope = aegis.seal({"secret": "classified"})
        
        # Tamper with payload (simulate bit flip)
        tampered_payload = bytearray(envelope.payload)
        tampered_payload[5] ^= 0xFF  # Flip bits
        tampered_envelope = SealedEnvelope(
            payload=bytes(tampered_payload),
            seal=envelope.seal,
            timestamp=envelope.timestamp,
            key_id=envelope.key_id,
            nonce=envelope.nonce
        )
        
        # Verification must fail
        try:
            aegis.unseal(tampered_envelope)
            print("  ❌ FAILED: Tampered data was accepted!")
        except AegisError as e:
            print(f"  Tampering detected: {e}")
            print("  ✅ PASSED: Bit flip detected and rejected")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 3: Wrong key rejection
    tests_total += 1
    print("\n[TEST 3] Wrong Key Rejection...")
    try:
        aegis1 = Aegis()
        aegis2 = Aegis()  # Different key
        
        envelope = aegis1.seal({"confidential": True})
        
        # Try to unseal with wrong key
        try:
            aegis2.unseal(envelope)
            print("  ❌ FAILED: Wrong key accepted!")
        except AegisError as e:
            print(f"  Wrong key rejected: {e}")
            print("  ✅ PASSED: Cross-key attack prevented")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 4: Replay protection (age check)
    tests_total += 1
    print("\n[TEST 4] Replay Protection...")
    try:
        aegis = Aegis(max_age=1)  # 1 second max age
        envelope = aegis.seal({"action": "transfer"})
        
        # Wait for expiry
        time.sleep(1.5)
        
        # Try to use expired envelope
        try:
            aegis.unseal(envelope)
            print("  ❌ FAILED: Expired envelope accepted!")
        except AegisError as e:
            print(f"  Replay blocked: {e}")
            print("  ✅ PASSED: Stale data rejected")
            tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 5: Serialization round-trip
    tests_total += 1
    print("\n[TEST 5] Envelope Serialization...")
    try:
        aegis = Aegis()
        original_data = {"complex": {"nested": [1, 2, 3]}}
        
        envelope = aegis.seal(original_data)
        
        # Serialize to dict and back
        envelope_dict = envelope.to_dict()
        restored_envelope = SealedEnvelope.from_dict(envelope_dict)
        
        # Verify restored envelope
        recovered_data = aegis.unseal(restored_envelope)
        assert recovered_data == original_data
        
        print(f"  Serialized envelope: {len(json.dumps(envelope_dict))} bytes")
        print("  ✅ PASSED: Envelope survives serialization")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Test 6: Bytes sealing
    tests_total += 1
    print("\n[TEST 6] Raw Bytes Sealing...")
    try:
        aegis = Aegis()
        original_bytes = b'\x00\x01\x02\x03\xff\xfe\xfd'
        
        envelope = aegis.seal_bytes(original_bytes)
        recovered_bytes = aegis.unseal_bytes(envelope)
        
        assert recovered_bytes == original_bytes
        print(f"  Original: {original_bytes.hex()}")
        print(f"  Recovered: {recovered_bytes.hex()}")
        print("  ✅ PASSED: Binary data integrity preserved")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        
    # Summary
    print("\n" + "=" * 60)
    print(f"                RESULTS: {tests_passed}/{tests_total} PASSED")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n🛡️  AEGIS OPERATIONAL")
        print("INV-SEC-013 (Cryptographic Integrity): ✅ ENFORCED")
        print("\n\"Data without a valid Seal is noise.\"")
        
    return tests_passed == tests_total


if __name__ == "__main__":
    import sys
    success = _self_test()
    sys.exit(0 if success else 1)
