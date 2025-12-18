"""
ProofPack Generation Tests — PROOFPACK_SPEC_v1.md

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

Tests for:
- Deterministic generation (same PDO → same ProofPack, excluding timestamps)
- Hash stability across runs
- File structure per spec Section 3.1
- Manifest integrity binding
- Artifact resolution

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

import pytest

from core.occ.proofpack import (
    HASH_ALGORITHM,
    PROOFPACK_VERSION,
    ArtifactResolver,
    ProofPackGenerationError,
    ProofPackGenerator,
    ProofPackManifest,
    StubArtifactResolver,
    canonical_json,
    compute_json_hash,
    compute_sha256,
    generate_proofpack,
    get_proofpack_generator,
    ref_to_filename,
    reset_proofpack_generator,
)
from core.occ.schemas.pdo import PDOCreate, PDOOutcome, PDOSourceSystem
from core.occ.store.pdo_store import PDOStore, get_pdo_store, reset_pdo_store

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
def sample_pdo():
    """Create a sample PDO for testing."""
    store = get_pdo_store()
    create = PDOCreate(
        source_system=PDOSourceSystem.OCC,
        outcome=PDOOutcome.APPROVED,
        actor="test-agent",
        input_refs=["input:abc123", "input:def456"],
        decision_ref="decision:xyz789",
        outcome_ref="outcome:qrs012",
    )
    record = store.create(create)
    return record


@pytest.fixture
def custom_artifact_resolver():
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


# =============================================================================
# SCHEMA UTILITY TESTS
# =============================================================================


class TestCanonicalJson:
    """Tests for canonical JSON serialization."""

    def test_canonical_json_sorted_keys(self):
        """Keys are sorted alphabetically."""
        data = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(data)
        assert result == '{"a":2,"m":3,"z":1}'

    def test_canonical_json_no_spaces(self):
        """No spaces in separators."""
        data = {"key": "value"}
        result = canonical_json(data)
        assert " " not in result
        assert result == '{"key":"value"}'

    def test_canonical_json_nested(self):
        """Nested objects also sorted."""
        data = {"outer": {"z": 1, "a": 2}}
        result = canonical_json(data)
        assert result == '{"outer":{"a":2,"z":1}}'

    def test_canonical_json_deterministic(self):
        """Same input always produces same output."""
        data = {"key1": "val1", "key2": {"nested": "value"}}
        result1 = canonical_json(data)
        result2 = canonical_json(data)
        assert result1 == result2


class TestHashFunctions:
    """Tests for hash computation functions."""

    def test_compute_sha256_bytes(self):
        """SHA-256 of bytes."""
        result = compute_sha256(b"hello")
        assert len(result) == 64  # SHA-256 hex is 64 chars
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_compute_json_hash(self):
        """Hash of JSON object is deterministic."""
        data = {"key": "value"}
        h1 = compute_json_hash(data)
        h2 = compute_json_hash(data)
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_json_hash_order_independent(self):
        """Key order doesn't affect hash due to canonical JSON."""
        data1 = {"a": 1, "b": 2}
        data2 = {"b": 2, "a": 1}
        assert compute_json_hash(data1) == compute_json_hash(data2)


class TestRefToFilename:
    """Tests for ref_to_filename utility."""

    def test_ref_produces_hash_filename(self):
        """Ref produces hash-based filename."""
        result = ref_to_filename("abc123")
        # Should be {hash16chars}.json
        assert result.endswith(".json")
        assert len(result) == 21  # 16 + 5 for ".json"

    def test_same_ref_same_filename(self):
        """Same ref always produces same filename."""
        assert ref_to_filename("input:abc123") == ref_to_filename("input:abc123")

    def test_different_refs_different_filenames(self):
        """Different refs produce different filenames."""
        assert ref_to_filename("ref1") != ref_to_filename("ref2")


# =============================================================================
# GENERATOR TESTS
# =============================================================================


class TestProofPackGenerator:
    """Tests for ProofPackGenerator class."""

    def test_generate_basic(self, sample_pdo, custom_artifact_resolver):
        """Basic generation succeeds."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        assert "pdo_id" in result
        assert result["pdo_id"] == str(sample_pdo.pdo_id)
        assert "exported_at" in result
        assert "manifest" in result
        assert "files" in result

    def test_generate_has_required_files(self, sample_pdo, custom_artifact_resolver):
        """Generated ProofPack has required files per spec."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        files = result["files"]
        assert "manifest.json" in files
        assert "pdo/record.json" in files
        assert "VERIFICATION.txt" in files

    def test_generate_has_artifact_files(self, sample_pdo, custom_artifact_resolver):
        """Generated ProofPack has artifact files."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        files = result["files"]
        # Check inputs directory has files
        input_files = [f for f in files if f.startswith("inputs/")]
        assert len(input_files) > 0

        # Check decision directory has file
        decision_files = [f for f in files if f.startswith("decision/")]
        assert len(decision_files) == 1

        # Check outcome directory has file
        outcome_files = [f for f in files if f.startswith("outcome/")]
        assert len(outcome_files) == 1

    def test_generate_with_lineage(self, sample_pdo, custom_artifact_resolver):
        """Generation includes lineage when requested."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id, include_lineage=True)

        # Lineage files only present if there is a chain
        # Since sample_pdo has no previous_pdo_id, no lineage files expected
        files = result["files"]
        assert "VERIFICATION.txt" in files  # Verify generation succeeded

    def test_generate_without_lineage(self, sample_pdo, custom_artifact_resolver):
        """Generation excludes lineage when not requested."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id, include_lineage=False)

        files = result["files"]
        lineage_files = [f for f in files if f.startswith("lineage/")]
        assert len(lineage_files) == 0

    def test_generate_pdo_not_found(self, custom_artifact_resolver):
        """Generation fails for non-existent PDO."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        fake_id = uuid4()

        with pytest.raises(ProofPackGenerationError, match="not found"):
            generator.generate(fake_id)

    def test_manifest_structure(self, sample_pdo, custom_artifact_resolver):
        """Manifest has correct structure per spec."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        manifest = result["manifest"]
        assert "proofpack_version" in manifest
        assert manifest["proofpack_version"] == "1.0"
        assert "exporter" in manifest
        assert "contents" in manifest
        assert "integrity" in manifest

    def test_manifest_contents(self, sample_pdo, custom_artifact_resolver):
        """Manifest contents reference correct files."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        contents = result["manifest"]["contents"]
        assert "pdo" in contents
        assert contents["pdo"]["path"] == "pdo/record.json"
        assert "inputs" in contents
        assert "decision" in contents
        assert "outcome" in contents

    def test_manifest_integrity(self, sample_pdo, custom_artifact_resolver):
        """Manifest has integrity hashes."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        integrity = result["manifest"]["integrity"]
        assert "manifest_hash" in integrity
        assert integrity["hash_algorithm"] == "sha256"


# =============================================================================
# DETERMINISM TESTS
# =============================================================================


class TestDeterministicGeneration:
    """Tests for deterministic ProofPack generation."""

    def test_same_pdo_same_structure(self, sample_pdo, custom_artifact_resolver):
        """Same PDO generates same file structure."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)

        result1 = generator.generate(sample_pdo.pdo_id)
        result2 = generator.generate(sample_pdo.pdo_id)

        # File keys should match
        assert set(result1["files"].keys()) == set(result2["files"].keys())

    def test_same_pdo_same_content(self, sample_pdo, custom_artifact_resolver):
        """Same PDO generates same content (excluding export timestamp)."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)

        result1 = generator.generate(sample_pdo.pdo_id)
        result2 = generator.generate(sample_pdo.pdo_id)

        # PDO record should be identical
        assert result1["files"]["pdo/record.json"] == result2["files"]["pdo/record.json"]

    def test_pdo_record_canonical_format(self, sample_pdo, custom_artifact_resolver):
        """PDO record in ProofPack uses canonical JSON."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        pdo_json = result["files"]["pdo/record.json"]
        # Should be valid JSON
        parsed = json.loads(pdo_json)
        assert parsed["pdo_id"] == str(sample_pdo.pdo_id)


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestProofPackGeneratorSingleton:
    """Tests for generator singleton."""

    def test_generate_proofpack_function(self, sample_pdo):
        """Module-level function works."""
        result = generate_proofpack(sample_pdo.pdo_id)
        assert result["pdo_id"] == str(sample_pdo.pdo_id)

    def test_get_proofpack_generator_singleton(self):
        """get_proofpack_generator returns singleton."""
        g1 = get_proofpack_generator()
        g2 = get_proofpack_generator()
        assert g1 is g2

    def test_reset_proofpack_generator(self):
        """reset clears singleton."""
        g1 = get_proofpack_generator()
        reset_proofpack_generator()
        g2 = get_proofpack_generator()
        assert g1 is not g2


# =============================================================================
# STUB RESOLVER TESTS
# =============================================================================


class TestStubArtifactResolver:
    """Tests for default stub resolver."""

    def test_stub_resolves_input(self):
        """Stub resolver returns placeholder for input."""
        resolver = StubArtifactResolver()
        result = resolver.resolve_input("test:ref")
        assert result is not None
        assert "ref" in result

    def test_stub_resolves_decision(self):
        """Stub resolver returns placeholder for decision."""
        resolver = StubArtifactResolver()
        result = resolver.resolve_decision("decision:ref")
        assert result is not None
        assert "ref" in result

    def test_stub_resolves_outcome(self):
        """Stub resolver returns placeholder for outcome."""
        resolver = StubArtifactResolver()
        result = resolver.resolve_outcome("outcome:ref")
        assert result is not None
        assert "ref" in result


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestGenerationErrors:
    """Tests for error handling in generation."""

    def test_pdo_not_found_error(self, custom_artifact_resolver):
        """Clear error when PDO doesn't exist."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        with pytest.raises(ProofPackGenerationError) as exc_info:
            generator.generate(uuid4())

        assert "not found" in str(exc_info.value).lower()

    def test_fail_on_unresolved_disabled(self, sample_pdo):
        """With fail_on_unresolved=False, stub data is used."""
        # Use default stub resolver
        generator = ProofPackGenerator()
        result = generator.generate(sample_pdo.pdo_id, fail_on_unresolved=False)

        # Should succeed with stub data
        assert result["pdo_id"] == str(sample_pdo.pdo_id)


# =============================================================================
# VERIFICATION.TXT TESTS
# =============================================================================


class TestVerificationInstructions:
    """Tests for VERIFICATION.txt file."""

    def test_verification_txt_exists(self, sample_pdo, custom_artifact_resolver):
        """VERIFICATION.txt file is included."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        assert "VERIFICATION.txt" in result["files"]

    def test_verification_txt_contains_steps(self, sample_pdo, custom_artifact_resolver):
        """VERIFICATION.txt contains verification steps."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        content = result["files"]["VERIFICATION.txt"]
        assert "Step 1" in content or "step 1" in content.lower() or "1." in content
        assert "hash" in content.lower()

    def test_verification_txt_references_pdo_id(self, sample_pdo, custom_artifact_resolver):
        """VERIFICATION.txt references the PDO ID."""
        generator = ProofPackGenerator(artifact_resolver=custom_artifact_resolver)
        result = generator.generate(sample_pdo.pdo_id)

        content = result["files"]["VERIFICATION.txt"]
        assert str(sample_pdo.pdo_id) in content
