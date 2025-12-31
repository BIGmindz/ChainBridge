"""
Space and Time Provider Tests

Test suite for SpaceAndTimeProofProvider.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.

Agent: GID-01 (Cody) — Senior Backend Engineer

Tests:
- Proof determinism (INV-PROOF-001)
- Hash stability
- Failure modes
- Verification flow
"""

import hashlib
import json
import pytest
from datetime import datetime, timedelta

from core.gie.proof.provider import (
    ProofInput,
    ProofOutput,
    ProofClass,
    ProofStatus,
    VerificationStatus,
    ProofProviderRegistry,
    LocalHashProvider,
    get_proof_registry,
    reset_proof_registry,
)
from core.gie.proof.providers.space_and_time import (
    SpaceAndTimeProofProvider,
    SpaceAndTimeConfig,
    get_space_and_time_provider,
    reset_space_and_time_provider,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sxt_config():
    """Test configuration for Space and Time."""
    return SpaceAndTimeConfig(
        api_endpoint="https://test.spaceandtime.io",
        api_key="test-api-key",
        namespace="test_governance",
        proof_format="snark",
        timeout_seconds=10,
        proof_expiry_hours=1,
    )


@pytest.fixture
def sxt_provider(sxt_config):
    """Space and Time provider in mock mode."""
    reset_space_and_time_provider()
    return SpaceAndTimeProofProvider(config=sxt_config, mock_mode=True)


@pytest.fixture
def proof_input():
    """Sample proof input."""
    return ProofInput(
        input_id="TEST-INPUT-001",
        data_hash="sha256:abc123def456",
        query_template="SELECT * FROM governance.decisions WHERE pdo_id = :pdo_id",
        parameters=(("pdo_id", "PDO-001"),),
        timestamp="2025-12-26T12:00:00Z",
        requestor_gid="GID-01",
    )


@pytest.fixture(autouse=True)
def cleanup():
    """Reset globals after each test."""
    yield
    reset_space_and_time_provider()
    reset_proof_registry()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PROOF DETERMINISM (INV-PROOF-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProofDeterminism:
    """Tests for INV-PROOF-001: Same input → same output hash."""

    def test_same_input_produces_same_hash(self, sxt_provider, proof_input):
        """Identical inputs must produce identical proof hashes."""
        output1 = sxt_provider.generate_proof(proof_input)
        output2 = sxt_provider.generate_proof(proof_input)
        
        assert output1.proof_hash == output2.proof_hash
        assert output1.input_hash == output2.input_hash

    def test_different_input_produces_different_hash(self, sxt_provider):
        """Different inputs must produce different proof hashes."""
        input1 = ProofInput(
            input_id="INPUT-A",
            data_hash="sha256:aaa",
            query_template="SELECT 1",
            parameters=(),
            timestamp="2025-12-26T12:00:00Z",
            requestor_gid="GID-01",
        )
        
        input2 = ProofInput(
            input_id="INPUT-B",
            data_hash="sha256:bbb",
            query_template="SELECT 2",
            parameters=(),
            timestamp="2025-12-26T12:00:00Z",
            requestor_gid="GID-01",
        )
        
        output1 = sxt_provider.generate_proof(input1)
        output2 = sxt_provider.generate_proof(input2)
        
        assert output1.proof_hash != output2.proof_hash

    def test_determinism_with_parameters(self, sxt_provider):
        """Parameters must affect determinism correctly."""
        base_input = ProofInput(
            input_id="PARAM-TEST",
            data_hash="sha256:xyz",
            query_template="SELECT * FROM t WHERE x = :val",
            parameters=(("val", "foo"),),
            timestamp="2025-12-26T12:00:00Z",
            requestor_gid="GID-01",
        )
        
        different_param_input = ProofInput(
            input_id="PARAM-TEST",
            data_hash="sha256:xyz",
            query_template="SELECT * FROM t WHERE x = :val",
            parameters=(("val", "bar"),),  # Different value
            timestamp="2025-12-26T12:00:00Z",
            requestor_gid="GID-01",
        )
        
        output1 = sxt_provider.generate_proof(base_input)
        output2 = sxt_provider.generate_proof(different_param_input)
        
        assert output1.proof_hash != output2.proof_hash

    def test_input_canonical_hash_is_stable(self, proof_input):
        """ProofInput.compute_canonical_hash() must be stable."""
        hash1 = proof_input.compute_canonical_hash()
        hash2 = proof_input.compute_canonical_hash()
        
        assert hash1 == hash2
        assert hash1.startswith("sha256:")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: HASH STABILITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashStability:
    """Tests for hash stability across provider instances."""

    def test_hash_stable_across_instances(self, sxt_config, proof_input):
        """Same input produces same hash across different provider instances."""
        provider1 = SpaceAndTimeProofProvider(config=sxt_config, mock_mode=True)
        provider2 = SpaceAndTimeProofProvider(config=sxt_config, mock_mode=True)
        
        output1 = provider1.generate_proof(proof_input)
        output2 = provider2.generate_proof(proof_input)
        
        assert output1.proof_hash == output2.proof_hash

    def test_proof_hash_format(self, sxt_provider, proof_input):
        """Proof hash must have correct format."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.proof_hash.startswith("sxt:")
        # Hash should be SHA-256 (64 hex chars)
        hash_part = output.proof_hash.split(":")[1]
        assert len(hash_part) == 64
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_verification_handle_format(self, sxt_provider, proof_input):
        """Verification handle must have correct format."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.verification_handle.startswith("vh:")
        assert len(output.verification_handle) > 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PROOF GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestProofGeneration:
    """Tests for proof generation functionality."""

    def test_generate_returns_success_status(self, sxt_provider, proof_input):
        """Successful generation returns SUCCESS status."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.status == ProofStatus.SUCCESS
        assert output.error_message is None

    def test_generate_sets_provider_id(self, sxt_provider, proof_input):
        """Output includes correct provider ID."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.provider_id == "SPACE_AND_TIME_P2"

    def test_generate_sets_proof_class(self, sxt_provider, proof_input):
        """Output includes correct proof class."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.proof_class == ProofClass.P2_ZK_PROOF

    def test_generate_sets_expiry(self, sxt_provider, proof_input):
        """Output includes expiry timestamp."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.expires_at is not None
        assert output.expires_at > output.created_at

    def test_generate_sets_algorithm_version(self, sxt_provider, proof_input):
        """Output includes algorithm version for quantum migration."""
        output = sxt_provider.generate_proof(proof_input)
        
        assert output.algorithm_version is not None
        assert "mock" in output.algorithm_version or "v1" in output.algorithm_version


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerification:
    """Tests for proof verification."""

    def test_verify_valid_proof(self, sxt_provider, proof_input):
        """Valid proof verifies successfully."""
        output = sxt_provider.generate_proof(proof_input)
        result = sxt_provider.verify_proof(output.proof_hash)
        
        assert result.is_valid is True
        assert result.status == VerificationStatus.VALID

    def test_verify_unknown_proof(self, sxt_provider):
        """Unknown proof hash returns NOT_FOUND."""
        result = sxt_provider.verify_proof("sxt:nonexistent123")
        
        assert result.is_valid is False
        assert result.status == VerificationStatus.NOT_FOUND

    def test_verify_includes_metadata(self, sxt_provider, proof_input):
        """Verification result includes proper metadata."""
        output = sxt_provider.generate_proof(proof_input)
        result = sxt_provider.verify_proof(output.proof_hash)
        
        assert result.proof_hash == output.proof_hash
        assert result.verifier_id == "SPACE_AND_TIME_P2"
        assert result.verified_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FAILURE MODES
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailureModes:
    """Tests for failure handling."""

    def test_provider_isolation_on_error(self, sxt_config):
        """Provider errors don't propagate (INV-PROOF-003)."""
        # Create provider that will fail
        provider = SpaceAndTimeProofProvider(
            config=sxt_config,
            mock_mode=False,  # Would fail without API key in real scenario
        )
        
        # In mock fallback mode, it should still work
        proof_input = ProofInput(
            input_id="FAIL-TEST",
            data_hash="sha256:test",
            query_template="SELECT 1",
            parameters=(),
            timestamp="2025-12-26T12:00:00Z",
            requestor_gid="GID-TEST",
        )
        
        # Should not raise, should return result (possibly with error status)
        output = provider.generate_proof(proof_input)
        assert output is not None

    def test_audit_log_captures_operations(self, sxt_provider, proof_input):
        """Audit log captures all operations (INV-PROOF-004)."""
        # Generate proof
        sxt_provider.generate_proof(proof_input)
        
        # Check audit log
        log = sxt_provider.get_audit_log()
        assert len(log) >= 1
        
        entry = log[0]
        assert entry.operation == "GENERATE"
        assert entry.provider_id == "SPACE_AND_TIME_P2"

    def test_verification_logs_to_audit(self, sxt_provider, proof_input):
        """Verification operations are logged."""
        output = sxt_provider.generate_proof(proof_input)
        sxt_provider.verify_proof(output.proof_hash)
        
        log = sxt_provider.get_audit_log()
        verify_entries = [e for e in log if e.operation == "VERIFY"]
        
        assert len(verify_entries) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: QUERY BUILDING
# ═══════════════════════════════════════════════════════════════════════════════

class TestQueryBuilding:
    """Tests for SQL query building helpers."""

    def test_build_governance_query(self, sxt_provider):
        """Query builder produces valid SQL."""
        query = sxt_provider.build_governance_query(
            table="decisions",
            conditions={"pdo_id": "PDO-001", "status": "APPROVED"},
            select_columns=["pdo_id", "timestamp"],
        )
        
        assert "SELECT" in query
        assert "pdo_id, timestamp" in query
        assert "test_governance.decisions" in query
        assert "pdo_id = 'PDO-001'" in query
        assert "status = 'APPROVED'" in query

    def test_build_query_with_no_conditions(self, sxt_provider):
        """Query builder handles empty conditions."""
        query = sxt_provider.build_governance_query(
            table="audit_log",
            conditions={},
        )
        
        assert "WHERE 1=1" in query

    def test_create_proof_input_helper(self, sxt_provider):
        """create_proof_input helper produces valid input."""
        proof_input = sxt_provider.create_proof_input(
            input_id="HELPER-TEST",
            data_hash="sha256:helper",
            query="SELECT 1",
            requestor_gid="GID-01",
            parameters={"key": "value"},
        )
        
        assert proof_input.input_id == "HELPER-TEST"
        assert proof_input.data_hash == "sha256:helper"
        assert proof_input.requestor_gid == "GID-01"
        assert ("key", "value") in proof_input.parameters


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PROOF METADATA ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

class TestProofMetadata:
    """Tests for proof metadata access (hash-first per INV-PROOF-002)."""

    def test_get_proof_metadata_returns_hashes(self, sxt_provider, proof_input):
        """Metadata access returns hash references only."""
        output = sxt_provider.generate_proof(proof_input)
        metadata = sxt_provider.get_proof_metadata(output.proof_hash)
        
        assert metadata is not None
        assert "proof_hash" in metadata
        assert "input_hash" in metadata
        assert metadata["proof_hash"] == output.proof_hash

    def test_get_metadata_for_unknown_proof(self, sxt_provider):
        """Unknown proof returns None."""
        metadata = sxt_provider.get_proof_metadata("unknown:hash")
        assert metadata is None

    def test_count_proofs(self, sxt_provider, proof_input):
        """Proof counting works correctly."""
        assert sxt_provider.count_proofs() == 0
        
        sxt_provider.generate_proof(proof_input)
        assert sxt_provider.count_proofs() == 1

    def test_list_proof_hashes(self, sxt_provider, proof_input):
        """Listing returns hash-only references."""
        output = sxt_provider.generate_proof(proof_input)
        hashes = sxt_provider.list_proof_hashes()
        
        assert output.proof_hash in hashes
        # Should be strings, not full objects
        assert all(isinstance(h, str) for h in hashes)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: REGISTRY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistryIntegration:
    """Tests for provider registry integration."""

    def test_register_with_registry(self, sxt_provider):
        """Provider can be registered with global registry."""
        reset_proof_registry()
        registry = get_proof_registry()
        
        registry.register(sxt_provider)
        registry.set_primary(sxt_provider.provider_id)
        
        primary = registry.get_primary()
        assert primary.provider_id == "SPACE_AND_TIME_P2"

    def test_fallback_to_local_hash(self):
        """Registry falls back to local hash if primary unavailable."""
        reset_proof_registry()
        registry = get_proof_registry()
        
        # Don't set a primary
        primary = registry.get_primary()
        
        # Should fall back to LOCAL_HASH_P0
        assert primary.provider_id == "LOCAL_HASH_P0"

    def test_list_providers(self, sxt_provider):
        """Registry lists all registered providers."""
        reset_proof_registry()
        registry = get_proof_registry()
        registry.register(sxt_provider)
        
        providers = registry.list_providers()
        
        assert "LOCAL_HASH_P0" in providers
        assert "SPACE_AND_TIME_P2" in providers


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingletonManagement:
    """Tests for singleton provider access."""

    def test_get_singleton(self):
        """Global singleton access works."""
        reset_space_and_time_provider()
        
        provider1 = get_space_and_time_provider(mock_mode=True)
        provider2 = get_space_and_time_provider()
        
        assert provider1 is provider2

    def test_reset_singleton(self):
        """Singleton can be reset."""
        provider1 = get_space_and_time_provider(mock_mode=True)
        reset_space_and_time_provider()
        provider2 = get_space_and_time_provider(mock_mode=True)
        
        assert provider1 is not provider2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONFIG FROM ENV
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigFromEnv:
    """Tests for environment-based configuration."""

    def test_config_defaults(self):
        """Default config has sensible values."""
        config = SpaceAndTimeConfig()
        
        assert config.namespace == "chainbridge_governance"
        assert config.proof_format == "snark"
        assert config.timeout_seconds == 30

    def test_config_from_env(self, monkeypatch):
        """Config loads from environment variables."""
        monkeypatch.setenv("SXT_NAMESPACE", "custom_namespace")
        monkeypatch.setenv("SXT_TIMEOUT", "60")
        
        config = SpaceAndTimeConfig.from_env()
        
        assert config.namespace == "custom_namespace"
        assert config.timeout_seconds == 60
