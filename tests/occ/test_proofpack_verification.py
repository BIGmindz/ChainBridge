"""
ProofPack Verification Tests — PROOFPACK_SPEC_v1.md Section 6

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

Tests for:
- Offline verification
- Tamper detection
- Hash verification

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from typing import Any, Dict
from uuid import uuid4

import pytest

from core.occ.proofpack import (
    ArtifactResolver,
    ProofPackGenerator,
    ProofPackVerifier,
    VerificationOutcome,
    canonical_json,
    generate_proofpack,
    get_proofpack_verifier,
    reset_proofpack_generator,
    verify_proofpack,
)
from core.occ.schemas.pdo import PDOCreate, PDOOutcome, PDOSourceSystem
from core.occ.store.pdo_store import get_pdo_store, reset_pdo_store

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_singletons(monkeypatch):
    """Reset singleton stores before each test."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        temp_path = f.name
    monkeypatch.setenv("CHAINBRIDGE_PDO_STORE_PATH", temp_path)
    reset_pdo_store()
    reset_proofpack_generator()
    yield
    reset_pdo_store()
    reset_proofpack_generator()
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def test_artifact_resolver():
    """Create an artifact resolver with deterministic test data."""

    class TestArtifactResolver(ArtifactResolver):
        """Resolver that returns deterministic test data."""

        def resolve_input(self, ref: str) -> Dict[str, Any]:
            return {
                "ref": ref,
                "type": "input",
                "data": {"test": "input_value", "ref": ref},
                "timestamp": "2025-01-01T00:00:00Z",
            }

        def resolve_decision(self, ref: str) -> Dict[str, Any]:
            return {
                "ref": ref,
                "type": "decision",
                "data": {"verdict": "approved", "ref": ref},
                "timestamp": "2025-01-01T00:00:01Z",
            }

        def resolve_outcome(self, ref: str) -> Dict[str, Any]:
            return {
                "ref": ref,
                "type": "outcome",
                "data": {"status": "complete", "ref": ref},
                "timestamp": "2025-01-01T00:00:02Z",
            }

    return TestArtifactResolver()


@pytest.fixture
def sample_pdo():
    """Create a sample PDO for testing."""
    store = get_pdo_store()
    create = PDOCreate(
        source_system=PDOSourceSystem.OCC,
        outcome=PDOOutcome.APPROVED,
        actor="test-verifier-agent",
        input_refs=["input:ver_abc", "input:ver_def"],
        decision_ref="decision:ver_xyz",
        outcome_ref="outcome:ver_qrs",
    )
    return store.create(create)


@pytest.fixture
def valid_proofpack(sample_pdo, test_artifact_resolver):
    """Generate a valid ProofPack for testing."""
    generator = ProofPackGenerator(artifact_resolver=test_artifact_resolver)
    return generator.generate(sample_pdo.pdo_id)


# =============================================================================
# VERIFICATION SUCCESS TESTS
# =============================================================================


class TestVerificationSuccess:
    """Tests for successful verification of valid ProofPacks."""

    def test_verify_valid_proofpack(self, valid_proofpack):
        """Valid ProofPack passes verification."""
        verifier = ProofPackVerifier()
        result = verifier.verify(valid_proofpack)

        assert result.outcome == VerificationOutcome.VALID
        assert result.is_valid is True

    def test_verify_all_steps_pass(self, valid_proofpack):
        """All verification steps pass for valid ProofPack."""
        verifier = ProofPackVerifier()
        result = verifier.verify(valid_proofpack)

        for step in result.steps:
            assert step.passed is True, f"Step {step.step} failed: {step.message}"

    def test_verify_returns_correct_pdo_id(self, valid_proofpack, sample_pdo):
        """Verification returns correct PDO ID."""
        verifier = ProofPackVerifier()
        result = verifier.verify(valid_proofpack)

        assert result.pdo_id == str(sample_pdo.pdo_id)

    def test_module_level_verify_function(self, valid_proofpack):
        """Module-level verify_proofpack function works."""
        result = verify_proofpack(valid_proofpack)
        assert result.is_valid is True

    def test_get_verifier_instance(self):
        """get_proofpack_verifier returns instance."""
        v1 = get_proofpack_verifier()
        assert v1 is not None


# =============================================================================
# TAMPER DETECTION TESTS
# =============================================================================


class TestTamperDetection:
    """Tests for tamper detection."""

    def test_pdo_tamper_fails(self, valid_proofpack):
        """Tampered PDO record fails verification."""
        tampered = copy.deepcopy(valid_proofpack)

        pdo_data = json.loads(tampered["files"]["pdo/record.json"])
        pdo_data["actor"] = "TAMPERED_ACTOR"
        tampered["files"]["pdo/record.json"] = canonical_json(pdo_data)

        verifier = ProofPackVerifier()
        result = verifier.verify(tampered)

        assert result.is_valid is False

    def test_input_artifact_tamper_fails(self, valid_proofpack):
        """Tampered input artifact fails verification."""
        tampered = copy.deepcopy(valid_proofpack)

        input_files = [k for k in tampered["files"] if k.startswith("inputs/")]
        if input_files:
            artifact_data = json.loads(tampered["files"][input_files[0]])
            artifact_data["TAMPERED"] = True
            tampered["files"][input_files[0]] = canonical_json(artifact_data)

            verifier = ProofPackVerifier()
            result = verifier.verify(tampered)

            assert result.is_valid is False

    def test_manifest_tamper_fails(self, valid_proofpack):
        """Tampered manifest fails verification."""
        tampered = copy.deepcopy(valid_proofpack)

        manifest_data = json.loads(tampered["files"]["manifest.json"])
        manifest_data["exporter"]["agent"] = "EVIL_AGENT"
        tampered["files"]["manifest.json"] = canonical_json(manifest_data)

        verifier = ProofPackVerifier()
        result = verifier.verify(tampered)

        assert result.is_valid is False


# =============================================================================
# MISSING FILE TESTS
# =============================================================================


class TestMissingFiles:
    """Tests for missing file detection."""

    def test_missing_pdo_fails(self, valid_proofpack):
        """Missing PDO record fails verification."""
        tampered = copy.deepcopy(valid_proofpack)
        del tampered["files"]["pdo/record.json"]

        verifier = ProofPackVerifier()
        result = verifier.verify(tampered)

        assert result.is_valid is False

    def test_missing_manifest_fails(self, valid_proofpack):
        """Missing manifest fails verification."""
        tampered = copy.deepcopy(valid_proofpack)
        del tampered["files"]["manifest.json"]

        verifier = ProofPackVerifier()
        result = verifier.verify(tampered)

        assert result.is_valid is False


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_proofpack_fails(self):
        """Empty ProofPack fails verification."""
        verifier = ProofPackVerifier()
        result = verifier.verify({})

        assert result.is_valid is False

    def test_no_files_fails(self):
        """ProofPack with no files fails."""
        verifier = ProofPackVerifier()
        result = verifier.verify({"files": {}})

        assert result.is_valid is False

    def test_malformed_json_fails(self, valid_proofpack):
        """Malformed JSON fails verification."""
        tampered = copy.deepcopy(valid_proofpack)
        tampered["files"]["pdo/record.json"] = "not valid json {"

        verifier = ProofPackVerifier()
        result = verifier.verify(tampered)

        assert result.is_valid is False

    def test_extra_files_allowed(self, valid_proofpack):
        """Extra files don't break verification."""
        modified = copy.deepcopy(valid_proofpack)
        modified["files"]["extra/bonus.txt"] = "Extra content"

        verifier = ProofPackVerifier()
        result = verifier.verify(modified)

        assert result.outcome == VerificationOutcome.VALID


# =============================================================================
# ROUND-TRIP TESTS
# =============================================================================


class TestRoundTrip:
    """Tests for generate → verify round trip."""

    def test_generated_proofpack_verifies(self, sample_pdo, test_artifact_resolver):
        """Generated ProofPack always verifies."""
        generator = ProofPackGenerator(artifact_resolver=test_artifact_resolver)

        proofpack = generator.generate(sample_pdo.pdo_id)
        result = verify_proofpack(proofpack)
        assert result.outcome == VerificationOutcome.VALID

    def test_serialize_deserialize_verifies(self, valid_proofpack):
        """Serialized/deserialized ProofPack verifies."""
        serialized = json.dumps(valid_proofpack)
        deserialized = json.loads(serialized)

        result = verify_proofpack(deserialized)
        assert result.outcome == VerificationOutcome.VALID

    def test_offline_verification(self, valid_proofpack):
        """Verification works offline."""
        reset_pdo_store()
        reset_proofpack_generator()

        verifier = ProofPackVerifier()
        result = verifier.verify(valid_proofpack)

        assert result.outcome == VerificationOutcome.VALID
