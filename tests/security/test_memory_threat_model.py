# ═══════════════════════════════════════════════════════════════════════════════
# Memory Threat Model Tests
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Memory Threat Model Tests — Tests for TMV-MEM-* and TMM-MEM-*.
"""

import pytest

from core.security.memory_threat_model import (
    AttackVector,
    MemoryMitigation,
    MemoryThreatModelRegistry,
    MemoryThreatVector,
    MitigationStatus,
    ThreatCategory,
    ThreatSeverity,
    TMV_MEM_001,
    TMV_MEM_002,
    TMV_MEM_006,
    TMV_MEM_010,
    TMM_MEM_001,
    TMM_MEM_002,
    TMM_MEM_006,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY THREAT VECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryThreatVector:
    """Tests for MemoryThreatVector."""

    def test_valid_threat_creation(self) -> None:
        """Test creating a valid threat vector."""
        threat = MemoryThreatVector(
            threat_id="TMV-MEM-TEST",
            name="Test Threat",
            description="A test threat",
            category=ThreatCategory.MEMORY_POISONING,
            severity=ThreatSeverity.HIGH,
            attack_vectors=[AttackVector.EXTERNAL],
            preconditions=["Test precondition"],
            impact="Test impact",
            likelihood="MEDIUM",
            affected_components=["TestComponent"],
        )
        assert threat.threat_id == "TMV-MEM-TEST"

    def test_invalid_id_raises(self) -> None:
        """Test that invalid ID format raises error."""
        with pytest.raises(ValueError):
            MemoryThreatVector(
                threat_id="INVALID-001",
                name="Test",
                description="Test",
                category=ThreatCategory.MEMORY_POISONING,
                severity=ThreatSeverity.HIGH,
                attack_vectors=[AttackVector.EXTERNAL],
                preconditions=[],
                impact="Test",
                likelihood="HIGH",
                affected_components=[],
            )

    def test_compute_risk_score(self) -> None:
        """Test risk score computation."""
        threat_critical_high = MemoryThreatVector(
            threat_id="TMV-MEM-TEST1",
            name="Test",
            description="Test",
            category=ThreatCategory.MEMORY_POISONING,
            severity=ThreatSeverity.CRITICAL,
            attack_vectors=[AttackVector.EXTERNAL],
            preconditions=[],
            impact="Test",
            likelihood="HIGH",
            affected_components=[],
        )
        assert threat_critical_high.compute_risk_score() == 1.0

        threat_low_low = MemoryThreatVector(
            threat_id="TMV-MEM-TEST2",
            name="Test",
            description="Test",
            category=ThreatCategory.MEMORY_POISONING,
            severity=ThreatSeverity.LOW,
            attack_vectors=[AttackVector.EXTERNAL],
            preconditions=[],
            impact="Test",
            likelihood="LOW",
            affected_components=[],
        )
        assert threat_low_low.compute_risk_score() == 0.25 * 0.3


class TestPredefinedThreats:
    """Tests for predefined TMV-MEM-* threats."""

    def test_tmv_mem_001_properties(self) -> None:
        """Test TMV-MEM-001 Direct Memory Poisoning."""
        assert TMV_MEM_001.threat_id == "TMV-MEM-001"
        assert TMV_MEM_001.category == ThreatCategory.MEMORY_POISONING
        assert TMV_MEM_001.severity == ThreatSeverity.CRITICAL

    def test_tmv_mem_002_properties(self) -> None:
        """Test TMV-MEM-002 Gradient-Based Manipulation."""
        assert TMV_MEM_002.threat_id == "TMV-MEM-002"
        assert TMV_MEM_002.likelihood == "LOW"  # Mitigated by INV-MEM-006

    def test_tmv_mem_006_properties(self) -> None:
        """Test TMV-MEM-006 Unauthorized Snapshot Deletion."""
        assert TMV_MEM_006.threat_id == "TMV-MEM-006"
        assert TMV_MEM_006.category == ThreatCategory.UNAUTHORIZED_ACCESS

    def test_tmv_mem_010_properties(self) -> None:
        """Test TMV-MEM-010 Memory Extraction Attack."""
        assert TMV_MEM_010.threat_id == "TMV-MEM-010"
        assert TMV_MEM_010.category == ThreatCategory.EXFILTRATION


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY MITIGATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryMitigation:
    """Tests for MemoryMitigation."""

    def test_valid_mitigation_creation(self) -> None:
        """Test creating a valid mitigation."""
        mitigation = MemoryMitigation(
            mitigation_id="TMM-MEM-TEST",
            name="Test Mitigation",
            description="A test mitigation",
            threat_ids=["TMV-MEM-001"],
            status=MitigationStatus.IMPLEMENTED,
            implementation_notes="Test notes",
            effectiveness="HIGH",
            cost="LOW",
        )
        assert mitigation.mitigation_id == "TMM-MEM-TEST"

    def test_invalid_id_raises(self) -> None:
        """Test that invalid ID format raises error."""
        with pytest.raises(ValueError):
            MemoryMitigation(
                mitigation_id="INVALID-001",
                name="Test",
                description="Test",
                threat_ids=[],
                status=MitigationStatus.PLANNED,
                implementation_notes="Test",
                effectiveness="HIGH",
                cost="LOW",
            )


class TestPredefinedMitigations:
    """Tests for predefined TMM-MEM-* mitigations."""

    def test_tmm_mem_001_properties(self) -> None:
        """Test TMM-MEM-001 Cryptographic State Hashing."""
        assert TMM_MEM_001.mitigation_id == "TMM-MEM-001"
        assert TMM_MEM_001.status == MitigationStatus.IMPLEMENTED
        assert "INV-MEM-001" in TMM_MEM_001.invariants_enforced

    def test_tmm_mem_002_properties(self) -> None:
        """Test TMM-MEM-002 Production Learning Prohibition."""
        assert TMM_MEM_002.mitigation_id == "TMM-MEM-002"
        assert "TMV-MEM-002" in TMM_MEM_002.threat_ids

    def test_tmm_mem_006_properties(self) -> None:
        """Test TMM-MEM-006 Shadow Mode Default."""
        assert TMM_MEM_006.mitigation_id == "TMM-MEM-006"
        assert "INV-MEM-010" in TMM_MEM_006.invariants_enforced


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY THREAT MODEL REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryThreatModelRegistry:
    """Tests for MemoryThreatModelRegistry."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton between tests."""
        MemoryThreatModelRegistry._instance = None
        MemoryThreatModelRegistry._initialized = False

    def test_singleton_pattern(self) -> None:
        """Test registry is singleton."""
        registry1 = MemoryThreatModelRegistry()
        registry2 = MemoryThreatModelRegistry()
        assert registry1 is registry2

    def test_p26_threats_registered(self) -> None:
        """Test that P26 threats are auto-registered."""
        registry = MemoryThreatModelRegistry()
        assert registry.threat_count() == 12  # TMV-MEM-001 through 012

    def test_p26_mitigations_registered(self) -> None:
        """Test that P26 mitigations are auto-registered."""
        registry = MemoryThreatModelRegistry()
        assert registry.mitigation_count() == 10  # TMM-MEM-001 through 010

    def test_get_threat(self) -> None:
        """Test getting threat by ID."""
        registry = MemoryThreatModelRegistry()
        threat = registry.get_threat("TMV-MEM-001")
        assert threat is not None
        assert threat.name == "Direct Memory Poisoning"

    def test_get_mitigation(self) -> None:
        """Test getting mitigation by ID."""
        registry = MemoryThreatModelRegistry()
        mit = registry.get_mitigation("TMM-MEM-001")
        assert mit is not None
        assert mit.name == "Cryptographic State Hashing"

    def test_list_by_category(self) -> None:
        """Test filtering threats by category."""
        registry = MemoryThreatModelRegistry()
        poisoning = registry.list_by_category(ThreatCategory.MEMORY_POISONING)
        assert len(poisoning) == 3  # TMV-MEM-001, 002, 003

    def test_list_by_severity(self) -> None:
        """Test filtering threats by severity."""
        registry = MemoryThreatModelRegistry()
        critical = registry.list_by_severity(ThreatSeverity.CRITICAL)
        assert len(critical) >= 4  # Multiple critical threats

    def test_get_mitigations_for_threat(self) -> None:
        """Test getting mitigations for a specific threat."""
        registry = MemoryThreatModelRegistry()
        mits = registry.get_mitigations_for_threat("TMV-MEM-001")
        assert len(mits) >= 1
        assert any(m.mitigation_id == "TMM-MEM-001" for m in mits)

    def test_compute_coverage(self) -> None:
        """Test coverage computation."""
        registry = MemoryThreatModelRegistry()
        coverage = registry.compute_coverage()

        assert coverage["total_threats"] == 12
        assert coverage["total_mitigations"] == 10
        assert coverage["coverage_percentage"] > 0
