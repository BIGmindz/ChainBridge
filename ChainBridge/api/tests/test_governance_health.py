"""
Tests for Governance Health API — PAC-CODY-P01-GOVERNANCE-HEALTH-BACKEND-AGGREGATION-01

Unit tests for governance health service and routes.
Validates read-only operations, fail-closed behavior, and response schemas.

Authority: CODY (GID-01)
Dispatch: PAC-BENSON-EXEC-P61
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.schemas.governance_health import (
    ArtifactStatus,
    SettlementStage,
    ChainStatus,
    LedgerIntegrity,
    ComplianceFramework,
    GovernanceArtifact,
    GovernanceHealthMetrics,
    SettlementChain,
    EnterpriseComplianceSummary,
    GovernanceHealthResponse,
    SettlementChainsResponse,
    ComplianceSummaryResponse,
)
from api.services.governance_health import (
    GovernanceHealthService,
    get_governance_health_service,
    ENTERPRISE_MAPPINGS,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_ledger_data() -> Dict[str, Any]:
    """Sample ledger data for testing."""
    return {
        "ledger_metadata": {
            "version": "1.1.0",
            "created_at": "2025-12-01T00:00:00Z",
            "integrity_mode": "FAIL_CLOSED",
        },
        "sequence_state": {
            "next_sequence": 11,
            "total_entries": 10,
            "last_entry_timestamp": "2025-12-20T15:00:00Z",
        },
        "entries": [
            {
                "sequence": 1,
                "timestamp": "2025-12-15T10:00:00Z",
                "entry_type": "PAC_ISSUED",
                "artifact_id": "PAC-CODY-P01",
                "agent_gid": "GID-01",
                "agent_name": "CODY",
            },
            {
                "sequence": 2,
                "timestamp": "2025-12-15T10:30:00Z",
                "entry_type": "PAC_EXECUTED",
                "artifact_id": "PAC-CODY-P01",
                "agent_gid": "GID-01",
                "agent_name": "CODY",
            },
            {
                "sequence": 3,
                "timestamp": "2025-12-15T11:00:00Z",
                "entry_type": "WRAP_SUBMITTED",
                "artifact_id": "WRAP-CODY-P01-20251215",
                "agent_gid": "GID-01",
                "agent_name": "CODY",
                "metadata": {"pac_id": "PAC-CODY-P01"},
            },
            {
                "sequence": 4,
                "timestamp": "2025-12-15T12:00:00Z",
                "entry_type": "WRAP_ACCEPTED",
                "artifact_id": "WRAP-CODY-P01-20251215",
                "agent_gid": "GID-01",
                "agent_name": "CODY",
                "metadata": {"pac_id": "PAC-CODY-P01"},
            },
            {
                "sequence": 5,
                "timestamp": "2025-12-16T10:00:00Z",
                "entry_type": "PAC_ISSUED",
                "artifact_id": "PAC-SONNY-P01",
                "agent_gid": "GID-02",
                "agent_name": "SONNY",
            },
            {
                "sequence": 6,
                "timestamp": "2025-12-16T11:00:00Z",
                "entry_type": "PAC_EXECUTED",
                "artifact_id": "PAC-SONNY-P01",
                "agent_gid": "GID-02",
                "agent_name": "SONNY",
            },
            {
                "sequence": 7,
                "timestamp": "2025-12-16T12:00:00Z",
                "entry_type": "WRAP_SUBMITTED",
                "artifact_id": "WRAP-SONNY-P01-20251216",
                "agent_gid": "GID-02",
                "agent_name": "SONNY",
                "metadata": {"pac_id": "PAC-SONNY-P01"},
            },
            {
                "sequence": 8,
                "timestamp": "2025-12-17T10:00:00Z",
                "entry_type": "PAC_ISSUED",
                "artifact_id": "PAC-CODY-P02",
                "agent_gid": "GID-01",
                "agent_name": "CODY",
            },
            {
                "sequence": 9,
                "timestamp": "2025-12-18T10:00:00Z",
                "entry_type": "PAC_ISSUED",
                "artifact_id": "PAC-BENSON-P42",
                "agent_gid": "GID-00",
                "agent_name": "BENSON",
            },
            {
                "sequence": 10,
                "timestamp": "2025-12-18T11:00:00Z",
                "entry_type": "CORRECTION_OPENED",
                "artifact_id": "PAC-BENSON-P42",
                "agent_gid": "GID-00",
                "agent_name": "BENSON",
            },
        ],
    }


@pytest.fixture
def temp_ledger_file(tmp_path: Path, mock_ledger_data: Dict[str, Any]) -> Path:
    """Create a temporary ledger file for testing."""
    ledger_path = tmp_path / "GOVERNANCE_LEDGER.json"
    with open(ledger_path, "w") as f:
        json.dump(mock_ledger_data, f)
    return ledger_path


@pytest.fixture
def service_with_mock_ledger(temp_ledger_file: Path) -> GovernanceHealthService:
    """Create service with temporary ledger."""
    return GovernanceHealthService(ledger_path=temp_ledger_file)


# =============================================================================
# SERVICE TESTS
# =============================================================================

class TestGovernanceHealthService:
    """Tests for GovernanceHealthService."""
    
    def test_get_health_metrics(self, service_with_mock_ledger: GovernanceHealthService):
        """Test health metrics aggregation."""
        metrics = service_with_mock_ledger.get_health_metrics()
        
        # PAC counts
        assert metrics.total_pacs == 4  # 4 PAC_ISSUED entries
        assert metrics.positive_closures == 0  # No POSITIVE_CLOSURE_ACKNOWLEDGED
        assert metrics.blocked_pacs == 1  # 1 CORRECTION_OPENED
        
        # WRAP counts
        assert metrics.total_wraps == 2  # 2 WRAP_SUBMITTED
        assert metrics.accepted_wraps == 1  # 1 WRAP_ACCEPTED
        
        # Integrity
        assert metrics.ledger_integrity == LedgerIntegrity.HEALTHY
        assert metrics.sequence_gaps == 0
    
    def test_get_settlement_chains(self, service_with_mock_ledger: GovernanceHealthService):
        """Test settlement chain aggregation."""
        chains = service_with_mock_ledger.get_settlement_chains(limit=10)
        
        assert len(chains) >= 1
        
        # Find the completed chain (PAC-CODY-P01)
        cody_chain = next((c for c in chains if c.pac_id == "PAC-CODY-P01"), None)
        assert cody_chain is not None
        assert cody_chain.status == ChainStatus.COMPLETED
        assert cody_chain.current_stage == SettlementStage.LEDGER_COMMIT
        assert cody_chain.wrap_id == "WRAP-CODY-P01-20251215"
    
    def test_get_compliance_summary(self, service_with_mock_ledger: GovernanceHealthService):
        """Test compliance summary."""
        summary = service_with_mock_ledger.get_compliance_summary()
        
        assert len(summary.mappings) == len(ENTERPRISE_MAPPINGS)
        assert summary.compliance_score == 100.0
        assert summary.framework_coverage.sox == 100.0
        assert summary.framework_coverage.soc2 == 100.0
        assert summary.framework_coverage.nist == 100.0
        assert summary.framework_coverage.iso27001 == 100.0
        
        # Verify framework distribution
        frameworks = {m.framework for m in summary.mappings}
        assert ComplianceFramework.SOX in frameworks
        assert ComplianceFramework.SOC2 in frameworks
        assert ComplianceFramework.NIST_CSF in frameworks
        assert ComplianceFramework.ISO_27001 in frameworks
    
    def test_verify_ledger_integrity_healthy(self, service_with_mock_ledger: GovernanceHealthService):
        """Test integrity verification with healthy ledger."""
        ledger = service_with_mock_ledger._load_ledger()
        integrity, gaps = service_with_mock_ledger._verify_ledger_integrity(ledger)
        
        assert integrity == LedgerIntegrity.HEALTHY
        assert gaps == 0
    
    def test_verify_ledger_integrity_with_gaps(self, tmp_path: Path):
        """Test integrity verification with sequence gaps."""
        ledger_with_gaps = {
            "ledger_metadata": {"version": "1.1.0"},
            "sequence_state": {"next_sequence": 5},
            "entries": [
                {"sequence": 1, "entry_type": "PAC_ISSUED"},
                {"sequence": 2, "entry_type": "PAC_EXECUTED"},
                {"sequence": 5, "entry_type": "WRAP_SUBMITTED"},  # Gap: 3, 4 missing
            ],
        }
        
        ledger_path = tmp_path / "gap_ledger.json"
        with open(ledger_path, "w") as f:
            json.dump(ledger_with_gaps, f)
        
        service = GovernanceHealthService(ledger_path=ledger_path)
        ledger = service._load_ledger()
        integrity, gaps = service._verify_ledger_integrity(ledger)
        
        assert integrity == LedgerIntegrity.DEGRADED
        assert gaps == 1  # One gap (from 2 to 5)
    
    def test_missing_ledger_returns_empty(self, tmp_path: Path):
        """Test handling of missing ledger file."""
        nonexistent = tmp_path / "nonexistent" / "GOVERNANCE_LEDGER.json"
        service = GovernanceHealthService(ledger_path=nonexistent)
        
        metrics = service.get_health_metrics()
        
        # Should return zeroed metrics, not raise
        assert metrics.total_pacs == 0
        assert metrics.ledger_integrity == LedgerIntegrity.HEALTHY
    
    def test_caching(self, service_with_mock_ledger: GovernanceHealthService):
        """Test ledger caching behavior."""
        # First load
        ledger1 = service_with_mock_ledger._load_ledger()
        
        # Second load should return cached
        ledger2 = service_with_mock_ledger._load_ledger()
        
        assert ledger1 is ledger2  # Same object (cached)
        
        # Force refresh should reload
        ledger3 = service_with_mock_ledger._load_ledger(force_refresh=True)
        
        # Content should be same but different object
        assert ledger3 is not ledger1


class TestFlowNodes:
    """Tests for settlement flow node building."""
    
    def test_build_flow_nodes_completed(self, service_with_mock_ledger: GovernanceHealthService):
        """Test flow nodes for completed chain."""
        entries = [
            {"entry_type": "PAC_ISSUED"},
            {"entry_type": "PAC_EXECUTED"},
            {"entry_type": "WRAP_SUBMITTED"},
            {"entry_type": "WRAP_ACCEPTED"},
        ]
        
        nodes = service_with_mock_ledger._build_flow_nodes(entries, ChainStatus.COMPLETED)
        
        # All stages should be finalized for completed chain
        assert all(n.status == ArtifactStatus.FINALIZED for n in nodes)
    
    def test_build_flow_nodes_in_progress(self, service_with_mock_ledger: GovernanceHealthService):
        """Test flow nodes for in-progress chain."""
        entries = [
            {"entry_type": "PAC_ISSUED"},
            {"entry_type": "PAC_EXECUTED"},
        ]
        
        nodes = service_with_mock_ledger._build_flow_nodes(entries, ChainStatus.IN_PROGRESS)
        
        # PAC stages finalized, later stages pending
        pac_dispatch = next(n for n in nodes if n.stage == SettlementStage.PAC_DISPATCH)
        agent_exec = next(n for n in nodes if n.stage == SettlementStage.AGENT_EXECUTION)
        ber_gen = next(n for n in nodes if n.stage == SettlementStage.BER_GENERATION)
        
        assert pac_dispatch.status == ArtifactStatus.FINALIZED
        assert agent_exec.status == ArtifactStatus.FINALIZED
        assert ber_gen.status == ArtifactStatus.PENDING


# =============================================================================
# SCHEMA TESTS
# =============================================================================

class TestSchemas:
    """Tests for Pydantic schemas."""
    
    def test_governance_health_metrics_serialization(self):
        """Test GovernanceHealthMetrics JSON serialization."""
        metrics = GovernanceHealthMetrics(
            total_pacs=10,
            active_pacs=2,
            blocked_pacs=1,
            positive_closures=7,
            total_bers=7,
            pending_bers=0,
            approved_bers=7,
            total_pdos=7,
            finalized_pdos=7,
            total_wraps=7,
            accepted_wraps=7,
            settlement_rate=70.0,
            avg_settlement_time_ms=180000,
            pending_settlements=2,
            ledger_integrity=LedgerIntegrity.HEALTHY,
            last_ledger_sync=datetime.now(timezone.utc),
            sequence_gaps=0,
        )
        
        data = metrics.model_dump(mode="json")
        
        assert data["total_pacs"] == 10
        assert data["ledger_integrity"] == "HEALTHY"
    
    def test_settlement_flow_node_serialization(self):
        """Test SettlementFlowNode serialization."""
        from api.schemas.governance_health import SettlementFlowNode
        
        node = SettlementFlowNode(
            stage=SettlementStage.PAC_DISPATCH,
            status=ArtifactStatus.FINALIZED,
            authority="BENSON (GID-00)",
        )
        
        data = node.model_dump(mode="json")
        
        assert data["stage"] == "PAC_DISPATCH"
        assert data["status"] == "FINALIZED"
        assert data["authority"] == "BENSON (GID-00)"
    
    def test_enterprise_mapping_serialization(self):
        """Test EnterpriseMapping serialization."""
        from api.schemas.governance_health import EnterpriseMapping
        
        mapping = EnterpriseMapping(
            framework=ComplianceFramework.SOX,
            control="§302",
            description="Scope Definition",
            artifact=GovernanceArtifact.PAC,
        )
        
        data = mapping.model_dump(mode="json")
        
        assert data["framework"] == "SOX"
        assert data["artifact"] == "PAC"


# =============================================================================
# API ROUTE TESTS
# =============================================================================

class TestRoutes:
    """Tests for API routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from api.server import app
        return TestClient(app)
    
    def test_health_endpoint(self, client: TestClient):
        """Test GET /api/governance/health endpoint."""
        with patch(
            "api.routes.governance_health.get_governance_health_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_health_metrics.return_value = GovernanceHealthMetrics(
                total_pacs=5,
                active_pacs=1,
                blocked_pacs=0,
                positive_closures=4,
                total_bers=4,
                pending_bers=0,
                approved_bers=4,
                total_pdos=4,
                finalized_pdos=4,
                total_wraps=4,
                accepted_wraps=4,
                settlement_rate=80.0,
                avg_settlement_time_ms=180000,
                pending_settlements=1,
                ledger_integrity=LedgerIntegrity.HEALTHY,
                last_ledger_sync=datetime.now(timezone.utc),
                sequence_gaps=0,
            )
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/governance/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["metrics"]["total_pacs"] == 5
            assert data["metrics"]["ledger_integrity"] == "HEALTHY"
    
    def test_settlement_chains_endpoint(self, client: TestClient):
        """Test GET /api/governance/settlement-chains endpoint."""
        with patch(
            "api.routes.governance_health.get_governance_health_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_settlement_chains.return_value = [
                SettlementChain(
                    chain_id="chain-test123",
                    pac_id="PAC-TEST-P01",
                    current_stage=SettlementStage.LEDGER_COMMIT,
                    status=ChainStatus.COMPLETED,
                    started_at=datetime.now(timezone.utc),
                    nodes=[],
                    agent_gid="GID-01",
                    agent_name="TEST",
                )
            ]
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/governance/settlement-chains")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["chains"]) == 1
            assert data["chains"][0]["pac_id"] == "PAC-TEST-P01"
    
    def test_compliance_summary_endpoint(self, client: TestClient):
        """Test GET /api/governance/compliance-summary endpoint."""
        with patch(
            "api.routes.governance_health.get_governance_health_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_compliance_summary.return_value = EnterpriseComplianceSummary(
                mappings=[],
                last_audit_date="2025-12-20",
                compliance_score=100.0,
                framework_coverage=MagicMock(
                    sox=100.0, soc2=100.0, nist=100.0, iso27001=100.0
                ),
            )
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/governance/compliance-summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["summary"]["compliance_score"] == 100.0
    
    def test_settlement_chains_limit_parameter(self, client: TestClient):
        """Test limit parameter validation."""
        with patch(
            "api.routes.governance_health.get_governance_health_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_settlement_chains.return_value = []
            mock_get_service.return_value = mock_service
            
            # Valid limit
            response = client.get("/api/governance/settlement-chains?limit=5")
            assert response.status_code == 200
            
            # Invalid limit (too high)
            response = client.get("/api/governance/settlement-chains?limit=200")
            assert response.status_code == 422  # Validation error
            
            # Invalid limit (too low)
            response = client.get("/api/governance/settlement-chains?limit=0")
            assert response.status_code == 422


# =============================================================================
# FAIL-CLOSED TESTS
# =============================================================================

class TestFailClosed:
    """Tests for fail-closed behavior."""
    
    def test_service_fails_closed_on_malformed_ledger(self, tmp_path: Path):
        """Test that malformed ledger causes fail-closed."""
        malformed_path = tmp_path / "malformed.json"
        with open(malformed_path, "w") as f:
            f.write("not valid json {{{")
        
        service = GovernanceHealthService(ledger_path=malformed_path)
        
        with pytest.raises(json.JSONDecodeError):
            service._load_ledger(force_refresh=True)


# =============================================================================
# SINGLETON TESTS
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_governance_health_service_returns_singleton(self):
        """Test that get_governance_health_service returns same instance."""
        # Clear the singleton first
        import api.services.governance_health as module
        module._service_instance = None
        
        service1 = get_governance_health_service()
        service2 = get_governance_health_service()
        
        assert service1 is service2
