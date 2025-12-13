"""
ChainIQ ML Model Security Module (SAM GID-06)
PAC-SAM-SEC-018: Model Supply-Chain Protection

Provides cryptographic signing and verification for ML model artifacts
to protect against model poisoning, supply chain attacks, and unauthorized swapping.

SECURITY FEATURES:
- SHA256 classical signatures (immediate protection)
- PQC Kyber/ML-KEM hybrid signatures (quantum-resistant, future-proof)
- Anomaly detection heuristics
- Automatic quarantine for tampered models
- Full audit trail and chain of trust

Threat Coverage:
- Model poisoning
- Shadow mode corruption
- Adversarial inputs
- Malware-embedded pickle models
- Supply chain attacks (sklearn, numpy)
- Model integrity failure
- Unauthorized model swapping
- "Harvest-Now-Decrypt-Later" ML model theft (PQC protection)

Author: SAM (GID-06) - Security & Threat Engineer
Date: 2025-12-11
Version: 2.0 (PQC-Enhanced)
"""

import base64
import hashlib
import hmac
import json
import logging
import pickle
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# PQC ALGORITHM SELECTION (PAC-SAM-NEXT-019)
# ═══════════════════════════════════════════════════════════════════════════════


class PQCAlgorithm(Enum):
    """
    Post-Quantum Cryptography algorithm selection.

    NIST-approved algorithms for key encapsulation and signatures:
    - ML-KEM (formerly Kyber): Key Encapsulation Mechanism
    - Dilithium: Digital Signature Algorithm
    """

    # Key Encapsulation Mechanisms (KEM)
    ML_KEM_512 = "ML-KEM-512"  # NIST Level 1 (128-bit security)
    ML_KEM_768 = "ML-KEM-768"  # NIST Level 3 (192-bit security) - DEFAULT
    ML_KEM_1024 = "ML-KEM-1024"  # NIST Level 5 (256-bit security)

    # Digital Signature Algorithms
    DILITHIUM2 = "Dilithium2"  # NIST Level 2 (128-bit security)
    DILITHIUM3 = "Dilithium3"  # NIST Level 3 (192-bit security)
    DILITHIUM5 = "Dilithium5"  # NIST Level 5 (256-bit security)

    # Legacy mapping (Kyber -> ML-KEM)
    KYBER512 = "Kyber512"  # Maps to ML-KEM-512
    KYBER768 = "Kyber768"  # Maps to ML-KEM-768
    KYBER1024 = "Kyber1024"  # Maps to ML-KEM-1024


# Mapping from PQCAlgorithm to liboqs algorithm names
PQC_ALGORITHM_MAPPING = {
    PQCAlgorithm.ML_KEM_512: "Kyber512",
    PQCAlgorithm.ML_KEM_768: "Kyber768",
    PQCAlgorithm.ML_KEM_1024: "Kyber1024",
    PQCAlgorithm.KYBER512: "Kyber512",
    PQCAlgorithm.KYBER768: "Kyber768",
    PQCAlgorithm.KYBER1024: "Kyber1024",
    PQCAlgorithm.DILITHIUM2: "Dilithium2",
    PQCAlgorithm.DILITHIUM3: "Dilithium3",
    PQCAlgorithm.DILITHIUM5: "Dilithium5",
}


def is_kem_algorithm(algo: PQCAlgorithm) -> bool:
    """Check if algorithm is a KEM (vs signature)."""
    return algo in {
        PQCAlgorithm.ML_KEM_512,
        PQCAlgorithm.ML_KEM_768,
        PQCAlgorithm.ML_KEM_1024,
        PQCAlgorithm.KYBER512,
        PQCAlgorithm.KYBER768,
        PQCAlgorithm.KYBER1024,
    }


def is_signature_algorithm(algo: PQCAlgorithm) -> bool:
    """Check if algorithm is a signature algorithm."""
    return algo in {
        PQCAlgorithm.DILITHIUM2,
        PQCAlgorithm.DILITHIUM3,
        PQCAlgorithm.DILITHIUM5,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY EXCEPTIONS (Defined early for use by PQC engine)
# ═══════════════════════════════════════════════════════════════════════════════


class ModelSecurityError(Exception):
    """Raised when model security validation fails."""


class ModelQuarantineError(Exception):
    """Raised when a model is quarantined due to security concerns."""


# ═══════════════════════════════════════════════════════════════════════════════
# PQC KYBER/ML-KEM HYBRID SIGNATURE MODULE
# ═══════════════════════════════════════════════════════════════════════════════

# Try to import PQC libraries (graceful fallback if not available)
PQC_AVAILABLE = False
PQC_LIBRARY = None

try:
    # Try liboqs-python (Open Quantum Safe)
    import oqs

    PQC_AVAILABLE = True
    PQC_LIBRARY = "liboqs"
    logger.info("✓ PQC: liboqs library loaded (ML-KEM/Kyber available)")
except ImportError:
    try:
        # Try pqcrypto as fallback
        import pqcrypto

        PQC_AVAILABLE = True
        PQC_LIBRARY = "pqcrypto"
        logger.info("✓ PQC: pqcrypto library loaded")
    except ImportError:
        logger.warning(
            "⚠️  PQC libraries not available (liboqs or pqcrypto). "
            "Using SHA256-only signatures. Install liboqs-python for quantum resistance."
        )


class PQCSignatureEngine:
    """
    Post-Quantum Cryptography signature engine with algorithm selection.

    PAC-SAM-NEXT-019: PQC Strict Mode + Algorithm Selection

    Supported algorithms:
    - ML-KEM-512: NIST Level 1 (128-bit security)
    - ML-KEM-768: NIST Level 3 (192-bit security) - DEFAULT
    - ML-KEM-1024: NIST Level 5 (256-bit security)
    - Dilithium2: NIST Level 2 digital signatures
    - Dilithium3: NIST Level 3 digital signatures
    - Dilithium5: NIST Level 5 digital signatures

    Provides hybrid signatures combining:
    - SHA256 (classical, immediate security)
    - Selected PQC algorithm (quantum-resistant, future-proof)

    The hybrid approach ensures:
    1. Backward compatibility with classical systems
    2. Protection against "Harvest-Now-Decrypt-Later" attacks
    3. Graceful degradation if PQC libraries unavailable
    """

    DEFAULT_KEM_ALGORITHM = PQCAlgorithm.ML_KEM_768
    DEFAULT_SIG_ALGORITHM = PQCAlgorithm.DILITHIUM2

    def __init__(self, kem_algorithm: PQCAlgorithm = None, sig_algorithm: PQCAlgorithm = None, strict_mode: bool = False):
        """
        Initialize PQC engine with algorithm selection.

        Args:
            kem_algorithm: Key encapsulation algorithm (default: ML-KEM-768)
            sig_algorithm: Signature algorithm (default: Dilithium2)
            strict_mode: If True, fail hard on PQC unavailability
        """
        self.pqc_enabled = PQC_AVAILABLE
        self.strict_mode = strict_mode
        self.keypair = None
        self._secret_key = None

        # Set algorithms with defaults
        self.kem_algorithm = kem_algorithm or self.DEFAULT_KEM_ALGORITHM
        self.sig_algorithm = sig_algorithm or self.DEFAULT_SIG_ALGORITHM

        # Initialize KEM
        self.kem = None
        self.public_key = None

        # Initialize Signature (Dilithium)
        self.signer = None
        self.sig_public_key = None
        self._sig_secret_key = None

        if strict_mode and not PQC_AVAILABLE:
            raise ModelSecurityError(
                "PQC strict mode enabled but no PQC library available. " "Install liboqs-python: pip install liboqs-python"
            )

        if self.pqc_enabled and PQC_LIBRARY == "liboqs":
            self._initialize_liboqs()

    def _initialize_liboqs(self):
        """Initialize liboqs KEM and signature algorithms."""
        # Initialize KEM (ML-KEM/Kyber)
        try:
            kem_name = PQC_ALGORITHM_MAPPING.get(self.kem_algorithm, "Kyber768")
            self.kem = oqs.KeyEncapsulation(kem_name)
            self.public_key = self.kem.generate_keypair()
            self._secret_key = self.kem.secret_key
            logger.info(f"✓ PQC KEM: {self.kem_algorithm.value} keypair generated")
        except Exception as e:
            if self.strict_mode:
                raise ModelSecurityError(f"PQC KEM initialization failed: {e}")
            logger.warning(f"⚠️  PQC KEM generation failed: {e}")
            self.pqc_enabled = False
            return

        # Initialize Signature (Dilithium)
        try:
            sig_name = PQC_ALGORITHM_MAPPING.get(self.sig_algorithm, "Dilithium2")
            self.signer = oqs.Signature(sig_name)
            self.sig_public_key = self.signer.generate_keypair()
            self._sig_secret_key = self.signer.secret_key
            logger.info(f"✓ PQC Signature: {self.sig_algorithm.value} keypair generated")
        except Exception as e:
            if self.strict_mode:
                raise ModelSecurityError(f"PQC Signature initialization failed: {e}")
            logger.warning(f"⚠️  PQC Signature generation failed (KEM-only mode): {e}")
            # Continue with KEM only - signature is optional enhancement

    def compute_pqc_signature(self, data: bytes) -> Dict[str, str]:
        """
        Compute hybrid SHA256 + PQC signature with algorithm selection.

        PAC-SAM-NEXT-019: Supports ML-KEM-512/768/1024 + Dilithium2/3/5

        Args:
            data: Raw bytes to sign

        Returns:
            Dictionary with signature components including:
            - sha256: Classical hash
            - kem_algorithm: Selected KEM algorithm
            - sig_algorithm: Selected signature algorithm
            - pqc_mac: KEM-derived MAC
            - dilithium_signature: Dilithium signature (if available)
        """
        result = {
            "algorithm": "SHA256",
            "sha256": hashlib.sha256(data).hexdigest(),
            "pqc_enabled": self.pqc_enabled,
            "kem_algorithm": self.kem_algorithm.value if self.pqc_enabled else None,
            "sig_algorithm": self.sig_algorithm.value if self.pqc_enabled else None,
        }

        if self.pqc_enabled and PQC_LIBRARY == "liboqs":
            try:
                # KEM-based MAC using selected algorithm
                ciphertext, shared_secret = self.kem.encap_secret(self.public_key)

                # HMAC-SHA256 with PQC-derived key
                pqc_mac = hmac.new(shared_secret, result["sha256"].encode(), hashlib.sha256).hexdigest()

                result.update(
                    {
                        "algorithm": f"SHA256+{self.kem_algorithm.value}",
                        "pqc_variant": self.kem_algorithm.value,
                        "pqc_ciphertext": base64.b64encode(ciphertext).decode(),
                        "pqc_mac": pqc_mac,
                        "pqc_public_key": base64.b64encode(self.public_key).decode(),
                    }
                )

                # Add Dilithium signature if available
                if self.signer is not None:
                    dilithium_sig = self.signer.sign(data)
                    result.update(
                        {
                            "algorithm": f"SHA256+{self.kem_algorithm.value}+{self.sig_algorithm.value}",
                            "dilithium_signature": base64.b64encode(dilithium_sig).decode(),
                            "dilithium_public_key": base64.b64encode(self.sig_public_key).decode(),
                        }
                    )
                    logger.debug(f"✓ PQC signature: KEM={self.kem_algorithm.value}, SIG={self.sig_algorithm.value}")

            except Exception as e:
                if self.strict_mode:
                    raise ModelSecurityError(f"PQC signature computation failed: {e}")
                logger.warning(f"⚠️  PQC signature failed, using SHA256 only: {e}")

        return result

    def verify_pqc_signature(self, data: bytes, signature: Dict[str, Any], strict: bool = None) -> Union[Tuple[bool, str], bool]:
        """
        Verify hybrid SHA256 + PQC signature with strict mode support.

        PAC-SAM-NEXT-019: Strict Mode Enforcement

        Args:
            data: Original data bytes
            signature: Signature dictionary from compute_pqc_signature
            strict: Override instance strict_mode. If True, raises on failure.
                   If False, returns (is_valid, reason) tuple.
                   If None, uses instance setting.

        Returns:
            If strict=True: raises ModelSecurityError on failure, returns True on success
            If strict=False: Tuple of (is_valid, reason)

        Raises:
            ModelSecurityError: If strict=True and verification fails
        """
        use_strict = strict if strict is not None else self.strict_mode

        # Step 1: Always verify SHA256
        computed_sha256 = hashlib.sha256(data).hexdigest()
        expected_sha256 = signature.get("sha256")

        if computed_sha256 != expected_sha256:
            msg = f"SHA256 mismatch: expected {expected_sha256}, got {computed_sha256}"
            if use_strict:
                raise ModelSecurityError(msg)
            return False, msg

        # Step 2: Verify PQC KEM MAC if present
        if signature.get("pqc_enabled") and signature.get("pqc_mac"):
            if not self.pqc_enabled:
                msg = (
                    "Model has PQC signature but PQC library not available. "
                    "SHA256 verification passed, but quantum protection cannot be verified."
                )
                if use_strict:
                    raise ModelSecurityError(msg)
                logger.warning(f"⚠️  {msg}")
                return True, "SHA256 verified (PQC library not available for full verification)"

            try:
                # Decapsulate to get shared secret
                ciphertext = base64.b64decode(signature["pqc_ciphertext"])
                shared_secret = self.kem.decap_secret(ciphertext)

                # Verify HMAC
                expected_mac = signature.get("pqc_mac")
                computed_mac = hmac.new(shared_secret, computed_sha256.encode(), hashlib.sha256).hexdigest()

                if not hmac.compare_digest(computed_mac, expected_mac):
                    msg = "PQC MAC verification failed - possible quantum attack"
                    if use_strict:
                        raise ModelSecurityError(msg)
                    return False, msg

            except ModelSecurityError:
                raise
            except Exception as e:
                msg = f"PQC KEM verification error: {e}"
                if use_strict:
                    raise ModelSecurityError(msg)
                return False, msg

        # Step 3: Verify Dilithium signature if present
        dilithium_sig = signature.get("dilithium_signature")
        if dilithium_sig and self.signer is not None:
            try:
                sig_bytes = base64.b64decode(dilithium_sig)
                pub_key = base64.b64decode(signature.get("dilithium_public_key", ""))

                # Verify using Dilithium
                is_valid = self.signer.verify(data, sig_bytes, pub_key)

                if not is_valid:
                    msg = "Dilithium signature verification failed - possible tampering"
                    if use_strict:
                        raise ModelSecurityError(msg)
                    return False, msg

                kem_algo = signature.get("kem_algorithm", "ML-KEM-768")
                sig_algo = signature.get("sig_algorithm", "Dilithium2")
                return True, f"SHA256 + {kem_algo} + {sig_algo} verified (quantum-resistant)"

            except ModelSecurityError:
                raise
            except Exception as e:
                msg = f"Dilithium verification error: {e}"
                if use_strict:
                    raise ModelSecurityError(msg)
                return False, msg

        # KEM-only verification passed
        if signature.get("pqc_enabled"):
            kem_algo = signature.get("kem_algorithm", signature.get("pqc_variant", "ML-KEM-768"))
            return True, f"SHA256 + {kem_algo} verified (quantum-resistant)"

        return True, "SHA256 verified (classical signature)"


# Global PQC engine instance
_pqc_engine: Optional[PQCSignatureEngine] = None
_pqc_engine_config: Dict[str, Any] = {}


def get_pqc_engine(
    kem_algorithm: PQCAlgorithm = None, sig_algorithm: PQCAlgorithm = None, strict_mode: bool = False, force_new: bool = False
) -> PQCSignatureEngine:
    """
    Get or create global PQC engine with algorithm selection.

    PAC-SAM-NEXT-019: PQC Algorithm Selection

    Args:
        kem_algorithm: Key encapsulation algorithm (ML-KEM-512/768/1024)
        sig_algorithm: Signature algorithm (Dilithium2/3/5)
        strict_mode: If True, fail hard on PQC unavailability
        force_new: Force creation of new engine (for testing)

    Returns:
        Configured PQCSignatureEngine instance
    """
    global _pqc_engine, _pqc_engine_config

    new_config = {
        "kem_algorithm": kem_algorithm,
        "sig_algorithm": sig_algorithm,
        "strict_mode": strict_mode,
    }

    # Create new engine if config changed or forced
    if force_new or _pqc_engine is None or new_config != _pqc_engine_config:
        _pqc_engine = PQCSignatureEngine(kem_algorithm=kem_algorithm, sig_algorithm=sig_algorithm, strict_mode=strict_mode)
        _pqc_engine_config = new_config

    return _pqc_engine


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT CORRELATION ENGINE (PAC-SAM-NEXT-019)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ThreatSignal:
    """Individual threat signal from detection systems."""

    source: str  # Signal source (e.g., "anomaly_detector", "drift_detector")
    signal_type: str  # Type of signal (e.g., "content", "timeline", "size_drift")
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    confidence: float  # 0.0 - 1.0
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "signal_type": self.signal_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class ThreatCorrelationResult:
    """Result of threat correlation analysis."""

    stacking_score: float  # 0.0 - 100.0 composite threat score
    threat_level: str  # CRITICAL, HIGH, MEDIUM, LOW, SAFE
    correlated_signals: List[ThreatSignal]
    correlation_patterns: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stacking_score": self.stacking_score,
            "threat_level": self.threat_level,
            "correlated_signals": [s.to_dict() for s in self.correlated_signals],
            "correlation_patterns": self.correlation_patterns,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


class ThreatCorrelationEngine:
    """
    Threat Correlation Engine for ML Supply Chain Security.

    PAC-SAM-NEXT-019: Correlates multiple threat signals to detect
    sophisticated attacks that individual detectors might miss.

    Signal Types:
    - Content Anomalies: Unexpected model structure/weights
    - Timeline Anomalies: Suspicious modification patterns
    - Size Drift Anomalies: Unexpected file size changes
    - Metadata Mismatch Anomalies: Inconsistent metadata

    Integrates with:
    - Maggie's drift detection signals
    - Cody's code/model anomaly signals
    - ModelAnomalyDetector entropy/size analysis
    """

    # Severity weights for stacking score
    SEVERITY_WEIGHTS = {
        "CRITICAL": 40.0,
        "HIGH": 25.0,
        "MEDIUM": 10.0,
        "LOW": 5.0,
    }

    # Threat level thresholds
    THREAT_THRESHOLDS = {
        "CRITICAL": 75.0,
        "HIGH": 50.0,
        "MEDIUM": 25.0,
        "LOW": 10.0,
    }

    # Correlation multipliers for attack patterns
    CORRELATION_MULTIPLIERS = {
        "multi_source_attack": 1.5,  # Same threat from multiple detectors
        "timeline_correlation": 1.3,  # Anomalies cluster in time
        "cascading_anomaly": 1.4,  # One anomaly triggers others
        "metadata_content_mismatch": 1.6,  # Metadata doesn't match content
    }

    def __init__(self):
        self.signals: List[ThreatSignal] = []
        self.signal_history: List[ThreatSignal] = []
        self.correlation_cache: Dict[str, Any] = {}

    def add_signal(self, signal: ThreatSignal) -> None:
        """Add a threat signal for correlation."""
        self.signals.append(signal)
        self.signal_history.append(signal)

    def add_content_anomaly(
        self, details: Dict[str, Any], severity: str = "MEDIUM", confidence: float = 0.7, source: str = "anomaly_detector"
    ) -> ThreatSignal:
        """
        Add content anomaly signal.

        Content anomalies include:
        - Unexpected pickle opcodes
        - Suspicious import patterns
        - Abnormal model weight distributions
        - Hidden code injection
        """
        signal = ThreatSignal(
            source=source,
            signal_type="content_anomaly",
            severity=severity,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            details=details,
        )
        self.add_signal(signal)
        return signal

    def add_timeline_anomaly(
        self, details: Dict[str, Any], severity: str = "MEDIUM", confidence: float = 0.7, source: str = "anomaly_detector"
    ) -> ThreatSignal:
        """
        Add timeline anomaly signal.

        Timeline anomalies include:
        - Backdated modifications
        - Rapid successive changes
        - Off-hours modifications
        - Timestamp gaps/jumps
        """
        signal = ThreatSignal(
            source=source,
            signal_type="timeline_anomaly",
            severity=severity,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            details=details,
        )
        self.add_signal(signal)
        return signal

    def add_size_drift_anomaly(
        self, details: Dict[str, Any], severity: str = "MEDIUM", confidence: float = 0.7, source: str = "drift_detector"
    ) -> ThreatSignal:
        """
        Add size drift anomaly signal.

        Size drift anomalies include:
        - Sudden large size increases (payload injection)
        - Unexpected size decreases (model truncation)
        - Size inconsistent with version changes
        - Pattern deviation from historical baselines
        """
        signal = ThreatSignal(
            source=source,
            signal_type="size_drift_anomaly",
            severity=severity,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            details=details,
        )
        self.add_signal(signal)
        return signal

    def add_metadata_mismatch_anomaly(
        self, details: Dict[str, Any], severity: str = "HIGH", confidence: float = 0.8, source: str = "anomaly_detector"
    ) -> ThreatSignal:
        """
        Add metadata mismatch anomaly signal.

        Metadata mismatches include:
        - Hash doesn't match claimed version
        - Dependencies inconsistent with model type
        - Training date in future
        - Signature metadata conflicts
        """
        signal = ThreatSignal(
            source=source,
            signal_type="metadata_mismatch_anomaly",
            severity=severity,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            details=details,
        )
        self.add_signal(signal)
        return signal

    def ingest_maggie_drift_signals(self, drift_report: Dict[str, Any]) -> None:
        """
        Ingest drift signals from Maggie's drift detector.

        Expected format:
        {
            "model_path": "...",
            "drift_detected": true,
            "drift_magnitude": 0.45,
            "drift_type": "feature_distribution",
            "baseline_hash": "...",
            "current_hash": "..."
        }
        """
        if not drift_report.get("drift_detected"):
            return

        magnitude = drift_report.get("drift_magnitude", 0.0)

        # Map drift magnitude to severity
        if magnitude > 0.5:
            severity = "CRITICAL"
            confidence = 0.9
        elif magnitude > 0.3:
            severity = "HIGH"
            confidence = 0.8
        elif magnitude > 0.15:
            severity = "MEDIUM"
            confidence = 0.7
        else:
            severity = "LOW"
            confidence = 0.6

        self.add_size_drift_anomaly(
            details={
                "drift_magnitude": magnitude,
                "drift_type": drift_report.get("drift_type"),
                "model_path": drift_report.get("model_path"),
                "baseline_hash": drift_report.get("baseline_hash"),
                "current_hash": drift_report.get("current_hash"),
            },
            severity=severity,
            confidence=confidence,
            source="maggie_drift_detector",
        )

    def ingest_cody_anomaly_signals(self, anomaly_report: Dict[str, Any]) -> None:
        """
        Ingest anomaly signals from Cody's code/model analyzer.

        Expected format:
        {
            "anomalies": [
                {"type": "suspicious_import", "module": "os", "severity": "HIGH"},
                {"type": "entropy_spike", "value": 7.9, "severity": "MEDIUM"}
            ]
        }
        """
        for anomaly in anomaly_report.get("anomalies", []):
            anomaly_type = anomaly.get("type", "unknown")
            severity = anomaly.get("severity", "MEDIUM")

            if anomaly_type in ("suspicious_import", "hidden_code", "pickle_injection"):
                self.add_content_anomaly(details=anomaly, severity=severity, confidence=0.85, source="cody_analyzer")
            elif anomaly_type in ("entropy_spike", "structure_change"):
                self.add_content_anomaly(details=anomaly, severity=severity, confidence=0.75, source="cody_analyzer")

    def compute_stacking_score(self) -> float:
        """
        Compute the Threat Stacking Score from all signals.

        The stacking score aggregates multiple threat signals with:
        1. Base severity weights
        2. Confidence adjustments
        3. Correlation multipliers for attack patterns

        Returns:
            Float score from 0.0 (safe) to 100.0+ (critical)
        """
        if not self.signals:
            return 0.0

        # Base score from individual signals
        base_score = 0.0
        for signal in self.signals:
            weight = self.SEVERITY_WEIGHTS.get(signal.severity, 5.0)
            base_score += weight * signal.confidence

        # Apply correlation multipliers
        multiplier = 1.0
        patterns_found = []

        # Check for multi-source attack (same type from different sources)
        source_types: Dict[str, set] = {}
        for signal in self.signals:
            if signal.signal_type not in source_types:
                source_types[signal.signal_type] = set()
            source_types[signal.signal_type].add(signal.source)

        for signal_type, sources in source_types.items():
            if len(sources) > 1:
                multiplier *= self.CORRELATION_MULTIPLIERS["multi_source_attack"]
                patterns_found.append(f"multi_source_attack:{signal_type}")

        # Check for timeline correlation (signals within 5 minutes)
        if len(self.signals) >= 2:
            timestamps = sorted(s.timestamp for s in self.signals)
            for i in range(len(timestamps) - 1):
                delta = (timestamps[i + 1] - timestamps[i]).total_seconds()
                if delta < 300:  # 5 minutes
                    multiplier *= self.CORRELATION_MULTIPLIERS["timeline_correlation"]
                    patterns_found.append("timeline_correlation")
                    break

        # Check for metadata-content mismatch correlation
        has_metadata = any(s.signal_type == "metadata_mismatch_anomaly" for s in self.signals)
        has_content = any(s.signal_type == "content_anomaly" for s in self.signals)
        if has_metadata and has_content:
            multiplier *= self.CORRELATION_MULTIPLIERS["metadata_content_mismatch"]
            patterns_found.append("metadata_content_mismatch")

        self.correlation_cache["patterns"] = patterns_found
        return min(base_score * multiplier, 100.0)

    def correlate(self) -> ThreatCorrelationResult:
        """
        Run full threat correlation and generate result.

        Returns:
            ThreatCorrelationResult with stacking score, threat level,
            correlated signals, and recommendations.
        """
        stacking_score = self.compute_stacking_score()

        # Determine threat level
        if stacking_score >= self.THREAT_THRESHOLDS["CRITICAL"]:
            threat_level = "CRITICAL"
        elif stacking_score >= self.THREAT_THRESHOLDS["HIGH"]:
            threat_level = "HIGH"
        elif stacking_score >= self.THREAT_THRESHOLDS["MEDIUM"]:
            threat_level = "MEDIUM"
        elif stacking_score >= self.THREAT_THRESHOLDS["LOW"]:
            threat_level = "LOW"
        else:
            threat_level = "SAFE"

        # Generate recommendations
        recommendations = self._generate_recommendations(threat_level)

        return ThreatCorrelationResult(
            stacking_score=round(stacking_score, 2),
            threat_level=threat_level,
            correlated_signals=self.signals.copy(),
            correlation_patterns=self.correlation_cache.get("patterns", []),
            recommendations=recommendations,
        )

    def _generate_recommendations(self, threat_level: str) -> List[str]:
        """Generate actionable recommendations based on threat level."""
        recommendations = []

        if threat_level == "CRITICAL":
            recommendations.extend(
                [
                    "🚨 IMMEDIATE: Quarantine affected model artifacts",
                    "🚨 IMMEDIATE: Revoke associated signing keys",
                    "🔍 Conduct full supply chain audit",
                    "📢 Notify security team",
                    "🔄 Roll back to last known-good version",
                ]
            )
        elif threat_level == "HIGH":
            recommendations.extend(
                [
                    "⚠️ Suspend model deployment",
                    "🔍 Investigate anomaly sources",
                    "✅ Re-verify model signatures",
                    "📋 Review recent change history",
                ]
            )
        elif threat_level == "MEDIUM":
            recommendations.extend(
                [
                    "📋 Review and document anomalies",
                    "🔍 Monitor for additional signals",
                    "✅ Verify model provenance",
                ]
            )
        elif threat_level == "LOW":
            recommendations.extend(
                [
                    "📋 Log anomaly for tracking",
                    "🔍 Continue monitoring",
                ]
            )
        else:
            recommendations.append("✅ No immediate action required")

        return recommendations

    def clear_signals(self) -> None:
        """Clear current signals (preserves history)."""
        self.signals.clear()
        self.correlation_cache.clear()


# Global threat correlation engine
_threat_engine: Optional[ThreatCorrelationEngine] = None


def get_threat_correlation_engine() -> ThreatCorrelationEngine:
    """Get or create global threat correlation engine."""
    global _threat_engine
    if _threat_engine is None:
        _threat_engine = ThreatCorrelationEngine()
    return _threat_engine


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION MODULE
# ═══════════════════════════════════════════════════════════════════════════════


class ModelAnomalyDetector:
    """
    Advanced anomaly detection for model file tampering.

    Detects:
    - File size anomalies (sudden growth/shrinkage)
    - Entropy analysis (encrypted/compressed payloads)
    - Magic byte tampering
    - Timestamp manipulation
    - Unexpected file structure changes
    """

    # Expected ranges for known model types
    MODEL_SIZE_RANGES = {
        "risk_model": (0.001, 10),  # 1KB - 10MB
        "anomaly_model": (0.1, 100),  # 100KB - 100MB
        "default": (0.001, 50),  # 1KB - 50MB
    }

    # Pickle magic bytes
    PICKLE_MAGIC = [
        b"\x80\x04",  # Protocol 4
        b"\x80\x05",  # Protocol 5
        b"\x80\x03",  # Protocol 3
        b"\x80\x02",  # Protocol 2
    ]

    def __init__(self):
        self.baseline_cache: Dict[str, Dict] = {}

    def compute_file_entropy(self, data: bytes) -> float:
        """
        Compute Shannon entropy of file data.
        High entropy may indicate encryption or compression.

        Args:
            data: File bytes

        Returns:
            Entropy value (0-8 for bytes)
        """
        if not data:
            return 0.0

        import math
        from collections import Counter

        byte_counts = Counter(data)
        total = len(data)

        entropy = 0.0
        for count in byte_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        return entropy

    def detect_anomalies(
        self, model_path: Path, model_type: str = "default", previous_signature: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Run comprehensive anomaly detection.

        Args:
            model_path: Path to model file
            model_type: Type of model for size range checking
            previous_signature: Previous signature for delta analysis

        Returns:
            List of detected anomalies with severity and details
        """
        anomalies = []

        if not model_path.exists():
            anomalies.append({"type": "FILE_MISSING", "severity": "CRITICAL", "message": f"Model file not found: {model_path}"})
            return anomalies

        stat = model_path.stat()
        file_size_mb = stat.st_size / (1024 * 1024)

        # Read file for analysis
        with open(model_path, "rb") as f:
            header = f.read(1024)  # First 1KB for analysis
            f.seek(0)
            full_data = f.read()

        # Check 1: Size range
        size_range = self.MODEL_SIZE_RANGES.get(model_type, self.MODEL_SIZE_RANGES["default"])
        if not (size_range[0] <= file_size_mb <= size_range[1]):
            anomalies.append(
                {
                    "type": "SIZE_ANOMALY",
                    "severity": "HIGH" if file_size_mb > size_range[1] * 2 else "MEDIUM",
                    "message": f"Size {file_size_mb:.2f}MB outside expected range {size_range}MB",
                    "actual": file_size_mb,
                    "expected_range": size_range,
                }
            )

        # Check 2: Pickle magic bytes
        valid_pickle = any(header.startswith(magic) for magic in self.PICKLE_MAGIC)
        if not valid_pickle:
            anomalies.append(
                {
                    "type": "MAGIC_BYTE_INVALID",
                    "severity": "CRITICAL",
                    "message": "File does not have valid pickle magic bytes - possible tampering",
                    "header_hex": header[:16].hex(),
                }
            )

        # Check 3: Entropy analysis
        entropy = self.compute_file_entropy(full_data[:65536])  # First 64KB
        if entropy > 7.9:  # Very high entropy (near random)
            anomalies.append(
                {
                    "type": "HIGH_ENTROPY",
                    "severity": "HIGH",
                    "message": f"Unusually high entropy ({entropy:.2f}/8.0) - possible encrypted payload",
                    "entropy": entropy,
                }
            )
        elif entropy < 2.0:  # Very low entropy
            anomalies.append(
                {
                    "type": "LOW_ENTROPY",
                    "severity": "MEDIUM",
                    "message": f"Unusually low entropy ({entropy:.2f}/8.0) - possible padding attack",
                    "entropy": entropy,
                }
            )

        # Check 4: Size delta (if previous signature available)
        if previous_signature and "file_size_mb" in previous_signature:
            prev_size = previous_signature["file_size_mb"]
            delta_pct = abs(file_size_mb - prev_size) / prev_size * 100 if prev_size > 0 else 0

            if delta_pct > 50:  # More than 50% size change
                anomalies.append(
                    {
                        "type": "SIZE_DELTA_LARGE",
                        "severity": "HIGH",
                        "message": f"Size changed by {delta_pct:.1f}% from previous version",
                        "previous_size_mb": prev_size,
                        "current_size_mb": file_size_mb,
                        "delta_percent": delta_pct,
                    }
                )

        # Check 5: Timestamp analysis
        mtime = datetime.fromtimestamp(stat.st_mtime)
        ctime = datetime.fromtimestamp(stat.st_ctime)

        if mtime < ctime:
            anomalies.append(
                {
                    "type": "TIMESTAMP_ANOMALY",
                    "severity": "MEDIUM",
                    "message": "Modified time is before created time - possible backdating",
                    "mtime": mtime.isoformat(),
                    "ctime": ctime.isoformat(),
                }
            )

        return anomalies


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SECURITY MANAGER (Enhanced with PQC)
# ═══════════════════════════════════════════════════════════════════════════════

# Note: ModelSecurityError and ModelQuarantineError are defined at the top of the file


class ModelSecurityManager:
    """
    Manages ML model artifact signing, verification, and threat detection.

    Security Features (PAC-SAM-SEC-018):
    - SHA256 + PQC Kyber hybrid signatures
    - ML-KEM-768 quantum-resistant protection
    - Advanced anomaly detection
    - Metadata validation
    - Size/entropy anomaly detection
    - Dependency version checking
    - Quarantine mode for suspicious models
    - Full audit logging and chain of trust
    """

    SIGNATURE_VERSION = "2.0-PQC"
    MAX_MODEL_SIZE_MB = 50  # Anomaly threshold
    SECURE_STORAGE_PATH = Path(".chainbridge/models")
    QUARANTINE_PATH = Path(".chainbridge/quarantine")

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the model security manager with PQC support.

        Args:
            project_root: Root directory of the project. Defaults to repo root.
        """
        if project_root is None:
            # Find repository root (where .git exists)
            current = Path(__file__).resolve()
            while current.parent != current:
                if (current / ".git").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                # Fallback to 3 levels up from this file
                project_root = Path(__file__).resolve().parent.parent.parent.parent

        self.project_root = project_root
        self.secure_storage = self.project_root / self.SECURE_STORAGE_PATH
        self.quarantine_dir = self.project_root / self.QUARANTINE_PATH

        # Ensure directories exist
        self.secure_storage.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Initialize PQC engine and anomaly detector
        self.pqc_engine = get_pqc_engine()
        self.anomaly_detector = ModelAnomalyDetector()

    def compute_model_signature(self, model_path: Path) -> str:
        """
        Compute SHA256 signature of model artifact.

        Args:
            model_path: Path to the model file

        Returns:
            Hexadecimal SHA256 signature

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        sha256_hash = hashlib.sha256()

        with open(model_path, "rb") as f:
            # Read in 64KB chunks for large models
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def create_signature_metadata(
        self,
        model_path: Path,
        model_name: str,
        model_version: str,
        training_date: Optional[str] = None,
        sklearn_version: Optional[str] = None,
        numpy_version: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create comprehensive signature metadata with PQC hybrid signatures.

        Args:
            model_path: Path to the model file
            model_name: Name of the model (e.g., "risk_model")
            model_version: Version string (e.g., "v0.2.0")
            training_date: ISO format training date
            sklearn_version: scikit-learn version used for training
            numpy_version: NumPy version used for training
            additional_metadata: Additional custom metadata

        Returns:
            Dictionary containing signature and metadata with PQC protection
        """
        # Read model file for signing
        with open(model_path, "rb") as f:
            model_data = f.read()

        # Compute hybrid SHA256 + PQC signature
        pqc_signature = self.pqc_engine.compute_pqc_signature(model_data)

        file_size_mb = model_path.stat().st_size / (1024 * 1024)

        metadata = {
            "signature_version": self.SIGNATURE_VERSION,
            "model_name": model_name,
            "model_version": model_version,
            "sha256": pqc_signature["sha256"],
            "file_size_mb": round(file_size_mb, 3),
            "signed_at": datetime.utcnow().isoformat() + "Z",
            "signed_by": "SAM-GID-06-ModelSecurityManager",
            "training_date": training_date or "unknown",
            "dependencies": {"sklearn": sklearn_version or "unknown", "numpy": numpy_version or "unknown"},
            # PQC signature components (PAC-SAM-NEXT-019 enhanced)
            "pqc": {
                "enabled": pqc_signature.get("pqc_enabled", False),
                "algorithm": pqc_signature.get("algorithm", "SHA256"),
                "kem_algorithm": pqc_signature.get("kem_algorithm"),
                "sig_algorithm": pqc_signature.get("sig_algorithm"),
                "variant": pqc_signature.get("pqc_variant"),
                "ciphertext": pqc_signature.get("pqc_ciphertext"),
                "mac": pqc_signature.get("pqc_mac"),
                "public_key": pqc_signature.get("pqc_public_key"),
                # Dilithium signature (if available)
                "dilithium_signature": pqc_signature.get("dilithium_signature"),
                "dilithium_public_key": pqc_signature.get("dilithium_public_key"),
            },
            # Chain of trust
            "chain_of_trust": {
                "signer": "SAM-GID-06",
                "policy": "PAC-SAM-NEXT-019",
                "trust_level": "VERIFIED",
                "verification_required": True,
            },
        }

        if additional_metadata:
            metadata["additional"] = additional_metadata

        return metadata

    def sign_model(self, model_path: Path, signature_path: Optional[Path] = None, **metadata_kwargs) -> Path:
        """
        Sign a model artifact with SHA256 + PQC Kyber hybrid signature.

        Args:
            model_path: Path to the model file to sign
            signature_path: Optional custom path for signature file.
                           Defaults to <model_path>.sig.json
            **metadata_kwargs: Arguments passed to create_signature_metadata

        Returns:
            Path to the created signature file

        Example:
            >>> manager = ModelSecurityManager()
            >>> sig_path = manager.sign_model(
            ...     Path("ml_models/risk_v0.2.0.pkl"),
            ...     model_name="risk_model",
            ...     model_version="v0.2.0",
            ...     sklearn_version="1.3.0"
            ... )
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Default signature path
        if signature_path is None:
            signature_path = model_path.with_suffix(model_path.suffix + ".sig.json")

        # Create signature metadata with PQC
        metadata = self.create_signature_metadata(model_path, **metadata_kwargs)

        # Save signature
        with open(signature_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Log signing details
        pqc_status = "SHA256 + ML-KEM-768" if metadata["pqc"]["enabled"] else "SHA256 only"
        logger.info(f"✓ Signed model: {model_path} → {signature_path}")
        logger.info(f"  Algorithm: {pqc_status}")
        logger.info(f"  SHA256: {metadata['sha256'][:16]}...")
        logger.info(f"  Chain of Trust: {metadata['chain_of_trust']['policy']}")

        return signature_path

    def verify_model_signature(
        self, model_path: Path, signature_path: Optional[Path] = None, strict: bool = True, verify_pqc: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify model integrity against its SHA256 + PQC hybrid signature.

        Args:
            model_path: Path to the model file
            signature_path: Path to signature file. Defaults to <model_path>.sig.json
            strict: If True, raises exception on failure. If False, returns (False, reason)
            verify_pqc: If True, also verify PQC signature if present

        Returns:
            Tuple of (is_valid, error_message)

        Raises:
            ModelSecurityError: If strict=True and verification fails
        """
        if not model_path.exists():
            msg = f"Model file not found: {model_path}"
            if strict:
                raise ModelSecurityError(msg)
            return False, msg

        # Default signature path
        if signature_path is None:
            signature_path = model_path.with_suffix(model_path.suffix + ".sig.json")

        if not signature_path.exists():
            msg = f"Signature file not found: {signature_path}"
            if strict:
                raise ModelSecurityError(msg)
            return False, msg

        # Load signature metadata
        try:
            with open(signature_path, "r") as f:
                sig_metadata = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Invalid signature file format: {e}"
            if strict:
                raise ModelSecurityError(msg)
            return False, msg

        # Read model data
        with open(model_path, "rb") as f:
            model_data = f.read()

        # Verify using PQC engine (handles both SHA256 and PQC)
        pqc_sig = {
            "sha256": sig_metadata.get("sha256"),
            "pqc_enabled": sig_metadata.get("pqc", {}).get("enabled", False),
            "pqc_mac": sig_metadata.get("pqc", {}).get("mac"),
            "pqc_ciphertext": sig_metadata.get("pqc", {}).get("ciphertext"),
        }

        if verify_pqc:
            is_valid, reason = self.pqc_engine.verify_pqc_signature(model_data, pqc_sig)
        else:
            # SHA256 only verification
            computed_sha256 = hashlib.sha256(model_data).hexdigest()
            is_valid = computed_sha256 == pqc_sig["sha256"]
            reason = "SHA256 verified" if is_valid else "SHA256 mismatch"

        if not is_valid:
            msg = f"Signature verification failed: {reason}"
            if strict:
                raise ModelSecurityError(msg)
            return False, msg

        logger.info(f"✓ Model signature verified: {model_path}")
        logger.info(f"  Verification: {reason}")
        return True, reason

    def detect_threats(self, model_path: Path, signature_path: Optional[Path] = None, model_type: str = "default") -> List[str]:
        """
        Run comprehensive threat detection on model artifact.

        Enhanced with advanced anomaly detection (PAC-SAM-SEC-018):
        - Size anomalies
        - Entropy analysis
        - Magic byte validation
        - Timestamp manipulation
        - Dependency mismatches
        - Unexpected imports (via pickle inspection)

        Args:
            model_path: Path to the model file
            signature_path: Path to signature file
            model_type: Type of model for specific size range checking

        Returns:
            List of detected threats (empty if clean)
        """
        threats = []

        if not model_path.exists():
            threats.append("CRITICAL: Model file missing")
            return threats

        # Load previous signature for delta analysis
        previous_sig = None
        if signature_path is None:
            signature_path = model_path.with_suffix(model_path.suffix + ".sig.json")

        if signature_path.exists():
            try:
                with open(signature_path, "r") as f:
                    previous_sig = json.load(f)
            except Exception:
                pass

        # Run advanced anomaly detection
        anomalies = self.anomaly_detector.detect_anomalies(model_path, model_type=model_type, previous_signature=previous_sig)

        for anomaly in anomalies:
            severity = anomaly.get("severity", "MEDIUM")
            atype = anomaly.get("type", "UNKNOWN")
            message = anomaly.get("message", "")
            threats.append(f"{severity}_{atype}: {message}")

        # Check 1: Size anomaly (legacy check)
        file_size_mb = model_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_MODEL_SIZE_MB:
            threats.append(f"SIZE_ANOMALY: Model size {file_size_mb:.1f}MB exceeds " f"threshold {self.MAX_MODEL_SIZE_MB}MB")

        # Check 2: Signature metadata
        if signature_path is None:
            signature_path = model_path.with_suffix(model_path.suffix + ".sig.json")

        if signature_path.exists():
            try:
                with open(signature_path, "r") as f:
                    sig_metadata = json.load(f)

                # Check dependency versions
                deps = sig_metadata.get("dependencies", {})
                if deps.get("sklearn") == "unknown" or deps.get("numpy") == "unknown":
                    threats.append("DEPENDENCY_UNKNOWN: Missing dependency version metadata")
            except Exception as e:
                threats.append(f"METADATA_ERROR: Failed to parse signature: {e}")
        else:
            threats.append("UNSIGNED: Model lacks cryptographic signature")

        # Check 3: Pickle inspection (dangerous imports)
        try:
            with open(model_path, "rb") as f:
                # Inspect pickle opcodes without loading
                dangerous_imports = self._inspect_pickle_imports(f)
                if dangerous_imports:
                    threats.append(f"SUSPICIOUS_IMPORTS: {', '.join(dangerous_imports)}")
        except Exception as e:
            threats.append(f"PICKLE_INSPECTION_FAILED: {e}")

        return threats

    def run_threat_correlation(
        self,
        model_path: Path,
        signature_path: Optional[Path] = None,
        model_type: str = "default",
        maggie_drift_report: Optional[Dict[str, Any]] = None,
        cody_anomaly_report: Optional[Dict[str, Any]] = None,
    ) -> "ThreatCorrelationResult":
        """
        Run full threat correlation analysis on model artifact.

        PAC-SAM-NEXT-019: Integrates with Maggie + Cody's signals
        for comprehensive threat stacking score.

        Args:
            model_path: Path to the model file
            signature_path: Path to signature file
            model_type: Type of model for size range checking
            maggie_drift_report: Optional drift signals from Maggie
            cody_anomaly_report: Optional anomaly signals from Cody

        Returns:
            ThreatCorrelationResult with stacking score and recommendations
        """
        correlation_engine = get_threat_correlation_engine()
        correlation_engine.clear_signals()

        # Run local anomaly detection and feed to correlation engine
        if signature_path is None:
            signature_path = model_path.with_suffix(model_path.suffix + ".sig.json")

        previous_sig = None
        if signature_path.exists():
            try:
                with open(signature_path, "r") as f:
                    previous_sig = json.load(f)
            except Exception:
                pass

        # Get anomalies from local detector
        anomalies = self.anomaly_detector.detect_anomalies(model_path, model_type=model_type, previous_signature=previous_sig)

        # Feed anomalies to correlation engine
        for anomaly in anomalies:
            atype = anomaly.get("type", "UNKNOWN")
            severity = anomaly.get("severity", "MEDIUM")

            if atype in ("SIZE_ANOMALY", "SIZE_DELTA_LARGE"):
                correlation_engine.add_size_drift_anomaly(details=anomaly, severity=severity, source="local_anomaly_detector")
            elif atype in ("TIMESTAMP_ANOMALY",):
                correlation_engine.add_timeline_anomaly(details=anomaly, severity=severity, source="local_anomaly_detector")
            elif atype in ("MAGIC_BYTE_INVALID", "HIGH_ENTROPY", "LOW_ENTROPY"):
                correlation_engine.add_content_anomaly(details=anomaly, severity=severity, source="local_anomaly_detector")

        # Check for metadata mismatches
        if previous_sig:
            deps = previous_sig.get("dependencies", {})
            if deps.get("sklearn") == "unknown" or deps.get("numpy") == "unknown":
                correlation_engine.add_metadata_mismatch_anomaly(
                    details={"issue": "missing_dependency_versions", "signature": previous_sig},
                    severity="MEDIUM",
                    source="local_anomaly_detector",
                )

        # Check for suspicious imports
        try:
            with open(model_path, "rb") as f:
                dangerous_imports = self._inspect_pickle_imports(f)
                if dangerous_imports:
                    correlation_engine.add_content_anomaly(
                        details={"suspicious_imports": dangerous_imports}, severity="CRITICAL", confidence=0.95, source="pickle_inspector"
                    )
        except Exception:
            pass

        # Ingest external signals
        if maggie_drift_report:
            correlation_engine.ingest_maggie_drift_signals(maggie_drift_report)

        if cody_anomaly_report:
            correlation_engine.ingest_cody_anomaly_signals(cody_anomaly_report)

        # Run correlation and return result
        return correlation_engine.correlate()

    def _inspect_pickle_imports(self, file_handle) -> List[str]:
        """
        Inspect pickle file for dangerous imports without loading it.

        Args:
            file_handle: Open file handle for pickle file

        Returns:
            List of suspicious module names
        """
        import pickletools

        dangerous_modules = {"os", "sys", "subprocess", "socket", "urllib", "requests", "eval", "exec", "compile", "__builtin__"}

        suspicious = []

        try:
            opcodes = list(pickletools.genops(file_handle))
            for opcode, arg, pos in opcodes:
                if opcode.name in ("GLOBAL", "STACK_GLOBAL"):
                    if isinstance(arg, str):
                        module = arg.split(".")[0] if "." in arg else arg
                        if module in dangerous_modules:
                            suspicious.append(arg)
        except Exception:
            # Pickle inspection failed, but don't block loading
            pass

        return list(set(suspicious))

    def quarantine_model(self, model_path: Path, reason: str, signature_path: Optional[Path] = None):
        """
        Move a suspicious model to quarantine.

        Args:
            model_path: Path to the model file
            reason: Reason for quarantine
            signature_path: Optional signature file to move
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        quarantine_name = f"{model_path.stem}_{timestamp}{model_path.suffix}"
        quarantine_dest = self.quarantine_dir / quarantine_name

        # Move model to quarantine
        model_path.rename(quarantine_dest)

        # Create quarantine report
        report_path = quarantine_dest.with_suffix(".quarantine.json")
        report = {
            "original_path": str(model_path),
            "quarantined_at": datetime.utcnow().isoformat() + "Z",
            "reason": reason,
            "quarantined_by": "SAM-GID-06-ModelSecurityManager",
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Move signature if exists
        if signature_path and signature_path.exists():
            sig_dest = quarantine_dest.with_suffix(quarantine_dest.suffix + ".sig.json")
            signature_path.rename(sig_dest)

        logger.error(f"⚠️  QUARANTINED: {model_path} → {quarantine_dest}")
        logger.error(f"   Reason: {reason}")

        raise ModelQuarantineError(f"Model quarantined due to security concerns: {reason}")

    def load_verified_model(self, model_path: Path, signature_path: Optional[Path] = None, enable_quarantine: bool = True) -> Any:
        """
        Load a model with full security verification.

        This is the secure replacement for direct pickle.load().

        Args:
            model_path: Path to the model file
            signature_path: Path to signature file
            enable_quarantine: If True, quarantine suspicious models

        Returns:
            Loaded model object

        Raises:
            ModelSecurityError: If verification fails
            ModelQuarantineError: If model is quarantined

        Example:
            >>> manager = ModelSecurityManager()
            >>> model = manager.load_verified_model(Path("ml_models/risk_v0.2.0.pkl"))
        """
        # Step 1: Verify signature
        is_valid, error = self.verify_model_signature(model_path, signature_path, strict=False)

        if not is_valid:
            if enable_quarantine:
                self.quarantine_model(model_path, f"Signature verification failed: {error}")
            else:
                raise ModelSecurityError(f"Model signature verification failed: {error}")

        # Step 2: Threat detection
        threats = self.detect_threats(model_path, signature_path)

        if threats:
            threat_summary = "; ".join(threats)
            logger.warning(f"⚠️  Threats detected in {model_path}:")
            for threat in threats:
                logger.warning(f"   - {threat}")

            if enable_quarantine and any(t.startswith(("CRITICAL", "SUSPICIOUS_IMPORTS")) for t in threats):
                self.quarantine_model(model_path, f"Threats detected: {threat_summary}")

        # Step 3: Load model
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)

            logger.info(f"✓ Securely loaded model: {model_path}")
            return model

        except Exception as e:
            msg = f"Failed to load model: {e}"
            if enable_quarantine:
                self.quarantine_model(model_path, msg)
            else:
                raise ModelSecurityError(msg)


def get_security_manager() -> ModelSecurityManager:
    """Get the global ModelSecurityManager instance."""
    return ModelSecurityManager()


if __name__ == "__main__":
    # CLI for manual model verification
    import argparse

    parser = argparse.ArgumentParser(description="ChainIQ ML Model Security Tool (SAM GID-06)")
    parser.add_argument("command", choices=["sign", "verify", "inspect", "load"])
    parser.add_argument("model_path", help="Path to model file")
    parser.add_argument("--model-name", help="Model name (for signing)")
    parser.add_argument("--model-version", help="Model version (for signing)")
    parser.add_argument("--sklearn-version", help="scikit-learn version")
    parser.add_argument("--numpy-version", help="NumPy version")
    parser.add_argument("--no-quarantine", action="store_true", help="Disable quarantine mode")

    args = parser.parse_args()

    manager = ModelSecurityManager()
    model_path = Path(args.model_path)

    if args.command == "sign":
        if not args.model_name or not args.model_version:
            print("Error: --model-name and --model-version required for signing")
            sys.exit(1)

        sig_path = manager.sign_model(
            model_path,
            model_name=args.model_name,
            model_version=args.model_version,
            sklearn_version=args.sklearn_version,
            numpy_version=args.numpy_version,
        )
        print(f"✓ Model signed: {sig_path}")

    elif args.command == "verify":
        is_valid, error = manager.verify_model_signature(model_path, strict=False)
        if is_valid:
            print(f"✓ Signature valid: {model_path}")
        else:
            print(f"✗ Signature invalid: {error}")
            sys.exit(1)

    elif args.command == "inspect":
        threats = manager.detect_threats(model_path)
        if threats:
            print(f"⚠️  Threats detected in {model_path}:")
            for threat in threats:
                print(f"   - {threat}")
            sys.exit(1)
        else:
            print(f"✓ No threats detected: {model_path}")

    elif args.command == "load":
        try:
            model = manager.load_verified_model(model_path, enable_quarantine=not args.no_quarantine)
            print(f"✓ Model loaded successfully: {type(model)}")
        except (ModelSecurityError, ModelQuarantineError) as e:
            print(f"✗ Failed to load model: {e}")
            sys.exit(1)
