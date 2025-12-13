"""
Unit Tests for ML Model Security Module
SAM (GID-06) - Security & Threat Engineer
PAC-SAM-SEC-018: Model Supply-Chain Protection

Tests cryptographic signing, verification, PQC hybrid signatures,
anomaly detection, and threat detection.
"""

import json
import pickle
import tempfile
from pathlib import Path

import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.model_security import (  # PAC-SAM-NEXT-019 additions
    ModelAnomalyDetector,
    ModelQuarantineError,
    ModelSecurityError,
    ModelSecurityManager,
    PQCAlgorithm,
    PQCSignatureEngine,
    ThreatCorrelationEngine,
    ThreatCorrelationResult,
    ThreatSignal,
    get_pqc_engine,
    get_threat_correlation_engine,
    is_kem_algorithm,
    is_signature_algorithm,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_model():
    """Create a sample sklearn model."""
    model = Pipeline([("scaler", StandardScaler()), ("classifier", RandomForestClassifier(n_estimators=10, random_state=42))])
    return model


@pytest.fixture
def security_manager(temp_dir):
    """Create a ModelSecurityManager instance."""
    return ModelSecurityManager(project_root=temp_dir)


@pytest.fixture
def pqc_engine():
    """Create a PQC signature engine."""
    return PQCSignatureEngine()


@pytest.fixture
def anomaly_detector():
    """Create an anomaly detector instance."""
    return ModelAnomalyDetector()


class TestPQCSignatureEngine:
    """Test Post-Quantum Cryptography signature engine."""

    def test_pqc_engine_initialization(self, pqc_engine):
        """Test PQC engine initializes correctly."""
        assert pqc_engine is not None
        # pqc_enabled depends on library availability
        assert isinstance(pqc_engine.pqc_enabled, bool)

    def test_compute_sha256_signature(self, pqc_engine):
        """Test SHA256 signature computation (always available)."""
        data = b"test model data"
        sig = pqc_engine.compute_pqc_signature(data)

        assert "sha256" in sig
        assert len(sig["sha256"]) == 64  # SHA256 hex
        assert "algorithm" in sig
        assert "SHA256" in sig["algorithm"]

    def test_pqc_signature_contains_metadata(self, pqc_engine):
        """Test PQC signature includes PQC metadata."""
        data = b"test model data for PQC"
        sig = pqc_engine.compute_pqc_signature(data)

        assert "pqc_enabled" in sig

        if sig["pqc_enabled"]:
            assert "pqc_variant" in sig
            assert "pqc_mac" in sig
            assert "ML-KEM" in sig.get("pqc_variant", "") or "Kyber" in sig.get("pqc_variant", "")

    def test_verify_sha256_signature(self, pqc_engine):
        """Test SHA256 verification (classical)."""
        data = b"test verification data"
        sig = pqc_engine.compute_pqc_signature(data)

        is_valid, reason = pqc_engine.verify_pqc_signature(data, sig)

        assert is_valid
        assert "verified" in reason.lower()

    def test_verify_tampered_data(self, pqc_engine):
        """Test detection of tampered data."""
        data = b"original data"
        sig = pqc_engine.compute_pqc_signature(data)

        tampered_data = b"tampered data"
        is_valid, reason = pqc_engine.verify_pqc_signature(tampered_data, sig)

        assert not is_valid
        assert "mismatch" in reason.lower()


class TestModelAnomalyDetector:
    """Test advanced anomaly detection."""

    def test_compute_entropy(self, anomaly_detector):
        """Test entropy computation."""
        # Random data should have high entropy
        import os

        random_data = os.urandom(1024)
        high_entropy = anomaly_detector.compute_file_entropy(random_data)

        # Repeated data should have low entropy
        repeated_data = b"A" * 1024
        low_entropy = anomaly_detector.compute_file_entropy(repeated_data)

        assert high_entropy > 7.0  # Near maximum for bytes
        assert low_entropy < 0.1  # Near zero

    def test_detect_size_anomaly(self, anomaly_detector, temp_dir):
        """Test size anomaly detection."""
        model_path = temp_dir / "large_model.pkl"

        # Create large file (outside risk_model range)
        with open(model_path, "wb") as f:
            f.write(b"X" * (20 * 1024 * 1024))  # 20MB

        anomalies = anomaly_detector.detect_anomalies(model_path, model_type="risk_model")  # Expected range: 1KB - 10MB

        size_anomalies = [a for a in anomalies if "SIZE" in a.get("type", "")]
        assert len(size_anomalies) > 0

    def test_detect_invalid_pickle_magic(self, anomaly_detector, temp_dir):
        """Test detection of invalid pickle magic bytes."""
        model_path = temp_dir / "bad_model.pkl"

        # Create file with wrong magic bytes
        with open(model_path, "wb") as f:
            f.write(b"NOT_PICKLE_DATA" + b"\x00" * 1000)

        anomalies = anomaly_detector.detect_anomalies(model_path)

        magic_anomalies = [a for a in anomalies if "MAGIC" in a.get("type", "")]
        assert len(magic_anomalies) > 0
        assert any(a.get("severity") == "CRITICAL" for a in magic_anomalies)


class TestModelSigning:
    """Test model signing functionality."""

    def test_compute_signature(self, security_manager, sample_model, temp_dir):
        """Test SHA256 signature computation."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        signature = security_manager.compute_model_signature(model_path)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex length
        assert signature.isalnum()

    def test_signature_consistency(self, security_manager, sample_model, temp_dir):
        """Test that signature is deterministic."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        sig1 = security_manager.compute_model_signature(model_path)
        sig2 = security_manager.compute_model_signature(model_path)

        assert sig1 == sig2

    def test_sign_model(self, security_manager, sample_model, temp_dir):
        """Test model signing creates valid signature file with PQC metadata."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        sig_path = security_manager.sign_model(
            model_path, model_name="test_model", model_version="v1.0.0", sklearn_version="1.3.0", numpy_version="1.24.3"
        )

        assert sig_path.exists()
        assert sig_path.suffix == ".json"

        # Validate signature content
        with open(sig_path) as f:
            sig_data = json.load(f)

        assert sig_data["model_name"] == "test_model"
        assert sig_data["model_version"] == "v1.0.0"
        assert "sha256" in sig_data
        assert sig_data["dependencies"]["sklearn"] == "1.3.0"

        # Verify PQC and chain of trust metadata (v2.0 + PAC-SAM-NEXT-019)
        assert "pqc" in sig_data
        assert "chain_of_trust" in sig_data
        assert sig_data["chain_of_trust"]["policy"] == "PAC-SAM-NEXT-019"
        assert sig_data["signature_version"] == "2.0-PQC"
        assert sig_data["dependencies"]["numpy"] == "1.24.3"


class TestModelVerification:
    """Test model verification functionality."""

    def test_verify_valid_signature(self, security_manager, sample_model, temp_dir):
        """Test verification of valid signature."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(model_path, model_name="test_model", model_version="v1.0.0")

        # Verify
        is_valid, message = security_manager.verify_model_signature(model_path, strict=False)

        assert is_valid
        # On success, message contains verification info (not an error)
        assert message is None or "verified" in message.lower()

    def test_verify_tampered_model(self, security_manager, sample_model, temp_dir):
        """Test detection of tampered model."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(model_path, model_name="test_model", model_version="v1.0.0")

        # Tamper with model
        with open(model_path, "ab") as f:
            f.write(b"MALICIOUS_DATA")

        # Verify should fail
        is_valid, error = security_manager.verify_model_signature(model_path, strict=False)

        assert not is_valid
        assert "mismatch" in error.lower()

    def test_verify_missing_signature(self, security_manager, sample_model, temp_dir):
        """Test handling of missing signature file."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # No signature file created
        is_valid, error = security_manager.verify_model_signature(model_path, strict=False)

        assert not is_valid
        assert "not found" in error.lower()

    def test_verify_strict_mode(self, security_manager, sample_model, temp_dir):
        """Test strict mode raises exceptions."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Should raise exception in strict mode
        with pytest.raises(ModelSecurityError):
            security_manager.verify_model_signature(model_path, strict=True)


class TestThreatDetection:
    """Test threat detection heuristics."""

    def test_detect_size_anomaly(self, security_manager, temp_dir):
        """Test detection of oversized models."""
        model_path = temp_dir / "huge_model.pkl"

        # Create a large fake model (over 50MB threshold)
        with open(model_path, "wb") as f:
            f.write(b"X" * (60 * 1024 * 1024))  # 60MB

        threats = security_manager.detect_threats(model_path)

        assert any("SIZE_ANOMALY" in t for t in threats)

    def test_detect_unsigned_model(self, security_manager, sample_model, temp_dir):
        """Test detection of unsigned models."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        threats = security_manager.detect_threats(model_path)

        assert any("UNSIGNED" in t for t in threats)

    def test_no_threats_for_valid_model(self, security_manager, sample_model, temp_dir):
        """Test that valid models pass all checks."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(
            model_path, model_name="test_model", model_version="v1.0.0", sklearn_version="1.3.0", numpy_version="1.24.3"
        )

        threats = security_manager.detect_threats(model_path)

        # Should only have minor warnings, no critical threats
        critical_threats = [t for t in threats if "CRITICAL" in t or "UNSIGNED" in t]
        assert len(critical_threats) == 0


class TestQuarantine:
    """Test model quarantine functionality."""

    def test_quarantine_model(self, security_manager, sample_model, temp_dir):
        """Test quarantining a suspicious model."""
        model_path = temp_dir / "bad_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Quarantine should move file and create report
        with pytest.raises(ModelQuarantineError):
            security_manager.quarantine_model(model_path, reason="Test quarantine")

        # Original file should be gone
        assert not model_path.exists()

        # Quarantine directory should contain the file
        quarantined_files = list(security_manager.quarantine_dir.glob("*.pkl"))
        assert len(quarantined_files) == 1

        # Report should exist
        reports = list(security_manager.quarantine_dir.glob("*.quarantine.json"))
        assert len(reports) == 1

        # Validate report
        with open(reports[0]) as f:
            report = json.load(f)

        assert report["reason"] == "Test quarantine"
        assert "quarantined_at" in report


class TestSecureLoading:
    """Test secure model loading."""

    def test_load_verified_model(self, security_manager, sample_model, temp_dir):
        """Test loading a properly signed model."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(
            model_path, model_name="test_model", model_version="v1.0.0", sklearn_version="1.3.0", numpy_version="1.24.3"
        )

        # Load should succeed
        loaded_model = security_manager.load_verified_model(model_path, enable_quarantine=False)

        assert loaded_model is not None
        assert isinstance(loaded_model, Pipeline)

    def test_load_tampered_model_quarantines(self, security_manager, sample_model, temp_dir):
        """Test that tampered models are quarantined."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(model_path, model_name="test_model", model_version="v1.0.0")

        # Tamper
        with open(model_path, "ab") as f:
            f.write(b"TAMPERED")

        # Load should quarantine
        with pytest.raises(ModelQuarantineError):
            security_manager.load_verified_model(model_path, enable_quarantine=True)

    def test_load_unsigned_model_fails(self, security_manager, sample_model, temp_dir):
        """Test that unsigned models cannot be loaded."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # No signature - should fail
        with pytest.raises((ModelSecurityError, ModelQuarantineError)):
            security_manager.load_verified_model(model_path, enable_quarantine=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC-SAM-NEXT-019: PQC Strict Mode + Threat Correlation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPQCAlgorithmSelection:
    """Test PAC-SAM-NEXT-019 PQC Algorithm Selection."""

    def test_pqc_algorithm_enum(self):
        """Test PQCAlgorithm enum values."""

        # KEM algorithms
        assert PQCAlgorithm.ML_KEM_512.value == "ML-KEM-512"
        assert PQCAlgorithm.ML_KEM_768.value == "ML-KEM-768"
        assert PQCAlgorithm.ML_KEM_1024.value == "ML-KEM-1024"

        # Signature algorithms
        assert PQCAlgorithm.DILITHIUM2.value == "Dilithium2"
        assert PQCAlgorithm.DILITHIUM3.value == "Dilithium3"
        assert PQCAlgorithm.DILITHIUM5.value == "Dilithium5"

    def test_algorithm_selection_helpers(self):
        """Test algorithm classification helpers."""

        # KEM algorithms
        assert is_kem_algorithm(PQCAlgorithm.ML_KEM_512)
        assert is_kem_algorithm(PQCAlgorithm.ML_KEM_768)
        assert not is_kem_algorithm(PQCAlgorithm.DILITHIUM2)

        # Signature algorithms
        assert is_signature_algorithm(PQCAlgorithm.DILITHIUM2)
        assert is_signature_algorithm(PQCAlgorithm.DILITHIUM3)
        assert not is_signature_algorithm(PQCAlgorithm.ML_KEM_768)

    def test_pqc_engine_with_algorithm_selection(self):
        """Test PQC engine initialization with custom algorithms."""
        from app.ml.model_security import PQCSignatureEngine

        engine = PQCSignatureEngine(kem_algorithm=PQCAlgorithm.ML_KEM_512, sig_algorithm=PQCAlgorithm.DILITHIUM2, strict_mode=False)

        assert engine.kem_algorithm == PQCAlgorithm.ML_KEM_512
        assert engine.sig_algorithm == PQCAlgorithm.DILITHIUM2

    def test_get_pqc_engine_with_config(self):
        """Test get_pqc_engine with algorithm configuration."""

        engine = get_pqc_engine(kem_algorithm=PQCAlgorithm.ML_KEM_768, sig_algorithm=PQCAlgorithm.DILITHIUM2, force_new=True)

        assert engine is not None
        assert engine.kem_algorithm == PQCAlgorithm.ML_KEM_768


class TestStrictModeEnforcement:
    """Test PAC-SAM-NEXT-019 Strict Mode."""

    def test_strict_mode_raises_on_verification_failure(self):
        """Test strict=True raises immediately on failure."""
        from app.ml.model_security import ModelSecurityError, PQCSignatureEngine

        engine = PQCSignatureEngine(strict_mode=False)

        # Valid signature
        data = b"original data"
        sig = engine.compute_pqc_signature(data)

        # Tampered data with strict=True should raise
        tampered = b"tampered data"
        with pytest.raises(ModelSecurityError):
            engine.verify_pqc_signature(tampered, sig, strict=True)

    def test_strict_mode_returns_tuple_when_false(self):
        """Test strict=False returns (is_valid, reason) tuple."""
        from app.ml.model_security import PQCSignatureEngine

        engine = PQCSignatureEngine(strict_mode=False)

        data = b"original data"
        sig = engine.compute_pqc_signature(data)

        # Tampered data with strict=False returns tuple
        tampered = b"tampered data"
        result = engine.verify_pqc_signature(tampered, sig, strict=False)

        assert isinstance(result, tuple)
        assert len(result) == 2
        is_valid, reason = result
        assert is_valid is False
        assert "mismatch" in reason.lower()

    def test_verify_model_signature_strict_mode(self, security_manager, sample_model, temp_dir):
        """Test verify_model_signature strict mode in ModelSecurityManager."""
        from app.ml.model_security import ModelSecurityError

        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(model_path, model_name="test_model", model_version="v1.0.0")

        # Tamper with model
        with open(model_path, "ab") as f:
            f.write(b"TAMPERED")

        # strict=True should raise
        with pytest.raises(ModelSecurityError):
            security_manager.verify_model_signature(model_path, strict=True)

        # strict=False should return tuple
        is_valid, reason = security_manager.verify_model_signature(model_path, strict=False)
        assert is_valid is False


class TestThreatCorrelationEngine:
    """Test PAC-SAM-NEXT-019 Threat Correlation Engine."""

    def test_threat_signal_creation(self):
        """Test ThreatSignal dataclass."""
        from datetime import datetime


        signal = ThreatSignal(
            source="test_detector",
            signal_type="content_anomaly",
            severity="HIGH",
            confidence=0.85,
            timestamp=datetime.utcnow(),
            details={"test": "value"},
        )

        assert signal.source == "test_detector"
        assert signal.severity == "HIGH"
        assert signal.confidence == 0.85

        # Test serialization
        d = signal.to_dict()
        assert d["source"] == "test_detector"
        assert "timestamp" in d

    def test_threat_correlation_engine_initialization(self):
        """Test ThreatCorrelationEngine initialization."""

        engine = ThreatCorrelationEngine()
        assert engine.signals == []

        # Test global getter
        global_engine = get_threat_correlation_engine()
        assert global_engine is not None

    def test_add_content_anomaly(self):
        """Test adding content anomaly signals."""

        engine = ThreatCorrelationEngine()

        signal = engine.add_content_anomaly(details={"suspicious_imports": ["os", "subprocess"]}, severity="CRITICAL", confidence=0.95)

        assert signal.signal_type == "content_anomaly"
        assert signal.severity == "CRITICAL"
        assert len(engine.signals) == 1

    def test_add_timeline_anomaly(self):
        """Test adding timeline anomaly signals."""

        engine = ThreatCorrelationEngine()

        signal = engine.add_timeline_anomaly(details={"backdated": True, "mtime": "2020-01-01"}, severity="MEDIUM")

        assert signal.signal_type == "timeline_anomaly"
        assert len(engine.signals) == 1

    def test_add_size_drift_anomaly(self):
        """Test adding size drift anomaly signals."""

        engine = ThreatCorrelationEngine()

        signal = engine.add_size_drift_anomaly(
            details={"previous_size_mb": 1.5, "current_size_mb": 5.0, "delta_percent": 233}, severity="HIGH"
        )

        assert signal.signal_type == "size_drift_anomaly"
        assert len(engine.signals) == 1

    def test_add_metadata_mismatch_anomaly(self):
        """Test adding metadata mismatch anomaly signals."""

        engine = ThreatCorrelationEngine()

        signal = engine.add_metadata_mismatch_anomaly(details={"hash_mismatch": True}, severity="HIGH")

        assert signal.signal_type == "metadata_mismatch_anomaly"
        assert len(engine.signals) == 1

    def test_compute_stacking_score_empty(self):
        """Test stacking score with no signals is 0."""

        engine = ThreatCorrelationEngine()
        score = engine.compute_stacking_score()

        assert score == 0.0

    def test_compute_stacking_score_with_signals(self):
        """Test stacking score computation with signals."""

        engine = ThreatCorrelationEngine()

        # Add some signals
        engine.add_content_anomaly(details={"test": "content"}, severity="HIGH", confidence=0.8)
        engine.add_size_drift_anomaly(details={"test": "drift"}, severity="MEDIUM", confidence=0.7)

        score = engine.compute_stacking_score()

        # Score should be > 0 with signals
        assert score > 0.0
        assert score <= 100.0

    def test_correlate_returns_result(self):
        """Test correlate() returns ThreatCorrelationResult."""

        engine = ThreatCorrelationEngine()

        engine.add_content_anomaly(details={"suspicious_imports": ["os"]}, severity="CRITICAL")

        result = engine.correlate()

        assert isinstance(result, ThreatCorrelationResult)
        assert result.stacking_score > 0
        assert result.threat_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "SAFE"]
        assert len(result.recommendations) > 0

    def test_ingest_maggie_drift_signals(self):
        """Test ingestion of Maggie's drift detection signals."""

        engine = ThreatCorrelationEngine()

        maggie_report = {
            "model_path": "/models/risk_v1.pkl",
            "drift_detected": True,
            "drift_magnitude": 0.45,
            "drift_type": "feature_distribution",
        }

        engine.ingest_maggie_drift_signals(maggie_report)

        assert len(engine.signals) == 1
        assert engine.signals[0].source == "maggie_drift_detector"
        assert engine.signals[0].signal_type == "size_drift_anomaly"

    def test_ingest_cody_anomaly_signals(self):
        """Test ingestion of Cody's code/model anomaly signals."""

        engine = ThreatCorrelationEngine()

        cody_report = {
            "anomalies": [
                {"type": "suspicious_import", "module": "os", "severity": "HIGH"},
                {"type": "entropy_spike", "value": 7.9, "severity": "MEDIUM"},
            ]
        }

        engine.ingest_cody_anomaly_signals(cody_report)

        assert len(engine.signals) == 2
        sources = {s.source for s in engine.signals}
        assert "cody_analyzer" in sources

    def test_correlation_multiplier_multi_source(self):
        """Test correlation multiplier for multi-source attacks."""

        engine = ThreatCorrelationEngine()

        # Same signal type from different sources
        engine.add_content_anomaly(details={"test": "1"}, severity="HIGH", source="detector_a")
        engine.add_content_anomaly(details={"test": "2"}, severity="HIGH", source="detector_b")

        score = engine.compute_stacking_score()
        patterns = engine.correlation_cache.get("patterns", [])

        # Multi-source pattern should be detected
        assert any("multi_source_attack" in p for p in patterns)

    def test_threat_level_thresholds(self):
        """Test threat level determination based on score."""

        engine = ThreatCorrelationEngine()

        # Add enough critical signals to trigger CRITICAL level
        for _ in range(3):
            engine.add_content_anomaly(details={"attack": True}, severity="CRITICAL", confidence=0.95)

        result = engine.correlate()

        # Should be at least HIGH or CRITICAL with 3 critical signals
        assert result.threat_level in ["CRITICAL", "HIGH"]


class TestThreatCorrelationIntegration:
    """Test Threat Correlation integration with ModelSecurityManager."""

    def test_run_threat_correlation(self, security_manager, sample_model, temp_dir):
        """Test run_threat_correlation method."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        # Sign model
        security_manager.sign_model(model_path, model_name="test_model", model_version="v1.0.0")

        # Run threat correlation
        result = security_manager.run_threat_correlation(model_path)

        assert result is not None
        assert hasattr(result, "stacking_score")
        assert hasattr(result, "threat_level")
        assert hasattr(result, "recommendations")

    def test_run_threat_correlation_with_maggie_signals(self, security_manager, sample_model, temp_dir):
        """Test threat correlation with external Maggie signals."""
        model_path = temp_dir / "test_model.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(sample_model, f)

        security_manager.sign_model(model_path, model_name="test_model", model_version="v1.0.0")

        maggie_report = {"drift_detected": True, "drift_magnitude": 0.35, "drift_type": "feature_shift"}

        result = security_manager.run_threat_correlation(model_path, maggie_drift_report=maggie_report)

        # Should have signals from Maggie
        maggie_signals = [s for s in result.correlated_signals if s.source == "maggie_drift_detector"]
        assert len(maggie_signals) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
