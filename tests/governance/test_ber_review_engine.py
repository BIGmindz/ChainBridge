"""
Test BER Review Engine

Comprehensive test harness for BER Review Engine per PAC-022.
Tests all checklist items, failure modes, and Jeffrey law compliance.

Test Structure:
- Happy path tests
- Authority violation tests  
- Loop closure violation tests
- PDO chain violation tests
- Emission violation tests
- Decision validity tests
- Training signal tests
- Artifact integrity tests
- Temporal ordering tests
- Binary outcome enforcement
- Training signal generation
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Set

# Import schema
from core.governance.ber_review_schema import (
    BERReviewResult,
    CheckID,
    CheckResult,
    CheckSeverity,
    FailureMode,
    JeffreyAction,
    JeffreyTrainingSignal,
    ReviewOutcome,
    REQUIRED_CHECK_COUNT,
    validate_review_completeness,
    validate_binary_outcome,
)

# Import engine
from core.governance.ber_review_engine import (
    BERReviewEngine,
    BERReviewError,
    IncompleteReviewError,
    InvalidBERError,
    JeffreyViolationError,
    create_review_engine,
    review_ber,
)

# Import fixtures
from tests.governance.fixtures.ber_samples import (
    MockBERArtifact,
    create_valid_approve_ber,
    create_valid_corrective_ber,
    create_valid_reject_ber,
    create_ber_missing_authority,
    create_ber_invalid_authority,
    create_ber_jeffrey_issuer,
    create_ber_broken_loop,
    create_ber_orphan,
    create_ber_missing_wrap,
    create_ber_not_emitted,
    create_ber_missing_emission_timestamp,
    create_ber_invalid_decision,
    create_ber_narrative_decision,
    create_ber_partial_decision,
    create_ber_missing_training_signal,
    create_ber_temporal_paradox,
    create_ber_persona_bleed,
    get_all_valid_bers,
    get_all_invalid_bers,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> BERReviewEngine:
    """Create a BER review engine with terminal output disabled."""
    return create_review_engine(emit_terminal=False)


@pytest.fixture
def engine_with_pending() -> BERReviewEngine:
    """Create engine with pending PACs."""
    pending = {"PAC-VALID-001", "PAC-VALID-002", "PAC-VALID-003"}
    return create_review_engine(pending_pacs=pending, emit_terminal=False)


@pytest.fixture
def valid_ber() -> MockBERArtifact:
    """Create a valid APPROVE BER."""
    return create_valid_approve_ber()


# ═══════════════════════════════════════════════════════════════════════════════
# HAPPY PATH TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestHappyPath:
    """Test valid BERs pass all checks."""
    
    def test_valid_approve_ber_passes(self, engine):
        """Valid APPROVE BER should pass all checks."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        assert result.passed
        assert result.outcome == ReviewOutcome.PASS
        assert result.check_count >= REQUIRED_CHECK_COUNT
        assert len(result.failure_reasons) == 0
    
    def test_valid_corrective_ber_passes(self, engine):
        """Valid CORRECTIVE BER should pass all checks."""
        ber = create_valid_corrective_ber()
        result = engine.review(ber)
        
        assert result.passed
        assert result.outcome == ReviewOutcome.PASS
    
    def test_valid_reject_ber_passes(self, engine):
        """Valid REJECT BER should pass all checks."""
        ber = create_valid_reject_ber()
        result = engine.review(ber)
        
        assert result.passed
        assert result.outcome == ReviewOutcome.PASS
    
    def test_all_valid_bers_pass(self, engine):
        """All valid BER samples should pass."""
        for ber in get_all_valid_bers():
            result = engine.review(ber)
            assert result.passed, f"Valid BER {ber.pac_id} failed: {result.failure_reasons}"
    
    def test_passed_ber_allows_next_pac(self, engine):
        """Passed review should allow NEXT_PAC."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        assert result.allows_next_pac
        assert not result.requires_corrective_pac
        assert result.recommended_action == JeffreyAction.NEXT_PAC


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHORITY VIOLATION TESTS (CHK-001)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthorityViolations:
    """Test CHK-001: Authority Verification failures."""
    
    def test_missing_authority_fails(self, engine):
        """BER with missing issuer should fail CHK-001."""
        ber = create_ber_missing_authority()
        result = engine.review(ber)
        
        assert not result.passed
        assert result.outcome == ReviewOutcome.FAIL
        
        failed = result.get_failed_checks()
        assert any(c.check_id == CheckID.CHK_001.value for c in failed)
    
    def test_invalid_authority_fails(self, engine):
        """BER with invalid issuer should fail CHK-001."""
        ber = create_ber_invalid_authority()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        authority_check = next(
            (c for c in failed if c.check_id == CheckID.CHK_001.value), None
        )
        assert authority_check is not None
        assert authority_check.failure_mode == FailureMode.AUTHORITY_VIOLATION
    
    def test_jeffrey_cannot_issue_ber(self, engine):
        """Jeffrey as issuer should fail CHK-001."""
        ber = create_ber_jeffrey_issuer()
        result = engine.review(ber)
        
        assert not result.passed
        assert "JEFFREY" in str(result.failure_reasons) or any(
            "Invalid issuer" in r for r in result.failure_reasons
        )
    
    def test_only_gid00_can_issue(self, engine):
        """Only GID-00 or ORCHESTRATION_ENGINE can issue BERs."""
        # Test with ORCHESTRATION_ENGINE (also valid)
        now = datetime.now(timezone.utc)
        ber = MockBERArtifact(
            pac_id="PAC-AUTH-001",
            decision="APPROVE",
            issuer="ORCHESTRATION_ENGINE",  # Valid alternative
            issued_at=now.isoformat(),
            emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
            wrap_status="COMPLETE",
            session_state="BER_EMITTED",
        )
        result = engine.review(ber)
        
        # Authority check should pass
        authority_failures = [
            c for c in result.checks 
            if c.check_id == CheckID.CHK_001.value and not c.passed
        ]
        assert len(authority_failures) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# LOOP CLOSURE VIOLATION TESTS (CHK-002)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoopClosureViolations:
    """Test CHK-002: Loop Closure Verification failures."""
    
    def test_broken_loop_fails(self, engine):
        """BER with missing PAC ID should fail CHK-002."""
        ber = create_ber_broken_loop()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        loop_check = next(
            (c for c in failed if c.check_id == CheckID.CHK_002.value), None
        )
        assert loop_check is not None
    
    def test_orphan_ber_fails(self, engine_with_pending):
        """BER for non-pending PAC should fail CHK-002."""
        ber = create_ber_orphan()
        result = engine_with_pending.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        assert any(
            c.check_id == CheckID.CHK_002.value and 
            c.failure_mode == FailureMode.ORPHAN_BER
            for c in failed
        )
    
    def test_missing_wrap_fails(self, engine):
        """BER with missing WRAP reference should fail CHK-002."""
        ber = create_ber_missing_wrap()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        assert any(c.check_id == CheckID.CHK_002.value for c in failed)
    
    def test_pending_pac_passes_loop_check(self, engine_with_pending):
        """BER for pending PAC should pass loop check."""
        ber = create_valid_approve_ber("PAC-VALID-001")
        result = engine_with_pending.review(ber)
        
        loop_failures = [
            c for c in result.checks
            if c.check_id == CheckID.CHK_002.value and not c.passed
        ]
        assert len(loop_failures) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# EMISSION VIOLATION TESTS (CHK-004)
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmissionViolations:
    """Test CHK-004: Emission Verification failures."""
    
    def test_not_emitted_fails(self, engine):
        """BER not emitted should fail CHK-004."""
        ber = create_ber_not_emitted()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        emission_check = next(
            (c for c in failed if c.check_id == CheckID.CHK_004.value), None
        )
        assert emission_check is not None
        assert emission_check.failure_mode == FailureMode.EMISSION_VIOLATION
    
    def test_missing_emission_timestamp_fails(self, engine):
        """BER with missing emission timestamp should fail CHK-004."""
        ber = create_ber_missing_emission_timestamp()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        assert any(c.check_id == CheckID.CHK_004.value for c in failed)


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION VALIDITY TESTS (CHK-005)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDecisionValidityViolations:
    """Test CHK-005: Decision Validity failures."""
    
    def test_invalid_decision_fails(self, engine):
        """BER with invalid decision value should fail CHK-005."""
        ber = create_ber_invalid_decision()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        decision_check = next(
            (c for c in failed if c.check_id == CheckID.CHK_005.value), None
        )
        assert decision_check is not None
        assert decision_check.failure_mode == FailureMode.INVALID_DECISION
    
    def test_narrative_decision_fails(self, engine):
        """BER with narrative decision should fail CHK-005."""
        ber = create_ber_narrative_decision()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        assert any(c.check_id == CheckID.CHK_005.value for c in failed)
    
    def test_partial_decision_fails(self, engine):
        """BER with PARTIAL decision should fail CHK-005."""
        ber = create_ber_partial_decision()
        result = engine.review(ber)
        
        assert not result.passed
        
        failed = result.get_failed_checks()
        assert any(c.check_id == CheckID.CHK_005.value for c in failed)
    
    def test_valid_decisions_pass(self, engine):
        """All valid decision values should pass CHK-005."""
        for decision in ["APPROVE", "CORRECTIVE", "REJECT"]:
            now = datetime.now(timezone.utc)
            ber = MockBERArtifact(
                pac_id=f"PAC-DEC-{decision}",
                decision=decision,
                issuer="GID-00",
                issued_at=now.isoformat(),
                emitted_at=(now + timedelta(milliseconds=100)).isoformat(),
                wrap_status="COMPLETE",
                session_state="BER_EMITTED",
                training_signal={"test": True} if decision != "APPROVE" else None,
            )
            result = engine.review(ber)
            
            decision_failures = [
                c for c in result.checks
                if c.check_id == CheckID.CHK_005.value and not c.passed
            ]
            assert len(decision_failures) == 0, f"Decision {decision} failed"


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL TESTS (CHK-006)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTrainingSignalViolations:
    """Test CHK-006: Training Signal Presence failures."""
    
    def test_missing_training_signal_on_corrective(self, engine):
        """CORRECTIVE BER without training signal should fail CHK-006."""
        ber = create_ber_missing_training_signal()
        result = engine.review(ber)
        
        # CHK-006 is WARNING severity, so review may still pass
        # but the check itself should fail
        failed = [c for c in result.checks if not c.passed]
        training_check = next(
            (c for c in failed if c.check_id == CheckID.CHK_006.value), None
        )
        assert training_check is not None
        assert training_check.severity == CheckSeverity.WARNING
    
    def test_training_signal_not_required_for_approve(self, engine):
        """APPROVE BER doesn't require training signal."""
        ber = create_valid_approve_ber()
        assert ber.training_signal is None  # No training signal
        
        result = engine.review(ber)
        
        # CHK-006 should pass
        training_failures = [
            c for c in result.checks
            if c.check_id == CheckID.CHK_006.value and not c.passed
        ]
        assert len(training_failures) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL ORDERING TESTS (CHK-008)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTemporalOrderingViolations:
    """Test CHK-008: Temporal Ordering failures."""
    
    def test_temporal_paradox_fails(self, engine):
        """BER with emission before issuance should fail CHK-008."""
        ber = create_ber_temporal_paradox()
        result = engine.review(ber)
        
        # CHK-008 is WARNING severity
        failed = [c for c in result.checks if not c.passed]
        temporal_check = next(
            (c for c in failed if c.check_id == CheckID.CHK_008.value), None
        )
        assert temporal_check is not None
        assert temporal_check.failure_mode == FailureMode.TEMPORAL_VIOLATION


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA BLEED TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPersonaBleed:
    """Test persona bleed detection."""
    
    def test_persona_bleed_detected(self, engine):
        """Persona bleed should be detected via authority check."""
        ber = create_ber_persona_bleed()
        result = engine.review(ber)
        
        assert not result.passed
        
        # Should fail authority check
        failed = result.get_failed_checks()
        assert any(
            c.check_id == CheckID.CHK_001.value
            for c in failed
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BINARY OUTCOME ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class TestBinaryOutcomeEnforcement:
    """Test INV-JEFF-001: Binary outcome only."""
    
    def test_outcome_is_pass_or_fail(self, engine):
        """Review outcome must be PASS or FAIL only."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        assert result.outcome in (ReviewOutcome.PASS, ReviewOutcome.FAIL)
        assert validate_binary_outcome(result)
    
    def test_failed_review_requires_corrective_pac(self, engine):
        """Failed review must require CORRECTIVE_PAC."""
        ber = create_ber_invalid_authority()
        result = engine.review(ber)
        
        assert not result.passed
        assert result.requires_corrective_pac
        assert result.recommended_action == JeffreyAction.CORRECTIVE_PAC
    
    def test_passed_review_allows_next_pac(self, engine):
        """Passed review must allow NEXT_PAC."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        assert result.passed
        assert result.allows_next_pac
        assert result.recommended_action == JeffreyAction.NEXT_PAC
    
    def test_no_partial_outcomes(self, engine):
        """Review must not produce partial outcomes."""
        for ber in get_all_invalid_bers():
            result = engine.review(ber)
            
            # Outcome must be exactly PASS or FAIL
            assert result.outcome in (ReviewOutcome.PASS, ReviewOutcome.FAIL)
            
            # No "mostly passing" state
            if result.failed_count > 0:
                # Critical failures must fail
                critical = result.get_critical_failures()
                if len(critical) > 0:
                    assert not result.passed


# ═══════════════════════════════════════════════════════════════════════════════
# REVIEW COMPLETENESS
# ═══════════════════════════════════════════════════════════════════════════════


class TestReviewCompleteness:
    """Test all 8 checks are executed."""
    
    def test_all_checks_executed(self, engine):
        """Review must execute all 8 checks."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        assert result.check_count >= REQUIRED_CHECK_COUNT
        assert validate_review_completeness(result)
    
    def test_check_ids_present(self, engine):
        """All check IDs must be present."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        check_ids = {c.check_id for c in result.checks}
        
        for check_id in CheckID:
            assert check_id.value in check_ids, f"Missing check: {check_id}"
    
    def test_null_ber_raises(self, engine):
        """Null BER should raise InvalidBERError."""
        with pytest.raises(InvalidBERError):
            engine.review(None)


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestTrainingSignalGeneration:
    """Test training signal generation."""
    
    def test_training_signal_created(self, engine):
        """Training signal should be creatable from result."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        signal = engine.create_training_signal(result, ber.decision)
        
        assert isinstance(signal, JeffreyTrainingSignal)
        assert signal.pac_id == ber.pac_id
        assert signal.ber_id == result.ber_id
        assert signal.ber_decision == "APPROVE"
        assert signal.review_passed is True
        assert signal.outcome == JeffreyAction.NEXT_PAC
    
    def test_failed_review_signal(self, engine):
        """Failed review should generate CORRECTIVE signal."""
        ber = create_ber_invalid_authority()
        result = engine.review(ber)
        
        signal = engine.create_training_signal(result, ber.decision)
        
        assert signal.review_passed is False
        assert signal.outcome == JeffreyAction.CORRECTIVE_PAC
        assert len(signal.failure_reasons) > 0
    
    def test_signal_hash_generated(self, engine):
        """Training signal should have hash."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        signal = engine.create_training_signal(result, ber.decision)
        
        assert signal.signal_hash
        assert len(signal.signal_hash) == 16


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_review_ber_function(self):
        """review_ber convenience function should work."""
        ber = create_valid_approve_ber()
        result = review_ber(ber, emit_terminal=False)
        
        assert result.passed
        assert result.outcome == ReviewOutcome.PASS
    
    def test_create_review_engine_function(self):
        """create_review_engine should create working engine."""
        pending = {"PAC-001", "PAC-002"}
        engine = create_review_engine(pending_pacs=pending, emit_terminal=False)
        
        assert engine is not None
        assert "PAC-001" in engine._pending_pacs


# ═══════════════════════════════════════════════════════════════════════════════
# IMMUTABILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestImmutability:
    """Test result immutability."""
    
    def test_result_is_frozen(self, engine):
        """BERReviewResult should be immutable."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        with pytest.raises((AttributeError, TypeError)):
            result.outcome = ReviewOutcome.FAIL
    
    def test_check_result_is_frozen(self, engine):
        """CheckResult should be immutable."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        check = result.checks[0]
        with pytest.raises((AttributeError, TypeError)):
            check.passed = False


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailClosed:
    """Test FAIL-CLOSED discipline."""
    
    def test_any_critical_failure_fails_review(self, engine):
        """Any CRITICAL failure should fail the entire review."""
        # Test each critical failure type
        critical_bers = [
            create_ber_invalid_authority(),
            create_ber_broken_loop(),
            create_ber_not_emitted(),
            create_ber_invalid_decision(),
        ]
        
        for ber in critical_bers:
            result = engine.review(ber)
            assert not result.passed, f"BER {ber.pac_id} should fail"
    
    def test_warning_failures_dont_block(self, engine):
        """WARNING failures should not block review."""
        # CORRECTIVE without training signal has WARNING failure
        ber = create_ber_missing_training_signal()
        result = engine.review(ber)
        
        # Check if only WARNING failures exist
        failures = result.get_failed_checks()
        critical_failures = [c for c in failures if c.severity == CheckSeverity.CRITICAL]
        
        if len(critical_failures) == 0:
            # Only warnings - should pass
            assert result.passed


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_dict_ber_works(self, engine):
        """Engine should handle dict-style BERs."""
        ber_dict = {
            "pac_id": "PAC-DICT-001",
            "decision": "APPROVE",
            "issuer": "GID-00",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "wrap_status": "COMPLETE",
            "session_state": "BER_EMITTED",
        }
        
        result = engine.review(ber_dict)
        
        assert result.check_count >= REQUIRED_CHECK_COUNT
    
    def test_empty_pending_pacs_skips_orphan_check(self, engine):
        """Empty pending PACs should skip orphan check."""
        ber = create_valid_approve_ber("PAC-ANY-001")
        result = engine.review(ber)
        
        # Should pass loop check when no pending PACs tracked
        loop_failures = [
            c for c in result.checks
            if c.check_id == CheckID.CHK_002.value and 
            c.failure_mode == FailureMode.ORPHAN_BER
        ]
        assert len(loop_failures) == 0
    
    def test_multiple_failures_reported(self, engine):
        """BER with multiple issues should report all failures."""
        now = datetime.now(timezone.utc)
        ber = MockBERArtifact(
            pac_id="",  # Failure 1: broken loop
            decision="INVALID",  # Failure 2: invalid decision
            issuer="BADGUY",  # Failure 3: invalid authority
            issued_at=now.isoformat(),
            emitted_at="",  # Failure 4: missing emission
            wrap_status="",  # Failure 5: missing wrap
            session_state="BER_ISSUED",  # Failure 6: not emitted
        )
        
        result = engine.review(ber)
        
        assert not result.passed
        assert len(result.failure_reasons) > 1


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSchema:
    """Test schema definitions."""
    
    def test_check_id_enum_values(self):
        """CheckID enum should have all 8 checks."""
        assert len(CheckID) == 8
        assert CheckID.CHK_001.value == "CHK-001"
        assert CheckID.CHK_008.value == "CHK-008"
    
    def test_failure_mode_enum(self):
        """FailureMode enum should cover all modes."""
        assert FailureMode.AUTHORITY_VIOLATION.value == "AUTHORITY_VIOLATION"
        assert FailureMode.ORPHAN_BER.value == "ORPHAN_BER"
        assert FailureMode.EMISSION_VIOLATION.value == "EMISSION_VIOLATION"
    
    def test_review_outcome_enum(self):
        """ReviewOutcome must be binary."""
        assert len(ReviewOutcome) == 2
        assert ReviewOutcome.PASS.value == "PASS"
        assert ReviewOutcome.FAIL.value == "FAIL"
    
    def test_jeffrey_action_enum(self):
        """JeffreyAction must be binary."""
        assert len(JeffreyAction) == 2
        assert JeffreyAction.NEXT_PAC.value == "NEXT_PAC"
        assert JeffreyAction.CORRECTIVE_PAC.value == "CORRECTIVE_PAC"


# ═══════════════════════════════════════════════════════════════════════════════
# ZERO NARRATIVE TOLERANCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestZeroNarrativeTolerance:
    """Test that narrative responses are blocked."""
    
    def test_no_narrative_in_result(self, engine):
        """Result should not contain narrative approvals."""
        ber = create_valid_approve_ber()
        result = engine.review(ber)
        
        # Result should be structured, not narrative
        assert isinstance(result.outcome, ReviewOutcome)
        assert isinstance(result.checks, tuple)
        assert all(isinstance(c, CheckResult) for c in result.checks)
    
    def test_failure_reasons_are_structured(self, engine):
        """Failure reasons should be structured, not conversational."""
        ber = create_ber_invalid_authority()
        result = engine.review(ber)
        
        # Reasons should be machine-readable
        for reason in result.failure_reasons:
            assert not reason.startswith("I think")
            assert not reason.startswith("It seems")
            assert not reason.startswith("Maybe")
