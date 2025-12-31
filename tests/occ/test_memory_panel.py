# ═══════════════════════════════════════════════════════════════════════════════
# OCC Memory Panel Tests
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
OCC Memory Panel Tests — UI component tests for memory visualization.
"""

import pytest
from datetime import datetime, timezone

from core.occ.memory_panel import (
    ComponentSize,
    HealthStatus,
    InvariantComplianceMatrix,
    InvariantStatusRow,
    MemoryPanelFactory,
    MemoryStateCard,
    OCCMemoryPanel,
    PanelTheme,
    RoutingStatsPanel,
    SnapshotChainView,
    SnapshotNode,
)
from core.ml.neural_memory import (
    MemoryMode,
    MemorySnapshot,
    MemoryStateHash,
    MemoryTier,
    SnapshotStatus,
)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY STATE CARD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryStateCard:
    """Tests for MemoryStateCard."""

    def test_create_state_card(self) -> None:
        """Test creating a memory state card."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        card = MemoryStateCard(
            state_hash=state_hash,
            mode=MemoryMode.SHADOW,
        )
        assert card.health == HealthStatus.HEALTHY
        assert card.theme == PanelTheme.DARK

    def test_to_display_dict(self) -> None:
        """Test conversion to display dictionary."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        card = MemoryStateCard(
            state_hash=state_hash,
            mode=MemoryMode.SHADOW,
        )
        display = card.to_display_dict()

        assert display["component"] == "MemoryStateCard"
        assert "hash_preview" in display["data"]
        assert display["data"]["mode"] == "SHADOW"
        assert "aria-label" in display["accessibility"]

    def test_get_status_color(self) -> None:
        """Test status color mapping."""
        state_hash = MemoryStateHash.compute({"key": "value"})

        card_healthy = MemoryStateCard(
            state_hash=state_hash,
            mode=MemoryMode.SHADOW,
            health=HealthStatus.HEALTHY,
        )
        assert card_healthy.get_status_color() == "#10B981"  # Green

        card_critical = MemoryStateCard(
            state_hash=state_hash,
            mode=MemoryMode.SHADOW,
            health=HealthStatus.CRITICAL,
        )
        assert card_critical.get_status_color() == "#EF4444"  # Red


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT CHAIN VIEW TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSnapshotNode:
    """Tests for SnapshotNode."""

    def test_get_status_icon(self) -> None:
        """Test status icon mapping."""
        node_complete = SnapshotNode(
            snapshot_id="MEM-SNAP-000001",
            status=SnapshotStatus.COMPLETE,
            created_at=datetime.now(timezone.utc).isoformat(),
            hash_preview="abc123",
        )
        assert node_complete.get_status_icon() == "✓"

        node_anchored = SnapshotNode(
            snapshot_id="MEM-SNAP-000002",
            status=SnapshotStatus.ANCHORED,
            created_at=datetime.now(timezone.utc).isoformat(),
            hash_preview="def456",
        )
        assert node_anchored.get_status_icon() == "⚓"


class TestSnapshotChainView:
    """Tests for SnapshotChainView."""

    def test_from_snapshots(self) -> None:
        """Test creating view from snapshots."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshots = [
            MemorySnapshot(
                snapshot_id="MEM-SNAP-000001",
                state_hash=state_hash,
                status=SnapshotStatus.COMPLETE,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
            MemorySnapshot(
                snapshot_id="MEM-SNAP-000002",
                state_hash=state_hash,
                status=SnapshotStatus.ANCHORED,
                created_at=datetime.now(timezone.utc).isoformat(),
                predecessor_id="MEM-SNAP-000001",
            ),
        ]

        view = SnapshotChainView.from_snapshots(snapshots, current_id="MEM-SNAP-000002")
        assert len(view.nodes) == 2
        assert view.nodes[1].is_current is True

    def test_to_display_dict(self) -> None:
        """Test conversion to display dictionary."""
        view = SnapshotChainView(nodes=[
            SnapshotNode(
                snapshot_id="MEM-SNAP-000001",
                status=SnapshotStatus.COMPLETE,
                created_at=datetime.now(timezone.utc).isoformat(),
                hash_preview="abc123",
            ),
        ])

        display = view.to_display_dict()
        assert display["component"] == "SnapshotChainView"
        assert len(display["data"]["nodes"]) == 1
        assert display["accessibility"]["role"] == "list"


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING STATS PANEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestRoutingStatsPanel:
    """Tests for RoutingStatsPanel."""

    def test_from_stats(self) -> None:
        """Test creating panel from stats dictionary."""
        stats = {
            "fast_count": 10,
            "slow_count": 5,
            "hybrid_count": 3,
            "total_decisions": 18,
            "avg_confidence": 0.85,
        }
        panel = RoutingStatsPanel.from_stats(stats)

        assert panel.fast_count == 10
        assert panel.slow_count == 5
        assert panel.total_decisions == 18

    def test_to_display_dict_percentages(self) -> None:
        """Test percentage calculations in display dict."""
        panel = RoutingStatsPanel(
            fast_count=50,
            slow_count=30,
            hybrid_count=20,
            total_decisions=100,
        )
        display = panel.to_display_dict()

        assert display["data"]["fast"]["percentage"] == 50.0
        assert display["data"]["slow"]["percentage"] == 30.0
        assert display["data"]["hybrid"]["percentage"] == 20.0

    def test_to_display_dict_zero_total(self) -> None:
        """Test handling zero total decisions."""
        panel = RoutingStatsPanel()
        display = panel.to_display_dict()

        assert display["data"]["fast"]["percentage"] == 0
        assert display["data"]["total"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT COMPLIANCE MATRIX TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestInvariantStatusRow:
    """Tests for InvariantStatusRow."""

    def test_get_status_color(self) -> None:
        """Test status color mapping."""
        row_pass = InvariantStatusRow(
            invariant_id="INV-MEM-001",
            name="Test",
            status="PASS",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
        assert row_pass.get_status_color() == "#10B981"

        row_fail = InvariantStatusRow(
            invariant_id="INV-MEM-001",
            name="Test",
            status="FAIL",
            last_checked=datetime.now(timezone.utc).isoformat(),
        )
        assert row_fail.get_status_color() == "#EF4444"


class TestInvariantComplianceMatrix:
    """Tests for InvariantComplianceMatrix."""

    def test_add_invariant(self) -> None:
        """Test adding invariants to matrix."""
        matrix = InvariantComplianceMatrix()
        matrix.add_invariant("INV-MEM-001", "Snapshot Immutability", "PASS")
        matrix.add_invariant("INV-MEM-002", "Update Audit Trail", "PASS")

        assert len(matrix.rows) == 2
        assert matrix.overall_status == "PASS"

    def test_overall_status_fail_on_any_fail(self) -> None:
        """Test overall status becomes FAIL on any failure."""
        matrix = InvariantComplianceMatrix()
        matrix.add_invariant("INV-MEM-001", "Test 1", "PASS")
        matrix.add_invariant("INV-MEM-002", "Test 2", "FAIL")

        assert matrix.overall_status == "FAIL"

    def test_overall_status_warn(self) -> None:
        """Test overall status WARN when no failures."""
        matrix = InvariantComplianceMatrix()
        matrix.add_invariant("INV-MEM-001", "Test 1", "PASS")
        matrix.add_invariant("INV-MEM-002", "Test 2", "WARN")

        assert matrix.overall_status == "WARN"

    def test_to_display_dict(self) -> None:
        """Test conversion to display dictionary."""
        matrix = InvariantComplianceMatrix()
        matrix.add_invariant("INV-MEM-001", "Test 1", "PASS")
        matrix.add_invariant("INV-MEM-002", "Test 2", "FAIL")

        display = matrix.to_display_dict()
        assert display["component"] == "InvariantComplianceMatrix"
        assert display["data"]["total_invariants"] == 2
        assert display["data"]["passing"] == 1
        assert display["data"]["failing"] == 1
        assert display["accessibility"]["role"] == "grid"


# ═══════════════════════════════════════════════════════════════════════════════
# OCC MEMORY PANEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOCCMemoryPanel:
    """Tests for OCCMemoryPanel."""

    def test_is_complete(self) -> None:
        """Test completeness check."""
        panel_incomplete = OCCMemoryPanel()
        assert panel_incomplete.is_complete() is False

        state_hash = MemoryStateHash.compute({"key": "value"})
        panel_complete = OCCMemoryPanel(
            state_card=MemoryStateCard(state_hash=state_hash, mode=MemoryMode.SHADOW),
            chain_view=SnapshotChainView(),
            stats_panel=RoutingStatsPanel(),
            compliance_matrix=InvariantComplianceMatrix(),
        )
        assert panel_complete.is_complete() is True

    def test_get_overall_health_unknown_when_incomplete(self) -> None:
        """Test health is UNKNOWN when incomplete."""
        panel = OCCMemoryPanel()
        assert panel.get_overall_health() == HealthStatus.UNKNOWN

    def test_get_overall_health_critical_on_card_critical(self) -> None:
        """Test health is CRITICAL when state card is critical."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        panel = OCCMemoryPanel(
            state_card=MemoryStateCard(
                state_hash=state_hash,
                mode=MemoryMode.SHADOW,
                health=HealthStatus.CRITICAL,
            ),
            chain_view=SnapshotChainView(),
            stats_panel=RoutingStatsPanel(),
            compliance_matrix=InvariantComplianceMatrix(),
        )
        assert panel.get_overall_health() == HealthStatus.CRITICAL

    def test_get_overall_health_critical_on_compliance_fail(self) -> None:
        """Test health is CRITICAL when compliance fails."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        matrix = InvariantComplianceMatrix()
        matrix.add_invariant("INV-MEM-001", "Test", "FAIL")

        panel = OCCMemoryPanel(
            state_card=MemoryStateCard(state_hash=state_hash, mode=MemoryMode.SHADOW),
            chain_view=SnapshotChainView(),
            stats_panel=RoutingStatsPanel(),
            compliance_matrix=matrix,
        )
        assert panel.get_overall_health() == HealthStatus.CRITICAL

    def test_to_display_dict(self) -> None:
        """Test conversion to display dictionary."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        panel = OCCMemoryPanel(
            state_card=MemoryStateCard(state_hash=state_hash, mode=MemoryMode.SHADOW),
            chain_view=SnapshotChainView(),
            stats_panel=RoutingStatsPanel(),
            compliance_matrix=InvariantComplianceMatrix(),
        )

        display = panel.to_display_dict()
        assert display["component"] == "OCCMemoryPanel"
        assert display["header"]["title"] == "Neural Memory Monitor"
        assert display["components"]["state_card"] is not None
        assert display["layout"]["grid"] == "2x2"
        assert "skip_link" in display["accessibility"]


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY PANEL FACTORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryPanelFactory:
    """Tests for MemoryPanelFactory."""

    def test_create_state_card(self) -> None:
        """Test factory creates state card."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        card = MemoryPanelFactory.create_state_card(
            state_hash=state_hash,
            mode=MemoryMode.SHADOW,
        )
        assert isinstance(card, MemoryStateCard)

    def test_create_chain_view(self) -> None:
        """Test factory creates chain view."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshots = [
            MemorySnapshot(
                snapshot_id="MEM-SNAP-000001",
                state_hash=state_hash,
                status=SnapshotStatus.COMPLETE,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]
        view = MemoryPanelFactory.create_chain_view(snapshots)
        assert isinstance(view, SnapshotChainView)
        assert len(view.nodes) == 1

    def test_create_stats_panel(self) -> None:
        """Test factory creates stats panel."""
        stats = {"fast_count": 10, "slow_count": 5, "total_decisions": 15}
        panel = MemoryPanelFactory.create_stats_panel(stats)
        assert isinstance(panel, RoutingStatsPanel)
        assert panel.fast_count == 10

    def test_create_compliance_matrix(self) -> None:
        """Test factory creates compliance matrix."""
        results = {
            "INV-MEM-001": True,
            "INV-MEM-002": False,
            "INV-MEM-003": True,
        }
        matrix = MemoryPanelFactory.create_compliance_matrix(results)
        assert isinstance(matrix, InvariantComplianceMatrix)
        assert len(matrix.rows) == 3

    def test_create_full_panel(self) -> None:
        """Test factory creates complete panel."""
        state_hash = MemoryStateHash.compute({"key": "value"})
        snapshots = [
            MemorySnapshot(
                snapshot_id="MEM-SNAP-000001",
                state_hash=state_hash,
                status=SnapshotStatus.COMPLETE,
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
        ]

        panel = MemoryPanelFactory.create_full_panel(
            state_hash=state_hash,
            mode=MemoryMode.SHADOW,
            snapshots=snapshots,
            routing_stats={"fast_count": 10, "slow_count": 5, "total_decisions": 15},
            invariant_results={"INV-MEM-001": True},
        )

        assert isinstance(panel, OCCMemoryPanel)
        assert panel.is_complete() is True
