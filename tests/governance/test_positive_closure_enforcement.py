"""
Test POSITIVE_CLOSURE Enforcement — PAC-030 Compliance Tests.

This test suite validates all POSITIVE_CLOSURE invariants:
    INV-PC-001: BER without POSITIVE_CLOSURE is INVALID
    INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists
    INV-PC-003: POSITIVE_CLOSURE may only be emitted by GID-00
    INV-PC-004: Must reference PAC ID, BER ID, all WRAP hashes, final state
    INV-PC-005: Absence forces SESSION_INVALID

PAC Reference: PAC-JEFFREY-DRAFT-GOVERNANCE-POSITIVE-CLOSURE-STANDARD-030
"""

import pytest
from datetime import datetime, timezone

# =============================================================================
# POSITIVE_CLOSURE CORE TESTS
# =============================================================================

class TestPositiveClosureCreation:
    """Test POSITIVE_CLOSURE creation and validation."""
    
    def test_create_positive_closure_with_builder(self):
        """Test creating POSITIVE_CLOSURE using ClosureBuilder."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            POSITIVE_CLOSURE_AUTHORITY,
        )
        
        builder = ClosureBuilder(
            pac_id="PAC-TEST-001",
            ber_id="BER-TEST-001",
        )
        builder.add_wrap_hash("wrap_hash_agent_1")
        builder.add_wrap_hash("wrap_hash_agent_2")
        builder.set_final_state("SESSION_CLOSED")
        builder.set_invariants_verified(True)
        builder.set_checkpoints_resolved(0)
        
        closure = builder.build()
        
        assert closure.pac_id == "PAC-TEST-001"
        assert closure.ber_id == "BER-TEST-001"
        assert closure.issuer == POSITIVE_CLOSURE_AUTHORITY
        assert closure.wrap_count == 2
        assert closure.final_state == "SESSION_CLOSED"
        assert closure.invariants_verified is True
        assert closure.closure_hash is not None
        assert len(closure.closure_hash) == 64  # SHA-256 hex
    
    def test_create_positive_closure_with_factory(self):
        """Test creating POSITIVE_CLOSURE using factory function."""
        from core.governance.positive_closure import (
            create_positive_closure,
            POSITIVE_CLOSURE_AUTHORITY,
        )
        
        closure = create_positive_closure(
            pac_id="PAC-TEST-002",
            ber_id="BER-TEST-002",
            wrap_hashes=["hash1", "hash2", "hash3"],
            final_state="SESSION_CLOSED",
            invariants_verified=True,
            checkpoints_resolved=0,
        )
        
        assert closure.pac_id == "PAC-TEST-002"
        assert closure.issuer == POSITIVE_CLOSURE_AUTHORITY
        assert closure.wrap_count == 3
        assert "PC-" in closure.closure_id
    
    def test_closure_hash_is_deterministic(self):
        """Test that closure hash is deterministic for same inputs."""
        from core.governance.positive_closure import ClosureBuilder
        
        # Create two closures with identical content
        # Note: timestamp will differ, so we compare hash computation logic
        builder1 = ClosureBuilder(pac_id="PAC-DET", ber_id="BER-DET")
        builder1.add_wrap_hash("hash_a")
        builder1.set_final_state("SESSION_CLOSED")
        
        # Validate the hash computation mechanism
        from core.governance.positive_closure import compute_closure_hash_from_parts
        
        fixed_timestamp = "2025-01-01T00:00:00+00:00"
        hash1 = compute_closure_hash_from_parts(
            pac_id="PAC-DET",
            ber_id="BER-DET",
            wrap_hashes=("hash_a",),
            wrap_count=1,
            final_state="SESSION_CLOSED",
            issuer="GID-00",
            closed_at=fixed_timestamp,
        )
        hash2 = compute_closure_hash_from_parts(
            pac_id="PAC-DET",
            ber_id="BER-DET",
            wrap_hashes=("hash_a",),
            wrap_count=1,
            final_state="SESSION_CLOSED",
            issuer="GID-00",
            closed_at=fixed_timestamp,
        )
        
        assert hash1 == hash2
    
    def test_closure_is_immutable(self):
        """Test that PositiveClosure is immutable (frozen dataclass)."""
        from core.governance.positive_closure import create_positive_closure
        
        closure = create_positive_closure(
            pac_id="PAC-IMMUT",
            ber_id="BER-IMMUT",
            wrap_hashes=["hash1"],
            final_state="SESSION_CLOSED",
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            closure.pac_id = "MODIFIED"


# =============================================================================
# INV-PC-001: BER WITHOUT POSITIVE_CLOSURE IS INVALID
# =============================================================================

class TestINVPC001BERWithoutClosure:
    """INV-PC-001: BER without POSITIVE_CLOSURE is INVALID."""
    
    def test_validate_closure_for_ber_fails_when_missing(self):
        """Test that BER validation fails when closure is missing."""
        from core.governance.positive_closure import validate_closure_for_ber
        
        result = validate_closure_for_ber(
            closure=None,
            ber_id="BER-ORPHAN-001",
        )
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert "INV-PC-001" in result.errors[0]
    
    def test_validate_closure_for_ber_succeeds_when_present(self):
        """Test that BER validation succeeds when closure exists."""
        from core.governance.positive_closure import (
            create_positive_closure,
            validate_closure_for_ber,
        )
        
        closure = create_positive_closure(
            pac_id="PAC-VALID",
            ber_id="BER-VALID-001",
            wrap_hashes=["hash1"],
            final_state="SESSION_CLOSED",
        )
        
        result = validate_closure_for_ber(
            closure=closure,
            ber_id="BER-VALID-001",
        )
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_enforce_closure_before_ber_raises_on_missing(self):
        """Test that enforcement raises when closure is missing."""
        from core.governance.positive_closure import (
            enforce_closure_before_ber,
            PositiveClosureBERMissingError,
        )
        
        with pytest.raises(PositiveClosureBERMissingError):
            enforce_closure_before_ber(
                closure=None,
                ber_id="BER-MISSING-001",
            )
    
    def test_ber_schema_orphan_detection(self):
        """Test BERSchemaV2 orphan detection."""
        from core.governance.ber_schema import (
            create_ber_v2,
            emit_ber_v2,
            BERState,
        )
        
        # Create and emit BER without binding closure
        ber = create_ber_v2(
            pac_id="PAC-ORPHAN",
            decision="APPROVE",
            wrap_status="COMPLETE",
        )
        ber = emit_ber_v2(ber)
        
        assert ber.is_emitted is True
        assert ber.is_orphaned is True  # No closure bound
        assert ber.state == BERState.EMITTED
    
    def test_ber_schema_closure_binding(self):
        """Test BERSchemaV2 closure binding."""
        from core.governance.ber_schema import (
            create_ber_v2,
            emit_ber_v2,
            BERState,
        )
        
        ber = create_ber_v2(
            pac_id="PAC-BOUND",
            decision="APPROVE",
        )
        ber = emit_ber_v2(ber)
        ber = ber.bind_closure(
            closure_id="PC-TEST-001",
            closure_hash="a" * 64,
        )
        
        assert ber.is_closure_bound is True
        assert ber.is_orphaned is False
        assert ber.state == BERState.CLOSURE_BOUND


# =============================================================================
# INV-PC-002: PDO MAY NOT BE EMITTED UNLESS POSITIVE_CLOSURE EXISTS
# =============================================================================

class TestINVPC002PDORequiresClosure:
    """INV-PC-002: PDO may not be emitted unless POSITIVE_CLOSURE exists."""
    
    def test_validate_closure_for_pdo_fails_when_missing(self):
        """Test that PDO validation fails when closure is missing."""
        from core.governance.positive_closure import validate_closure_for_pdo
        
        result = validate_closure_for_pdo(
            closure=None,
            pac_id="PAC-NO-CLOSURE",
        )
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert "INV-PC-002" in result.errors[0]
    
    def test_validate_closure_for_pdo_succeeds_when_present(self):
        """Test that PDO validation succeeds when closure exists."""
        from core.governance.positive_closure import (
            create_positive_closure,
            validate_closure_for_pdo,
        )
        
        closure = create_positive_closure(
            pac_id="PAC-WITH-CLOSURE",
            ber_id="BER-001",
            wrap_hashes=["hash1"],
            final_state="SESSION_CLOSED",
        )
        
        result = validate_closure_for_pdo(
            closure=closure,
            pac_id="PAC-WITH-CLOSURE",
        )
        
        assert result.valid is True
    
    def test_enforce_closure_before_pdo_raises_on_missing(self):
        """Test that enforcement raises when closure is missing."""
        from core.governance.positive_closure import (
            enforce_closure_before_pdo,
            PositiveClosureNotEmittedError,
        )
        
        with pytest.raises(PositiveClosureNotEmittedError):
            enforce_closure_before_pdo(
                closure=None,
                pac_id="PAC-BLOCKED",
            )
    
    def test_pdo_schema_requires_closure_hash(self):
        """Test PDOSchemaV2 requires closure_hash."""
        from core.governance.pdo_schema import (
            PDOSchemaV2,
            PDOClosureMissingError,
        )
        
        # Should raise when closure_hash is empty/None
        with pytest.raises(PDOClosureMissingError):
            PDOSchemaV2(
                pdo_id="PDO-TEST",
                pac_id="PAC-TEST",
                wrap_id="WRAP-TEST",
                ber_id="BER-TEST",
                issuer="GID-00",
                proof_hash="a" * 64,
                decision_hash="b" * 64,
                outcome_hash="c" * 64,
                pdo_hash="d" * 64,
                closure_id="",
                closure_hash="",  # Empty - should fail
                proof_at="2025-01-01T00:00:00Z",
                decision_at="2025-01-01T00:00:00Z",
                outcome_at="2025-01-01T00:00:00Z",
                created_at="2025-01-01T00:00:00Z",
                outcome_status="ACCEPTED",
            )
    
    def test_pdo_factory_enforces_closure_requirement(self):
        """Test create_pdo_v2 enforces closure requirement."""
        from core.governance.pdo_schema import (
            create_pdo_v2,
            PDOClosureMissingError,
        )
        
        with pytest.raises(PDOClosureMissingError):
            create_pdo_v2(
                pac_id="PAC-NO-CLOSURE",
                wrap_id="WRAP-001",
                wrap_data={"status": "COMPLETE"},
                ber_id="BER-001",
                ber_data={"decision": "APPROVE"},
                outcome_status="ACCEPTED",
                closure_id="",
                closure_hash="",  # Empty - should fail
            )
    
    def test_pdo_creation_succeeds_with_closure(self):
        """Test PDO creation succeeds when closure is provided."""
        from core.governance.pdo_schema import create_pdo_v2
        
        pdo = create_pdo_v2(
            pac_id="PAC-WITH-CLOSURE",
            wrap_id="WRAP-001",
            wrap_data={"status": "COMPLETE"},
            ber_id="BER-001",
            ber_data={"decision": "APPROVE"},
            outcome_status="ACCEPTED",
            closure_id="PC-12345",
            closure_hash="a" * 64,
        )
        
        assert pdo.pac_id == "PAC-WITH-CLOSURE"
        assert pdo.closure_id == "PC-12345"
        assert pdo.has_valid_closure is True


# =============================================================================
# INV-PC-003: POSITIVE_CLOSURE MAY ONLY BE EMITTED BY GID-00
# =============================================================================

class TestINVPC003ExclusiveAuthority:
    """INV-PC-003: POSITIVE_CLOSURE may only be emitted by GID-00."""
    
    def test_closure_authority_check_succeeds_for_gid00(self):
        """Test that GID-00 can create closures."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            POSITIVE_CLOSURE_AUTHORITY,
        )
        
        builder = ClosureBuilder(pac_id="PAC-AUTH", ber_id="BER-AUTH")
        builder.add_wrap_hash("hash1")
        builder.set_final_state("SESSION_CLOSED")
        
        # Builder internally uses GID-00, should succeed
        closure = builder.build()
        assert closure.issuer == POSITIVE_CLOSURE_AUTHORITY
    
    def test_closure_authority_check_fails_for_agents(self):
        """Test that agents cannot create closures."""
        from core.governance.positive_closure import (
            PositiveClosure,
            PositiveClosureAuthorityError,
            compute_closure_hash_from_parts,
        )
        
        # Compute valid hash
        now = datetime.now(timezone.utc).isoformat()
        closure_hash = compute_closure_hash_from_parts(
            pac_id="PAC-AUTH",
            ber_id="BER-AUTH",
            wrap_hashes=("hash1",),
            wrap_count=1,
            final_state="SESSION_CLOSED",
            issuer="GID-01",  # Agent attempting creation
            closed_at=now,
        )
        
        # Should raise when agent tries to create
        with pytest.raises(PositiveClosureAuthorityError) as exc_info:
            PositiveClosure(
                closure_id="PC-INVALID",
                pac_id="PAC-AUTH",
                ber_id="BER-AUTH",
                wrap_hashes=("hash1",),
                wrap_count=1,
                final_state="SESSION_CLOSED",
                invariants_verified=True,
                checkpoints_resolved=0,
                issuer="GID-01",  # Agent - INVALID
                closed_at=now,
                closure_hash=closure_hash,
            )
        
        assert "GID-01" in str(exc_info.value)
        assert "INV-PC-003" in str(exc_info.value)
    
    def test_enforce_closure_authority_raises_for_non_gid00(self):
        """Test enforcement function raises for non-GID-00."""
        from core.governance.positive_closure import (
            enforce_closure_authority,
            PositiveClosureAuthorityError,
        )
        
        with pytest.raises(PositiveClosureAuthorityError):
            enforce_closure_authority("GID-07")  # Dan the Agent
        
        with pytest.raises(PositiveClosureAuthorityError):
            enforce_closure_authority("JEFFREY")  # Drafting surface


# =============================================================================
# INV-PC-004: MUST REFERENCE PAC ID, BER ID, ALL WRAP HASHES, FINAL STATE
# =============================================================================

class TestINVPC004RequiredReferences:
    """INV-PC-004: Must reference PAC ID, BER ID, all WRAP hashes, final state."""
    
    def test_builder_validation_fails_without_pac_id(self):
        """Test builder fails without PAC ID."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            PositiveClosureIncompleteError,
        )
        
        builder = ClosureBuilder(pac_id="", ber_id="BER-001")  # Empty PAC
        builder.add_wrap_hash("hash1")
        builder.set_final_state("SESSION_CLOSED")
        
        with pytest.raises(PositiveClosureIncompleteError) as exc_info:
            builder.build()
        
        assert "pac_id" in str(exc_info.value)
    
    def test_builder_validation_fails_without_ber_id(self):
        """Test builder fails without BER ID."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            PositiveClosureIncompleteError,
        )
        
        builder = ClosureBuilder(pac_id="PAC-001", ber_id="")  # Empty BER
        builder.add_wrap_hash("hash1")
        builder.set_final_state("SESSION_CLOSED")
        
        with pytest.raises(PositiveClosureIncompleteError):
            builder.build()
    
    def test_builder_validation_fails_without_wraps(self):
        """Test builder fails without WRAP hashes."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            PositiveClosureIncompleteError,
        )
        
        builder = ClosureBuilder(pac_id="PAC-001", ber_id="BER-001")
        # No wrap hashes added
        builder.set_final_state("SESSION_CLOSED")
        
        with pytest.raises(PositiveClosureIncompleteError) as exc_info:
            builder.build()
        
        assert "wrap_hash" in str(exc_info.value)
    
    def test_builder_validation_fails_without_final_state(self):
        """Test builder fails without final state."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            PositiveClosureIncompleteError,
        )
        
        builder = ClosureBuilder(pac_id="PAC-001", ber_id="BER-001")
        builder.add_wrap_hash("hash1")
        # No final state set
        
        with pytest.raises(PositiveClosureIncompleteError):
            builder.build()
    
    def test_validate_closure_wraps_detects_missing(self):
        """Test WRAP validation detects missing hashes."""
        from core.governance.positive_closure import (
            create_positive_closure,
            validate_closure_wraps,
        )
        
        closure = create_positive_closure(
            pac_id="PAC-WRAPS",
            ber_id="BER-WRAPS",
            wrap_hashes=["hash1", "hash2"],
            final_state="SESSION_CLOSED",
        )
        
        # Validate against expected 3 hashes (missing hash3)
        result = validate_closure_wraps(
            closure=closure,
            expected_wrap_hashes=["hash1", "hash2", "hash3"],
        )
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert "hash3" in str(result.errors)


# =============================================================================
# INV-PC-005: ABSENCE FORCES SESSION_INVALID
# =============================================================================

class TestINVPC005AbsenceForcesInvalid:
    """INV-PC-005: Absence of POSITIVE_CLOSURE forces SESSION_INVALID."""
    
    def test_enforce_session_closure_raises_when_missing(self):
        """Test that session enforcement raises when closure missing."""
        from core.governance.positive_closure import (
            enforce_session_closure,
            PositiveClosureNotEmittedError,
        )
        
        with pytest.raises(PositiveClosureNotEmittedError) as exc_info:
            enforce_session_closure(
                closure=None,
                pac_id="PAC-SESSION-INVALID",
                session_id="SESSION-001",
            )
        
        assert "PAC-SESSION-INVALID" in str(exc_info.value)
        assert "INVALID" in str(exc_info.value)
        assert "INV-PC-005" in str(exc_info.value)
    
    def test_loop_state_is_not_closed_without_closure(self):
        """Test LoopState.is_loop_closed is False without closure."""
        from core.governance.orchestration_engine import LoopState, DispatchStatus
        from core.governance.pac_schema import WRAPStatus, BERStatus
        
        loop = LoopState(pac_id="PAC-INCOMPLETE")
        loop.status = DispatchStatus.DISPATCHED
        
        # Record WRAP
        loop.record_wrap(WRAPStatus.COMPLETE)
        
        # Record BER
        loop.record_ber(BERStatus.APPROVE)
        
        # Simulate BER emission without closure
        loop.ber_emitted = True
        loop.ber_emitted_at = datetime.now(timezone.utc).isoformat()
        
        # PDO recorded but no closure
        loop.pdo_emitted = True
        loop.pdo_emitted_at = datetime.now(timezone.utc).isoformat()
        
        # Loop should NOT be closed because positive_closure_emitted is False
        assert loop.positive_closure_emitted is False
        assert loop.is_loop_closed is False
    
    def test_loop_state_is_closed_with_closure(self):
        """Test LoopState.is_loop_closed is True with closure."""
        from core.governance.orchestration_engine import LoopState, DispatchStatus
        from core.governance.pac_schema import WRAPStatus, BERStatus
        from core.governance.positive_closure import create_positive_closure
        
        loop = LoopState(pac_id="PAC-COMPLETE")
        loop.status = DispatchStatus.DISPATCHED
        
        # Record WRAP
        loop.record_wrap(WRAPStatus.COMPLETE)
        
        # Record BER
        loop.record_ber(BERStatus.APPROVE)
        
        # Simulate BER emission
        loop.ber_emitted = True
        loop.ber_emitted_at = datetime.now(timezone.utc).isoformat()
        
        # Create and record POSITIVE_CLOSURE
        closure = create_positive_closure(
            pac_id="PAC-COMPLETE",
            ber_id=loop.ber_id,
            wrap_hashes=[loop.wrap_hash or "hash1"],
            final_state="SESSION_CLOSED",
        )
        loop.record_positive_closure(closure)
        
        # Record PDO
        loop.pdo_emitted = True
        loop.pdo_emitted_at = datetime.now(timezone.utc).isoformat()
        
        # Now loop should be closed
        assert loop.positive_closure_emitted is True
        assert loop.is_loop_closed is True


# =============================================================================
# ORCHESTRATION ENGINE INTEGRATION TESTS
# =============================================================================

class TestOrchestrationEnginePositiveClosure:
    """Test POSITIVE_CLOSURE integration with orchestration engine."""
    
    def test_loop_state_records_positive_closure(self):
        """Test that LoopState.record_positive_closure works correctly."""
        from core.governance.orchestration_engine import LoopState, DispatchStatus
        from core.governance.positive_closure import create_positive_closure
        
        loop = LoopState(pac_id="PAC-RECORD-TEST")
        loop.status = DispatchStatus.DISPATCHED
        
        # Create closure
        closure = create_positive_closure(
            pac_id="PAC-RECORD-TEST",
            ber_id="BER-RECORD",
            wrap_hashes=["hash1"],
            final_state="SESSION_CLOSED",
        )
        
        # Record it
        loop.record_positive_closure(closure)
        
        assert loop.positive_closure_emitted is True
        assert loop.positive_closure is not None
        assert loop.positive_closure.pac_id == "PAC-RECORD-TEST"
    
    def test_loop_state_awaiting_positive_closure_property(self):
        """Test awaiting_positive_closure property on LoopState."""
        from core.governance.orchestration_engine import LoopState, DispatchStatus
        from core.governance.pac_schema import WRAPStatus, BERStatus
        
        loop = LoopState(pac_id="PAC-AWAIT-TEST")
        loop.status = DispatchStatus.DISPATCHED
        
        # Initially not awaiting closure (no BER emitted)
        assert loop.awaiting_positive_closure is False
        
        # Record WRAP
        loop.record_wrap(WRAPStatus.COMPLETE)
        assert loop.awaiting_positive_closure is False  # Still need BER
        
        # Record BER
        loop.record_ber(BERStatus.APPROVE)
        assert loop.awaiting_positive_closure is False  # Still need emission
        
        # BER emitted
        loop.ber_emitted = True
        assert loop.awaiting_positive_closure is True  # Now awaiting closure!
        
        # After closure
        from core.governance.positive_closure import create_positive_closure
        closure = create_positive_closure(
            pac_id="PAC-AWAIT-TEST",
            ber_id=loop.ber_id,
            wrap_hashes=[loop.wrap_hash or "hash1"],
            final_state="SESSION_CLOSED",
        )
        loop.record_positive_closure(closure)
        assert loop.awaiting_positive_closure is False  # No longer awaiting
    
    def test_is_loop_closed_requires_all_components(self):
        """Test that is_loop_closed requires POSITIVE_CLOSURE."""
        from core.governance.orchestration_engine import LoopState, DispatchStatus
        from core.governance.pac_schema import WRAPStatus, BERStatus
        from core.governance.positive_closure import create_positive_closure
        
        loop = LoopState(pac_id="PAC-FULL-CLOSURE")
        loop.status = DispatchStatus.DISPATCHED
        
        # Step through the full closure sequence
        assert loop.is_loop_closed is False
        
        loop.record_wrap(WRAPStatus.COMPLETE)
        assert loop.is_loop_closed is False
        
        loop.record_ber(BERStatus.APPROVE)
        assert loop.is_loop_closed is False
        
        loop.ber_emitted = True
        loop.ber_emitted_at = "2025-01-01T00:00:00Z"
        assert loop.is_loop_closed is False  # Missing closure and PDO
        
        # Add PDO but not closure - still not closed
        loop.pdo_emitted = True
        loop.pdo_emitted_at = "2025-01-01T00:00:00Z"
        assert loop.is_loop_closed is False  # Missing closure!
        
        # Now add closure
        closure = create_positive_closure(
            pac_id="PAC-FULL-CLOSURE",
            ber_id=loop.ber_id,
            wrap_hashes=[loop.wrap_hash or "hash1"],
            final_state="SESSION_CLOSED",
        )
        loop.record_positive_closure(closure)
        
        # NOW it's closed
        assert loop.is_loop_closed is True


# =============================================================================
# HASH VERIFICATION TESTS
# =============================================================================

class TestClosureHashVerification:
    """Test closure hash verification."""
    
    def test_verify_closure_hash_succeeds_for_valid(self):
        """Test hash verification succeeds for valid closure."""
        from core.governance.positive_closure import (
            create_positive_closure,
            verify_closure_hash,
        )
        
        closure = create_positive_closure(
            pac_id="PAC-HASH",
            ber_id="BER-HASH",
            wrap_hashes=["hash1", "hash2"],
            final_state="SESSION_CLOSED",
        )
        
        assert verify_closure_hash(closure) is True
    
    def test_closure_hash_mismatch_raises(self):
        """Test that hash mismatch raises during construction."""
        from core.governance.positive_closure import (
            PositiveClosure,
            PositiveClosureHashMismatchError,
        )
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Try to create closure with wrong hash
        with pytest.raises(PositiveClosureHashMismatchError):
            PositiveClosure(
                closure_id="PC-BAD",
                pac_id="PAC-BAD",
                ber_id="BER-BAD",
                wrap_hashes=("hash1",),
                wrap_count=1,
                final_state="SESSION_CLOSED",
                invariants_verified=True,
                checkpoints_resolved=0,
                issuer="GID-00",
                closed_at=now,
                closure_hash="wrong_hash_value",  # Invalid hash
            )


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================

class TestClosureSerialization:
    """Test closure serialization and deserialization."""
    
    def test_closure_to_dict_and_back(self):
        """Test closure can be serialized to dict and back."""
        from core.governance.positive_closure import (
            create_positive_closure,
            PositiveClosure,
        )
        
        original = create_positive_closure(
            pac_id="PAC-SERIAL",
            ber_id="BER-SERIAL",
            wrap_hashes=["h1", "h2"],
            final_state="SESSION_CLOSED",
        )
        
        # To dict
        data = original.to_dict()
        assert data["pac_id"] == "PAC-SERIAL"
        assert data["wrap_count"] == 2
        
        # From dict
        restored = PositiveClosure.from_dict(data)
        assert restored.pac_id == original.pac_id
        assert restored.closure_hash == original.closure_hash
        assert restored.wrap_hashes == original.wrap_hashes
    
    def test_ber_schema_serialization(self):
        """Test BERSchemaV2 serialization."""
        from core.governance.ber_schema import create_ber_v2, BERSchemaV2
        
        ber = create_ber_v2(
            pac_id="PAC-BER-SERIAL",
            decision="APPROVE",
            wrap_status="COMPLETE",
        )
        
        data = ber.to_dict()
        restored = BERSchemaV2.from_dict(data)
        
        assert restored.pac_id == ber.pac_id
        assert restored.decision == ber.decision
    
    def test_pdo_schema_serialization(self):
        """Test PDOSchemaV2 serialization."""
        from core.governance.pdo_schema import create_pdo_v2, PDOSchemaV2
        
        pdo = create_pdo_v2(
            pac_id="PAC-PDO-SERIAL",
            wrap_id="WRAP-001",
            wrap_data={"status": "COMPLETE"},
            ber_id="BER-001",
            ber_data={"decision": "APPROVE"},
            outcome_status="ACCEPTED",
            closure_id="PC-001",
            closure_hash="a" * 64,
        )
        
        data = pdo.to_dict()
        restored = PDOSchemaV2.from_dict(data)
        
        assert restored.pac_id == pdo.pac_id
        assert restored.closure_hash == pdo.closure_hash


# =============================================================================
# DECISION TYPES TESTS
# =============================================================================

class TestClosureDecisionTypes:
    """Test different closure decision types."""
    
    def test_clean_closure(self):
        """Test CLEAN closure decision."""
        from core.governance.positive_closure import create_positive_closure
        
        closure = create_positive_closure(
            pac_id="PAC-CLEAN",
            ber_id="BER-CLEAN",
            wrap_hashes=["h1"],
            final_state="SESSION_CLOSED",
            decision="CLEAN",
        )
        
        assert closure.decision == "CLEAN"
    
    def test_corrective_closure(self):
        """Test CORRECTIVE closure decision."""
        from core.governance.positive_closure import create_positive_closure
        
        closure = create_positive_closure(
            pac_id="PAC-CORRECTIVE",
            ber_id="BER-CORRECTIVE",
            wrap_hashes=["h1"],
            final_state="SESSION_CLOSED",
            decision="CORRECTIVE",
        )
        
        assert closure.decision == "CORRECTIVE"
    
    def test_invalid_closure(self):
        """Test INVALID closure decision."""
        from core.governance.positive_closure import create_positive_closure
        
        closure = create_positive_closure(
            pac_id="PAC-INVALID",
            ber_id="BER-INVALID",
            wrap_hashes=["h1"],
            final_state="SESSION_CLOSED",
            decision="INVALID",
        )
        
        assert closure.decision == "INVALID"


# =============================================================================
# MULTI-AGENT WRAP TESTS
# =============================================================================

class TestMultiAgentWrapHandling:
    """Test closure with multiple agent WRAPs."""
    
    def test_closure_with_multiple_wraps(self):
        """Test closure correctly tracks multiple WRAP hashes."""
        from core.governance.positive_closure import (
            ClosureBuilder,
            validate_closure_wraps,
        )
        
        builder = ClosureBuilder(pac_id="PAC-MULTI", ber_id="BER-MULTI")
        
        # Add 6 agent WRAP hashes
        agent_hashes = [
            "hash_gid_01",
            "hash_gid_02",
            "hash_gid_03",
            "hash_gid_06",
            "hash_gid_07",
            "hash_gid_10",
        ]
        builder.add_wrap_hashes(agent_hashes)
        builder.set_final_state("SESSION_CLOSED")
        
        closure = builder.build()
        
        assert closure.wrap_count == 6
        
        # Validate all hashes present
        result = validate_closure_wraps(
            closure=closure,
            expected_wrap_hashes=agent_hashes,
        )
        
        assert result.valid is True
    
    def test_wrap_hashes_are_sorted_for_determinism(self):
        """Test that WRAP hashes are sorted for deterministic hashing."""
        from core.governance.positive_closure import ClosureBuilder
        
        # Add hashes in reverse order
        builder = ClosureBuilder(pac_id="PAC-SORT", ber_id="BER-SORT")
        builder.add_wrap_hash("z_hash")
        builder.add_wrap_hash("a_hash")
        builder.add_wrap_hash("m_hash")
        builder.set_final_state("SESSION_CLOSED")
        
        closure = builder.build()
        
        # Verify hashes are sorted in tuple
        assert closure.wrap_hashes == ("a_hash", "m_hash", "z_hash")
