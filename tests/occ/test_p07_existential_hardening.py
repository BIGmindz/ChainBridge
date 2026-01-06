"""
PAC-OCC-P07 Existential Hardening Tests

Tests for the 6 existential failure hardening modules:
- EX1: T4 Dual Control
- EX2: Constitution Sealing
- EX3: Agent Registry
- EX4: Audit Archival
- EX5: Backup Integrity
- EX6: Alert Fatigue Detection
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# EX1: T4 DUAL CONTROL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestDualControlEnforcer:
    """Tests for T4 dual control enforcement."""
    
    def test_initiate_request(self):
        """Test initiating a dual control request."""
        from core.occ.auth.dual_control import DualControlEnforcer, T4Action
        
        enforcer = DualControlEnforcer()
        
        request = enforcer.initiate_request(
            action=T4Action.KILL_SWITCH_ENGAGE,
            operator_id="operator_1",
            context={"reason": "test"},
        )
        
        assert request.action == T4Action.KILL_SWITCH_ENGAGE
        assert request.initiated_by == "operator_1"
        assert request.status.value == "pending"
        assert request.first_approver is None
    
    def test_first_approval(self):
        """Test first approval workflow."""
        from core.occ.auth.dual_control import DualControlEnforcer, T4Action, ApprovalStatus
        
        enforcer = DualControlEnforcer()
        
        request = enforcer.initiate_request(
            action=T4Action.KILL_SWITCH_ENGAGE,
            operator_id="operator_1",
        )
        
        result = enforcer.approve(request.request_id, "approver_1")
        
        assert result.success
        assert result.status == ApprovalStatus.FIRST_APPROVED
        assert not result.execution_authorized
    
    def test_dual_approval_completes(self):
        """Test dual approval completion."""
        from core.occ.auth.dual_control import DualControlEnforcer, T4Action, ApprovalStatus
        
        enforcer = DualControlEnforcer()
        
        request = enforcer.initiate_request(
            action=T4Action.KILL_SWITCH_ENGAGE,
            operator_id="operator_1",
        )
        
        # First approval
        enforcer.approve(request.request_id, "approver_1")
        
        # Second approval
        result = enforcer.approve(request.request_id, "approver_2")
        
        assert result.success
        assert result.status == ApprovalStatus.FULLY_APPROVED
        assert result.execution_authorized
        assert len(result.approvers) == 2
    
    def test_same_operator_cannot_approve_twice(self):
        """INV-DUAL-002: Same operator cannot provide both approvals."""
        from core.occ.auth.dual_control import DualControlEnforcer, T4Action
        
        enforcer = DualControlEnforcer()
        
        request = enforcer.initiate_request(
            action=T4Action.KILL_SWITCH_ENGAGE,
            operator_id="operator_1",
        )
        
        # First approval
        enforcer.approve(request.request_id, "approver_1")
        
        # Same operator tries second approval
        result = enforcer.approve(request.request_id, "approver_1")
        
        assert not result.success
        assert "INV-DUAL-002" in result.message
    
    def test_hardware_token_verification(self):
        """Test hardware token verification."""
        from core.occ.auth.dual_control import HardwareTokenSimulator
        
        simulator = HardwareTokenSimulator()
        
        code = simulator.generate_code("operator_1")
        assert len(code) == 6
        assert code.isdigit()
        
        # Verify valid code
        assert simulator.verify_code("operator_1", code)
        
        # Wrong code fails
        assert not simulator.verify_code("operator_1", "000000")


# ═══════════════════════════════════════════════════════════════════════════════
# EX2: CONSTITUTION SEALING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestConstitutionSealer:
    """Tests for constitution sealing."""
    
    def test_seal_and_verify(self):
        """Test sealing and verifying constitution."""
        from core.occ.governance.constitution_seal import ConstitutionSealer
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create mock constitution
            constitution_path = Path(tmp_dir) / "ALEX_RULES.json"
            constitution_path.write_text(json.dumps({
                "version": "1.0.0",
                "rules": ["test"]
            }))
            
            manifest_path = Path(tmp_dir) / "seal.json"
            
            sealer = ConstitutionSealer(
                constitution_path=str(constitution_path),
                manifest_path=str(manifest_path),
                repo_root=tmp_dir,
            )
            
            # Seal (without dual control for test)
            manifest = sealer.seal(
                sealed_by="test_operator",
                require_dual_control=False,
            )
            
            assert manifest.sha256_hash
            assert manifest.sealed_by == "test_operator"
            
            # Verify
            result = sealer.verify(raise_on_mismatch=False)
            assert result.valid
    
    def test_tamper_detection(self):
        """Test detection of constitution tampering."""
        from core.occ.governance.constitution_seal import ConstitutionSealer, SealViolation
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            constitution_path = Path(tmp_dir) / "ALEX_RULES.json"
            constitution_path.write_text(json.dumps({"version": "1.0.0"}))
            manifest_path = Path(tmp_dir) / "seal.json"
            
            sealer = ConstitutionSealer(
                constitution_path=str(constitution_path),
                manifest_path=str(manifest_path),
                repo_root=tmp_dir,
            )
            
            # Seal
            sealer.seal(sealed_by="test", require_dual_control=False)
            
            # Tamper with constitution
            constitution_path.write_text(json.dumps({"version": "2.0.0", "tampered": True}))
            
            # Verify should fail
            result = sealer.verify(raise_on_mismatch=False)
            assert not result.valid
            
            # Should raise on mismatch
            with pytest.raises(SealViolation):
                sealer.verify(raise_on_mismatch=True)


# ═══════════════════════════════════════════════════════════════════════════════
# EX3: AGENT REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentRegistry:
    """Tests for agent registry enforcement."""
    
    def test_default_agents_registered(self):
        """Test default agents are registered."""
        from core.occ.governance.agent_registry import AgentRegistry
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = AgentRegistry(
                registry_path=str(Path(tmp_dir) / "registry.json"),
                repo_root=tmp_dir,
            )
            
            # Default agents should be registered
            assert registry.is_registered("GID-00")  # BENSON
            assert registry.is_registered("GID-08")  # ALEX
            assert registry.is_registered("GID-06")  # SAM
    
    def test_shadow_agent_blocked(self):
        """INV-AGENT-001: Unregistered agents cannot execute."""
        from core.occ.governance.agent_registry import AgentRegistry, ShadowAgentError
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = AgentRegistry(
                registry_path=str(Path(tmp_dir) / "registry.json"),
                repo_root=tmp_dir,
            )
            
            # Unknown agent should be blocked
            with pytest.raises(ShadowAgentError):
                registry.authorize_operation(
                    gid="GID-99",
                    operation="test_operation",
                )
    
    def test_registered_agent_authorized(self):
        """Test registered agent can execute."""
        from core.occ.governance.agent_registry import AgentRegistry
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            registry = AgentRegistry(
                registry_path=str(Path(tmp_dir) / "registry.json"),
                repo_root=tmp_dir,
            )
            
            # Known agent should be authorized
            result = registry.authorize_operation(
                gid="GID-01",  # CODY
                operation="test_operation",
            )
            
            assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# EX4: AUDIT ARCHIVAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditArchiver:
    """Tests for audit archival."""
    
    def test_storage_status(self):
        """Test storage status reporting."""
        from core.occ.store.audit_archiver import AuditArchiver
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            archiver = AuditArchiver(
                audit_path=str(Path(tmp_dir) / "audit"),
                archive_path=str(Path(tmp_dir) / "archive"),
            )
            
            status = archiver.get_storage_status()
            
            assert hasattr(status, "active_size_mb")
            assert hasattr(status, "archive_count")
            assert hasattr(status, "archival_recommended")


# ═══════════════════════════════════════════════════════════════════════════════
# EX5: BACKUP INTEGRITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBackupIntegrityVerifier:
    """Tests for backup integrity verification."""
    
    def test_register_and_verify_backup(self):
        """Test backup registration and verification."""
        from core.occ.store.backup_integrity import BackupIntegrityVerifier, BackupType
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create source file
            source = Path(tmp_dir) / "source.txt"
            source.write_text("test content")
            
            verifier = BackupIntegrityVerifier(
                backup_path=str(Path(tmp_dir) / "backups"),
                manifest_path=str(Path(tmp_dir) / "manifest.json"),
            )
            
            # Register backup
            entry = verifier.register_backup(
                source_path=str(source),
                backup_type=BackupType.CONFIG,
                created_by="test",
            )
            
            assert entry.backup_id
            assert entry.sha256_hash
            
            # Verify
            result = verifier.verify_backup(entry.backup_id)
            assert result.status.value == "verified"
            assert result.hash_matches
    
    def test_corrupted_backup_detected(self):
        """INV-BACKUP-001: Corrupted backups are detected."""
        from core.occ.store.backup_integrity import (
            BackupIntegrityVerifier, BackupType, VerificationStatus
        )
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            source = Path(tmp_dir) / "source.txt"
            source.write_text("test content")
            
            verifier = BackupIntegrityVerifier(
                backup_path=str(Path(tmp_dir) / "backups"),
                manifest_path=str(Path(tmp_dir) / "manifest.json"),
            )
            
            entry = verifier.register_backup(
                source_path=str(source),
                backup_type=BackupType.CONFIG,
                created_by="test",
                compress=False,  # No compression for easy corruption
            )
            
            # Corrupt the backup
            backup_path = Path(entry.backup_path)
            backup_path.write_text("corrupted content")
            
            # Verify should detect corruption
            result = verifier.verify_backup(entry.backup_id, test_restore=False)
            assert result.status == VerificationStatus.CORRUPTED
            assert not result.hash_matches


# ═══════════════════════════════════════════════════════════════════════════════
# EX6: ALERT FATIGUE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAlertFatigueDetector:
    """Tests for alert fatigue detection."""
    
    def test_record_event(self):
        """Test recording approval events."""
        from core.occ.governance.alert_fatigue import AlertFatigueDetector
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = AlertFatigueDetector(
                metrics_path=str(Path(tmp_dir) / "metrics.json")
            )
            
            event, alerts = detector.record_event(
                operator_id="operator_1",
                action="approve",
                target_type="pdo",
                target_id="PDO-001",
                justification="Approved after thorough review of all requirements",
            )
            
            assert event.event_id
            assert event.action == "approve"
    
    def test_velocity_metrics(self):
        """Test velocity metrics computation."""
        from core.occ.governance.alert_fatigue import AlertFatigueDetector
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = AlertFatigueDetector(
                metrics_path=str(Path(tmp_dir) / "metrics.json")
            )
            
            # Record some events
            for i in range(5):
                detector.record_event(
                    operator_id="operator_1",
                    action="approve" if i % 2 == 0 else "reject",
                    target_type="pdo",
                    target_id=f"PDO-{i:03d}",
                    justification=f"Review #{i} - detailed justification here",
                )
            
            metrics = detector.compute_velocity_metrics(window_hours=1)
            
            assert metrics.total_events == 5
            assert metrics.total_approvals == 3
            assert metrics.total_rejections == 2
    
    def test_weak_justification_flagged(self):
        """INV-FATIGUE-003: Weak justifications are flagged."""
        from core.occ.governance.alert_fatigue import AlertFatigueDetector, DriftIndicator
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = AlertFatigueDetector(
                metrics_path=str(Path(tmp_dir) / "metrics.json")
            )
            
            # Record many events first to ensure checks run
            for i in range(15):
                detector.record_event(
                    operator_id="operator_1",
                    action="approve",
                    target_type="pdo",
                    target_id=f"PDO-{i:03d}",
                    justification="Sufficient justification for the approval request",
                )
            
            # Record event with short justification
            event, alerts = detector.record_event(
                operator_id="operator_1",
                action="approve",
                target_type="pdo",
                target_id="PDO-999",
                justification="ok",  # Too short
            )
            
            weak_alerts = [a for a in alerts if a.indicator == DriftIndicator.WEAK_JUSTIFICATIONS]
            assert len(weak_alerts) > 0
    
    def test_drift_report_generation(self):
        """Test cultural drift report generation."""
        from core.occ.governance.alert_fatigue import AlertFatigueDetector
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            detector = AlertFatigueDetector(
                metrics_path=str(Path(tmp_dir) / "metrics.json")
            )
            
            # Record events
            for i in range(10):
                detector.record_event(
                    operator_id="operator_1",
                    action="approve" if i < 8 else "reject",
                    target_type="pdo",
                    target_id=f"PDO-{i:03d}",
                    justification=f"Detailed review justification number {i}",
                )
            
            report = detector.generate_drift_report(analysis_days=7)
            
            assert report.report_id
            assert report.total_events == 10
            assert report.avg_daily_approvals > 0


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestP07Integration:
    """Integration tests for P07 hardening modules."""
    
    def test_all_modules_instantiate(self):
        """Test all modules can be instantiated."""
        from core.occ.auth.dual_control import DualControlEnforcer
        from core.occ.governance.constitution_seal import ConstitutionSealer
        from core.occ.governance.agent_registry import AgentRegistry
        from core.occ.store.audit_archiver import AuditArchiver
        from core.occ.store.backup_integrity import BackupIntegrityVerifier
        from core.occ.governance.alert_fatigue import AlertFatigueDetector
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create minimal constitution
            constitution = Path(tmp_dir) / "constitution.json"
            constitution.write_text(json.dumps({"version": "1.0.0"}))
            
            instances = [
                DualControlEnforcer(),
                ConstitutionSealer(
                    constitution_path=str(constitution),
                    manifest_path=str(Path(tmp_dir) / "seal.json"),
                    repo_root=tmp_dir,
                ),
                AgentRegistry(
                    registry_path=str(Path(tmp_dir) / "registry.json"),
                    repo_root=tmp_dir,
                ),
                AuditArchiver(
                    audit_path=str(Path(tmp_dir) / "audit"),
                    archive_path=str(Path(tmp_dir) / "archive"),
                ),
                BackupIntegrityVerifier(
                    backup_path=str(Path(tmp_dir) / "backups"),
                    manifest_path=str(Path(tmp_dir) / "manifest.json"),
                ),
                AlertFatigueDetector(
                    metrics_path=str(Path(tmp_dir) / "metrics.json")
                ),
            ]
            
            assert len(instances) == 6
            for instance in instances:
                assert instance is not None
