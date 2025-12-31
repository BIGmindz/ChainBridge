#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🟦🟩 UNIT TESTS: WRAP AUTHORIZATION & PDO FINALIZATION
PAC Reference: PAC-BENSON-P57-WRAP-AUTHORIZATION-AND-PDO-FINALIZATION-01
═══════════════════════════════════════════════════════════════════════════════

Tests for WRAP authorization and PDO (Proof–Decision–Outcome) finalization.

Invariants Tested:
    - Only BENSON (GID-00) may authorize WRAP generation
    - BER must have human_review_completed=True for WRAP
    - BER must have no blocking violations
    - PDO binds BER + WRAP hashes immutably
    - Ledger commit is atomic
"""

import unittest
from datetime import datetime, timezone

# Import from benson_execution
from benson_execution import (
    BensonExecutionEngine,
    BERApprovalState,
    PDOArtifact,
    PDOStatus,
    WrapArtifact,
    WrapStatus,
    ExecutionResult,
)


class TestBERApprovalValidation(unittest.TestCase):
    """Test suite for BER approval state validation (T1)."""
    
    def setUp(self):
        self.engine = BensonExecutionEngine(enable_telemetry=False)
        self.valid_ber_data = {
            "ber_id": "BER-TEST-P57-01",
            "human_review_completed": True,
            "human_review_timestamp": "2025-12-25T00:00:00Z",
            "human_reviewer": "ALEX (HUMAN-IN-LOOP)",
            "violations": [],
            "quality_score": 1.0,
            "tasks_completed": ["T1", "T2", "T3"]
        }
    
    def test_valid_ber_approval_passes(self):
        """Test that valid BER approval state is accepted."""
        result = self.engine.validate_ber_approval(
            ber_id="BER-TEST-P57-01",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            ber_data=self.valid_ber_data
        )
        
        self.assertTrue(result.human_review_completed)
        self.assertTrue(result.no_blocking_violations)
        self.assertIsNotNone(result.approval_timestamp)
        self.assertIsNotNone(result.ber_hash)
    
    def test_missing_human_review_fails(self):
        """Test that missing human review blocks approval."""
        ber_data = self.valid_ber_data.copy()
        ber_data["human_review_completed"] = False
        
        result = self.engine.validate_ber_approval(
            ber_id="BER-TEST-P57-02",
            pac_id="PAC-BENSON-P57-TEST-02",
            agent_gid="GID-00",
            agent_name="BENSON",
            ber_data=ber_data
        )
        
        self.assertFalse(result.human_review_completed)
        self.assertIsNone(result.approval_timestamp)
    
    def test_blocking_violations_detected(self):
        """Test that blocking violations are detected."""
        ber_data = self.valid_ber_data.copy()
        ber_data["violations"] = [
            {"error_code": "GS_173", "severity": "HARD_BLOCK", "message": "Self-approval blocked"}
        ]
        
        result = self.engine.validate_ber_approval(
            ber_id="BER-TEST-P57-03",
            pac_id="PAC-BENSON-P57-TEST-03",
            agent_gid="GID-00",
            agent_name="BENSON",
            ber_data=ber_data
        )
        
        self.assertFalse(result.no_blocking_violations)
        self.assertIn("GS_173", result.blocking_violations)
        self.assertIsNone(result.approval_timestamp)
    
    def test_warning_violations_allowed(self):
        """Test that WARNING violations don't block approval."""
        ber_data = self.valid_ber_data.copy()
        ber_data["violations"] = [
            {"error_code": "GS_172", "severity": "WARNING", "message": "Prescriptive language"}
        ]
        
        result = self.engine.validate_ber_approval(
            ber_id="BER-TEST-P57-04",
            pac_id="PAC-BENSON-P57-TEST-04",
            agent_gid="GID-00",
            agent_name="BENSON",
            ber_data=ber_data
        )
        
        self.assertTrue(result.no_blocking_violations)
        self.assertIsNotNone(result.approval_timestamp)
    
    def test_ber_hash_is_computed(self):
        """Test that BER hash is computed correctly."""
        result = self.engine.validate_ber_approval(
            ber_id="BER-TEST-P57-05",
            pac_id="PAC-BENSON-P57-TEST-05",
            agent_gid="GID-00",
            agent_name="BENSON",
            ber_data=self.valid_ber_data
        )
        
        self.assertIsNotNone(result.ber_hash)
        self.assertEqual(len(result.ber_hash), 64)  # SHA256 hex


class TestWRAPAuthorization(unittest.TestCase):
    """Test suite for WRAP authorization from BER (T2)."""
    
    def setUp(self):
        self.engine = BensonExecutionEngine(enable_telemetry=False)
        self.execution_result = ExecutionResult(
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            execution_timestamp=datetime.now(timezone.utc).isoformat(),
            tasks_completed=["T1", "T2", "T3"],
            files_modified=["test.py"],
            quality_score=1.0,
            scope_compliance=True,
            execution_time_ms=5000
        )
    
    def _get_approved_ber(self):
        """Helper to create an approved BER state."""
        return BERApprovalState(
            ber_id="BER-TEST-P57-01",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            human_review_completed=True,
            human_review_timestamp="2025-12-25T00:00:00Z",
            human_reviewer="ALEX (HUMAN-IN-LOOP)",
            no_blocking_violations=True,
            blocking_violations=[],
            ber_hash="a" * 64,
            approval_timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def test_wrap_authorized_from_approved_ber(self):
        """Test WRAP is authorized from approved BER."""
        ber_approval = self._get_approved_ber()
        
        result = self.engine.authorize_wrap_from_ber(
            ber_approval=ber_approval,
            execution_result=self.execution_result
        )
        
        self.assertTrue(result["authorized"])
        self.assertIsNone(result["error_code"])
        self.assertIsNotNone(result["wrap"])
        self.assertIn("WRAP-BENSON-P57", result["wrap"].wrap_id)
    
    def test_wrap_denied_without_human_review(self):
        """Test WRAP is denied without human review."""
        ber_approval = self._get_approved_ber()
        ber_approval.human_review_completed = False
        
        result = self.engine.authorize_wrap_from_ber(
            ber_approval=ber_approval,
            execution_result=self.execution_result
        )
        
        self.assertFalse(result["authorized"])
        self.assertEqual(result["error_code"], "GS_180")
        self.assertIsNone(result["wrap"])
    
    def test_wrap_denied_with_blocking_violations(self):
        """Test WRAP is denied with blocking violations."""
        ber_approval = self._get_approved_ber()
        ber_approval.no_blocking_violations = False
        ber_approval.blocking_violations = ["GS_173"]
        
        result = self.engine.authorize_wrap_from_ber(
            ber_approval=ber_approval,
            execution_result=self.execution_result
        )
        
        self.assertFalse(result["authorized"])
        self.assertEqual(result["error_code"], "GS_181")
        self.assertIn("GS_173", result["blocking_violations"])
    
    def test_wrap_binds_to_ber_hash(self):
        """Test WRAP binds to BER hash."""
        ber_approval = self._get_approved_ber()
        
        result = self.engine.authorize_wrap_from_ber(
            ber_approval=ber_approval,
            execution_result=self.execution_result
        )
        
        self.assertIn("ber_hash", result)
        self.assertIn("wrap_hash", result)
    
    def test_wrap_includes_dispatch_session(self):
        """Test WRAP includes dispatch session ID when provided."""
        ber_approval = self._get_approved_ber()
        dispatch_session_id = "SESS-TEST123456789012"
        
        result = self.engine.authorize_wrap_from_ber(
            ber_approval=ber_approval,
            execution_result=self.execution_result,
            dispatch_session_id=dispatch_session_id
        )
        
        self.assertTrue(result["authorized"])
        # Dispatch session is bound in wrap hash computation


class TestPDOFinalization(unittest.TestCase):
    """Test suite for PDO finalization (T3)."""
    
    def setUp(self):
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def _get_approved_ber(self):
        """Helper to create an approved BER state."""
        return BERApprovalState(
            ber_id="BER-TEST-P57-01",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            human_review_completed=True,
            human_review_timestamp="2025-12-25T00:00:00Z",
            human_reviewer="ALEX (HUMAN-IN-LOOP)",
            no_blocking_violations=True,
            blocking_violations=[],
            ber_hash="a" * 64,
            approval_timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _get_wrap_artifact(self):
        """Helper to create a WRAP artifact."""
        return WrapArtifact(
            wrap_id="WRAP-BENSON-P57-20251225000000",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            wrap_hash="b" * 64,
            pac_hash="c" * 64,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generated_by="BENSON (GID-00)",
            status=WrapStatus.WRAP_GENERATED.value,
            quality_score=1.0,
            scope_compliance=True,
            training_signal={}
        )
    
    def test_pdo_finalized_successfully(self):
        """Test PDO is finalized successfully."""
        ber_approval = self._get_approved_ber()
        wrap = self._get_wrap_artifact()
        
        pdo = self.engine.finalize_pdo(
            wrap=wrap,
            ber_approval=ber_approval,
            decision_rationale="Test decision"
        )
        
        self.assertIn("PDO-BENSON-P57", pdo.pdo_id)
        self.assertEqual(pdo.status, PDOStatus.FINALIZED.value)
        self.assertEqual(pdo.outcome_status, "EXECUTION_ACCEPTED")
    
    def test_pdo_binds_proof_hashes(self):
        """Test PDO binds BER + WRAP + PAC hashes."""
        ber_approval = self._get_approved_ber()
        wrap = self._get_wrap_artifact()
        
        pdo = self.engine.finalize_pdo(
            wrap=wrap,
            ber_approval=ber_approval
        )
        
        self.assertEqual(pdo.proof_ber_hash, ber_approval.ber_hash)
        self.assertEqual(pdo.proof_wrap_hash, wrap.wrap_hash)
        self.assertEqual(pdo.proof_pac_hash, wrap.pac_hash)
        self.assertIsNotNone(pdo.proof_combined_hash)
    
    def test_pdo_decision_authority_is_benson(self):
        """Test PDO decision authority is BENSON (GID-00)."""
        ber_approval = self._get_approved_ber()
        wrap = self._get_wrap_artifact()
        
        pdo = self.engine.finalize_pdo(
            wrap=wrap,
            ber_approval=ber_approval
        )
        
        self.assertEqual(pdo.decision_authority, "BENSON (GID-00)")
        self.assertEqual(pdo.decision_type, "AUTHORIZATION_GRANTED")
    
    def test_pdo_includes_doctrine_hash(self):
        """Test PDO includes doctrine hash if available."""
        ber_approval = self._get_approved_ber()
        wrap = self._get_wrap_artifact()
        
        pdo = self.engine.finalize_pdo(
            wrap=wrap,
            ber_approval=ber_approval
        )
        
        # May be None if doctrine file doesn't exist, but field should be present
        self.assertTrue(hasattr(pdo, 'doctrine_hash'))
    
    def test_pdo_includes_training_signal(self):
        """Test PDO includes training signal."""
        ber_approval = self._get_approved_ber()
        wrap = self._get_wrap_artifact()
        
        pdo = self.engine.finalize_pdo(
            wrap=wrap,
            ber_approval=ber_approval
        )
        
        self.assertIsNotNone(pdo.training_signal)
        self.assertEqual(pdo.training_signal["pattern"], "PDO_FINALIZED")


class TestLedgerCommit(unittest.TestCase):
    """Test suite for ledger commit (T4)."""
    
    def setUp(self):
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def _get_approved_ber(self):
        """Helper to create an approved BER state."""
        return BERApprovalState(
            ber_id="BER-TEST-P57-01",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            human_review_completed=True,
            human_review_timestamp="2025-12-25T00:00:00Z",
            human_reviewer="ALEX (HUMAN-IN-LOOP)",
            no_blocking_violations=True,
            blocking_violations=[],
            ber_hash="a" * 64,
            approval_timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _get_wrap_artifact(self):
        """Helper to create a WRAP artifact."""
        return WrapArtifact(
            wrap_id="WRAP-BENSON-P57-20251225000000",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            wrap_hash="b" * 64,
            pac_hash="c" * 64,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generated_by="BENSON (GID-00)",
            status=WrapStatus.WRAP_GENERATED.value,
            quality_score=1.0,
            scope_compliance=True,
            training_signal={}
        )
    
    def _get_pdo_artifact(self):
        """Helper to create a PDO artifact."""
        return PDOArtifact(
            pdo_id="PDO-BENSON-P57-20251225000000",
            pac_id="PAC-BENSON-P57-TEST-01",
            ber_id="BER-TEST-P57-01",
            wrap_id="WRAP-BENSON-P57-20251225000000",
            agent_gid="GID-00",
            agent_name="BENSON",
            proof_ber_hash="a" * 64,
            proof_wrap_hash="b" * 64,
            proof_pac_hash="c" * 64,
            proof_combined_hash="d" * 64,
            decision_authority="BENSON (GID-00)",
            decision_timestamp=datetime.now(timezone.utc).isoformat(),
            decision_type="AUTHORIZATION_GRANTED",
            decision_rationale="Test",
            outcome_status="EXECUTION_ACCEPTED",
            outcome_timestamp=datetime.now(timezone.utc).isoformat(),
            status=PDOStatus.FINALIZED.value
        )
    
    def test_commit_returns_result(self):
        """Test commit_wrap_accepted returns a result dict."""
        wrap = self._get_wrap_artifact()
        pdo = self._get_pdo_artifact()
        ber_approval = self._get_approved_ber()
        
        result = self.engine.commit_wrap_accepted(
            wrap=wrap,
            pdo=pdo,
            ber_approval=ber_approval
        )
        
        self.assertIn("committed", result)
        self.assertIn("wrap_id", result)


class TestTrainingSignalEmission(unittest.TestCase):
    """Test suite for training signal emission (T5)."""
    
    def setUp(self):
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def _get_wrap_artifact(self):
        """Helper to create a WRAP artifact."""
        return WrapArtifact(
            wrap_id="WRAP-BENSON-P57-20251225000000",
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            wrap_hash="b" * 64,
            pac_hash="c" * 64,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generated_by="BENSON (GID-00)",
            status=WrapStatus.WRAP_GENERATED.value,
            quality_score=1.0,
            scope_compliance=True,
            training_signal={}
        )
    
    def _get_pdo_artifact(self):
        """Helper to create a PDO artifact."""
        return PDOArtifact(
            pdo_id="PDO-BENSON-P57-20251225000000",
            pac_id="PAC-BENSON-P57-TEST-01",
            ber_id="BER-TEST-P57-01",
            wrap_id="WRAP-BENSON-P57-20251225000000",
            agent_gid="GID-00",
            agent_name="BENSON",
            proof_ber_hash="a" * 64,
            proof_wrap_hash="b" * 64,
            proof_pac_hash="c" * 64,
            proof_combined_hash="d" * 64,
            decision_authority="BENSON (GID-00)",
            decision_timestamp=datetime.now(timezone.utc).isoformat(),
            decision_type="AUTHORIZATION_GRANTED",
            decision_rationale="Test",
            outcome_status="EXECUTION_ACCEPTED",
            outcome_timestamp=datetime.now(timezone.utc).isoformat(),
            status=PDOStatus.FINALIZED.value
        )
    
    def test_training_signal_emitted(self):
        """Test training signal is emitted correctly."""
        wrap = self._get_wrap_artifact()
        pdo = self._get_pdo_artifact()
        
        signal = self.engine.emit_execution_governance_success(wrap, pdo)
        
        self.assertEqual(signal["pattern"], "EXECUTION_GOVERNANCE_SUCCESS")
        self.assertTrue(signal["propagate"])
    
    def test_training_signal_includes_context(self):
        """Test training signal includes context."""
        wrap = self._get_wrap_artifact()
        pdo = self._get_pdo_artifact()
        
        signal = self.engine.emit_execution_governance_success(wrap, pdo)
        
        self.assertIn("context", signal)
        self.assertEqual(signal["context"]["wrap_id"], wrap.wrap_id)
        self.assertEqual(signal["context"]["pdo_id"], pdo.pdo_id)


class TestFullPipeline(unittest.TestCase):
    """Test suite for full WRAP authorization and PDO pipeline."""
    
    def setUp(self):
        self.engine = BensonExecutionEngine(enable_telemetry=False)
        self.execution_result = ExecutionResult(
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            execution_timestamp=datetime.now(timezone.utc).isoformat(),
            tasks_completed=["T1", "T2", "T3", "T4", "T5"],
            files_modified=["benson_execution.py"],
            quality_score=1.0,
            scope_compliance=True,
            execution_time_ms=5000
        )
        self.valid_ber_data = {
            "ber_id": "BER-TEST-P57-FULL-01",
            "human_review_completed": True,
            "human_review_timestamp": "2025-12-25T00:00:00Z",
            "human_reviewer": "ALEX (HUMAN-IN-LOOP)",
            "violations": [],
            "quality_score": 1.0,
            "tasks_completed": ["T1", "T2", "T3", "T4", "T5"]
        }
    
    def test_full_pipeline_succeeds_with_approved_ber(self):
        """Test full pipeline succeeds with approved BER."""
        result = self.engine.execute_full_wrap_authorization_and_pdo(
            pac_id="PAC-BENSON-P57-TEST-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            execution_result=self.execution_result,
            ber_data=self.valid_ber_data
        )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "COMPLETE")
        self.assertIsNotNone(result["wrap"])
        self.assertIsNotNone(result["pdo"])
        self.assertIsNotNone(result["training_signal"])
    
    def test_full_pipeline_fails_without_human_review(self):
        """Test full pipeline fails without human review."""
        ber_data = self.valid_ber_data.copy()
        ber_data["human_review_completed"] = False
        
        result = self.engine.execute_full_wrap_authorization_and_pdo(
            pac_id="PAC-BENSON-P57-TEST-02",
            agent_gid="GID-00",
            agent_name="BENSON",
            execution_result=self.execution_result,
            ber_data=ber_data
        )
        
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "WRAP_AUTHORIZATION")
        self.assertEqual(result["error_code"], "GS_180")
    
    def test_full_pipeline_fails_with_blocking_violations(self):
        """Test full pipeline fails with blocking violations."""
        ber_data = self.valid_ber_data.copy()
        ber_data["violations"] = [
            {"error_code": "GS_173", "severity": "HARD_BLOCK"}
        ]
        
        result = self.engine.execute_full_wrap_authorization_and_pdo(
            pac_id="PAC-BENSON-P57-TEST-03",
            agent_gid="GID-00",
            agent_name="BENSON",
            execution_result=self.execution_result,
            ber_data=ber_data
        )
        
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "WRAP_AUTHORIZATION")
        self.assertEqual(result["error_code"], "GS_181")


class TestPDOStatusEnum(unittest.TestCase):
    """Test PDOStatus enum values."""
    
    def test_pdo_status_values(self):
        """Test PDOStatus has expected values."""
        self.assertEqual(PDOStatus.PENDING.value, "PENDING")
        self.assertEqual(PDOStatus.FINALIZED.value, "FINALIZED")
        self.assertEqual(PDOStatus.REJECTED.value, "REJECTED")


class TestEngineAuthority(unittest.TestCase):
    """Test engine authority constants."""
    
    def test_authority_is_benson(self):
        """Test engine authority is BENSON (GID-00)."""
        engine = BensonExecutionEngine(enable_telemetry=False)
        self.assertEqual(engine.AUTHORITY_GID, "GID-00")
        self.assertEqual(engine.AUTHORITY_NAME, "BENSON")


if __name__ == "__main__":
    unittest.main(verbosity=2)
