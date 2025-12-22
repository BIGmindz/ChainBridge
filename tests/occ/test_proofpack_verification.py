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


# =============================================================================
# GAP-V TESTS: VERIFICATION FAILURE PATH COVERAGE (VERIFICATION_INVARIANTS.md)
# =============================================================================


class TestVerificationFailurePaths:
    """
    Tests for explicit verification failure paths.

    Per VERIFICATION_INVARIANTS.md:
    - GAP-V-01: Lineage timestamp non-monotonicity → INVALID_LINEAGE
    - GAP-V-02: Reference mismatch (input_refs) → INVALID_REFERENCES
    - GAP-V-03: Decision artifact tamper → INVALID_ARTIFACT_HASH
    - GAP-V-04: Outcome artifact tamper → INVALID_ARTIFACT_HASH
    """

    def test_lineage_non_monotonic_timestamp_fails(self, test_artifact_resolver):
        """
        GAP-V-01: Non-monotonic lineage timestamps fail at V-STEP-04.

        Per V-INV-008: Lineage chain requires ascending recorded_at.
        Verification must return INVALID_LINEAGE when timestamps go backward.
        """
        store = get_pdo_store()
        reset_pdo_store()

        # Create first PDO (older timestamp)
        pdo1_create = PDOCreate(
            source_system=PDOSourceSystem.OCC,
            outcome="approved",
            actor="test-agent",
            input_refs=["input:lin_001"],
            decision_ref="decision:lin_001",
            outcome_ref="outcome:lin_001",
        )
        pdo1 = store.create(pdo1_create)

        # Create second PDO linked to first (newer timestamp normally)
        pdo2_create = PDOCreate(
            source_system=PDOSourceSystem.OCC,
            outcome="approved",
            actor="test-agent",
            previous_pdo_id=pdo1.pdo_id,
            input_refs=["input:lin_002"],
            decision_ref="decision:lin_002",
            outcome_ref="outcome:lin_002",
        )
        pdo2 = store.create(pdo2_create)

        # Generate valid ProofPack
        generator = ProofPackGenerator(artifact_resolver=test_artifact_resolver)
        proofpack = generator.generate(pdo2.pdo_id)

        # Tamper: Make lineage PDO's timestamp NEWER than successor
        # Find lineage entry for pdo1
        lineage_files = [k for k in proofpack["files"] if k.startswith("lineage/")]
        if lineage_files:
            lineage_path = lineage_files[0]
            lineage_data = json.loads(proofpack["files"][lineage_path])

            # Set timestamp to far future (non-monotonic: older PDO has newer timestamp)
            lineage_data["recorded_at"] = "2099-12-31T23:59:59.999999Z"

            # Must recompute hash after tampering record
            canonical_data = {
                "pdo_id": str(lineage_data.get("pdo_id")),
                "version": lineage_data.get("version", "1.0"),
                "input_refs": sorted(lineage_data.get("input_refs", [])),
                "decision_ref": lineage_data.get("decision_ref"),
                "outcome_ref": lineage_data.get("outcome_ref"),
                "outcome": lineage_data.get("outcome"),
                "source_system": lineage_data.get("source_system"),
                "actor": lineage_data.get("actor"),
                "actor_type": lineage_data.get("actor_type", "system"),
                "recorded_at": lineage_data.get("recorded_at"),
                "previous_pdo_id": str(lineage_data.get("previous_pdo_id")) if lineage_data.get("previous_pdo_id") else None,
                "correlation_id": lineage_data.get("correlation_id"),
            }
            from core.occ.proofpack.generator import compute_json_hash, compute_sha256
            lineage_data["hash"] = compute_json_hash(canonical_data)
            proofpack["files"][lineage_path] = canonical_json(lineage_data)

            # Also update manifest hash for lineage file
            manifest = json.loads(proofpack["files"]["manifest.json"])
            for entry in manifest.get("contents", {}).get("lineage", []):
                if entry.get("path") == lineage_path:
                    entry["hash"] = compute_sha256(proofpack["files"][lineage_path].encode("utf-8"))

            # Recompute manifest hash
            manifest_data = {
                "proofpack_version": manifest.get("proofpack_version"),
                "pdo_id": manifest.get("pdo_id"),
                "exported_at": manifest.get("exported_at"),
                "exporter": manifest.get("exporter"),
                "contents": manifest.get("contents"),
            }
            manifest["integrity"]["manifest_hash"] = compute_json_hash(manifest_data)
            proofpack["files"]["manifest.json"] = canonical_json(manifest)

        verifier = ProofPackVerifier()
        result = verifier.verify(proofpack)

        # V-HALT-001: Must halt at V-STEP-04 with INVALID_LINEAGE
        assert result.outcome == VerificationOutcome.INVALID_LINEAGE
        assert result.is_valid is False
        assert "timestamp" in result.error_message.lower() or "lineage" in result.error_message.lower()

    def test_reference_mismatch_input_refs_fails(self, valid_proofpack):
        """
        GAP-V-02: Input refs mismatch fails at V-STEP-05.

        Per V-INV-009: Manifest input_refs must equal PDO input_refs (set equality).
        Verification must return INVALID_REFERENCES when sets differ.
        """
        tampered = copy.deepcopy(valid_proofpack)

        # Tamper: Add extra input ref to manifest that PDO doesn't have
        from core.occ.proofpack.generator import compute_json_hash, compute_sha256
        manifest = json.loads(tampered["files"]["manifest.json"])

        # Create bogus artifact with proper content and hash
        bogus_content = canonical_json({"ref": "input:BOGUS_EXTRA_REF", "data": "bogus"})
        bogus_hash = compute_sha256(bogus_content.encode("utf-8"))

        manifest["contents"]["inputs"].append({
            "ref": "input:BOGUS_EXTRA_REF",
            "path": "inputs/bogus.json",
            "hash": bogus_hash,
        })

        # Recompute manifest hash
        manifest_data = {
            "proofpack_version": manifest.get("proofpack_version"),
            "pdo_id": manifest.get("pdo_id"),
            "exported_at": manifest.get("exported_at"),
            "exporter": manifest.get("exporter"),
            "contents": manifest.get("contents"),
        }
        manifest["integrity"]["manifest_hash"] = compute_json_hash(manifest_data)
        tampered["files"]["manifest.json"] = canonical_json(manifest)

        # Add dummy file with matching hash so it passes artifact hash check
        tampered["files"]["inputs/bogus.json"] = bogus_content

        verifier = ProofPackVerifier()
        result = verifier.verify(tampered)

        # V-HALT-001: Must halt at V-STEP-05 with INVALID_REFERENCES
        assert result.outcome == VerificationOutcome.INVALID_REFERENCES
        assert result.is_valid is False
        assert "input" in result.error_message.lower() or "mismatch" in result.error_message.lower()

    def test_decision_artifact_tamper_fails(self, valid_proofpack):
        """
        GAP-V-03: Decision artifact tampering fails at V-STEP-02.

        Per V-INV-005: Artifact hash verification uses SHA-256 of file bytes.
        Decision artifact modification must return INVALID_ARTIFACT_HASH.
        """
        tampered = copy.deepcopy(valid_proofpack)

        # Find decision file
        decision_path = None
        manifest = json.loads(tampered["files"]["manifest.json"])
        decision_entry = manifest.get("contents", {}).get("decision", {})
        decision_path = decision_entry.get("path")

        if decision_path and decision_path in tampered["files"]:
            # Tamper: Modify decision artifact content
            decision_data = json.loads(tampered["files"][decision_path])
            decision_data["TAMPERED_DECISION"] = "MALICIOUS_CHANGE"
            tampered["files"][decision_path] = canonical_json(decision_data)

            # DO NOT update manifest hash - this simulates tampering

            verifier = ProofPackVerifier()
            result = verifier.verify(tampered)

            # V-HALT-001: Must halt at V-STEP-02 with INVALID_ARTIFACT_HASH
            assert result.outcome == VerificationOutcome.INVALID_ARTIFACT_HASH
            assert result.is_valid is False
            assert "hash" in result.error_message.lower() or "decision" in result.error_message.lower()

    def test_outcome_artifact_tamper_fails(self, valid_proofpack):
        """
        GAP-V-04: Outcome artifact tampering fails at V-STEP-02.

        Per V-INV-005: Artifact hash verification uses SHA-256 of file bytes.
        Outcome artifact modification must return INVALID_ARTIFACT_HASH.
        """
        tampered = copy.deepcopy(valid_proofpack)

        # Find outcome file
        outcome_path = None
        manifest = json.loads(tampered["files"]["manifest.json"])
        outcome_entry = manifest.get("contents", {}).get("outcome", {})
        outcome_path = outcome_entry.get("path")

        if outcome_path and outcome_path in tampered["files"]:
            # Tamper: Modify outcome artifact content
            outcome_data = json.loads(tampered["files"][outcome_path])
            outcome_data["TAMPERED_OUTCOME"] = "MALICIOUS_CHANGE"
            tampered["files"][outcome_path] = canonical_json(outcome_data)

            # DO NOT update manifest hash - this simulates tampering

            verifier = ProofPackVerifier()
            result = verifier.verify(tampered)

            # V-HALT-001: Must halt at V-STEP-02 with INVALID_ARTIFACT_HASH
            assert result.outcome == VerificationOutcome.INVALID_ARTIFACT_HASH
            assert result.is_valid is False
            assert "hash" in result.error_message.lower() or "outcome" in result.error_message.lower()


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
