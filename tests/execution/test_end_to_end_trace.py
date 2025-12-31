# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge End-to-End Trace Tests
# PAC-009: Full End-to-End Traceability
# ═══════════════════════════════════════════════════════════════════════════════

"""
Comprehensive tests for end-to-end traceability.

Tests cover:
- Trace registry operations
- Decision rationale binding
- Trace graph aggregation
- Invariant enforcement
- API endpoints

GOVERNANCE INVARIANTS TESTED:
- INV-TRACE-001: Every settlement must trace to exactly one PDO
- INV-TRACE-002: Every agent action must reference PAC + PDO
- INV-TRACE-003: Ledger hash links all phases
- INV-TRACE-004: OC renders full chain without inference
- INV-TRACE-005: Missing links are explicit and non-silent
"""

import pytest
from datetime import datetime, timezone

from core.execution.trace_registry import (
    TraceDomain,
    TraceLink,
    TraceLinkType,
    TraceRegistry,
    TraceInvariantViolation,
    get_trace_registry,
    reset_trace_registry,
    register_pdo_to_decision,
    register_decision_to_execution,
    register_execution_to_settlement,
    register_settlement_to_ledger,
    GENESIS_TRACE_HASH,
    UNAVAILABLE_MARKER,
)
from core.execution.decision_rationale import (
    DecisionFactor,
    DecisionFactorType,
    DecisionRationale,
    RationaleRegistry,
    RationaleStatus,
    get_rationale_registry,
    reset_rationale_registry,
    create_factor,
    register_decision_rationale,
)
from core.execution.trace_aggregator import (
    OCTraceView,
    OCTraceTimeline,
    TraceGap,
    TraceGraphAggregator,
    TraceNodeStatus,
    TraceViewStatus,
    get_trace_aggregator,
    reset_trace_aggregator,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_registries():
    """Reset all registries before each test."""
    reset_trace_registry()
    reset_rationale_registry()
    reset_trace_aggregator()
    yield
    reset_trace_registry()
    reset_rationale_registry()
    reset_trace_aggregator()


@pytest.fixture
def trace_registry():
    """Get fresh trace registry."""
    return TraceRegistry()


@pytest.fixture
def rationale_registry():
    """Get fresh rationale registry."""
    return RationaleRegistry()


@pytest.fixture
def sample_factors():
    """Create sample decision factors."""
    return [
        create_factor(
            factor_type=DecisionFactorType.MARKET_DATA,
            factor_name="BTC Price",
            factor_value=42000.0,
            weight=0.8,
            confidence=0.95,
            source="CoinGecko",
        ),
        create_factor(
            factor_type=DecisionFactorType.SIGNAL,
            factor_name="RSI Signal",
            factor_value="OVERSOLD",
            weight=0.6,
            confidence=0.85,
            source="Technical Analysis",
        ),
        create_factor(
            factor_type=DecisionFactorType.RISK_ASSESSMENT,
            factor_name="Portfolio Risk",
            factor_value=0.25,
            weight=0.4,
            confidence=0.90,
            source="Risk Engine",
        ),
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTraceRegistry:
    """Tests for TraceRegistry."""

    def test_register_link_creates_trace(self, trace_registry):
        """Test basic trace link registration."""
        link = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        assert link is not None
        assert link.trace_id.startswith("trace_")
        assert link.source_domain == TraceDomain.DECISION
        assert link.target_domain == TraceDomain.DECISION
        assert link.pac_id == "PAC-009"
        assert link.pdo_id == "pdo_001"
        assert link.trace_hash != ""
        assert link.previous_hash == GENESIS_TRACE_HASH

    def test_hash_chain_integrity(self, trace_registry):
        """Test hash chain is maintained across registrations."""
        link1 = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        link2 = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="dec_001",
            target_domain=TraceDomain.EXECUTION,
            target_id="exec_001",
            link_type=TraceLinkType.DECISION_TO_EXECUTION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        assert link2.previous_hash == link1.trace_hash
        assert link2.sequence_number == 1

    def test_verify_chain_valid(self, trace_registry):
        """Test chain verification passes for valid chain."""
        trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        is_valid, error = trace_registry.verify_chain()
        assert is_valid is True
        assert error is None

    def test_get_by_pdo_id(self, trace_registry):
        """Test retrieving links by PDO ID."""
        trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )
        trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_002",
            target_domain=TraceDomain.DECISION,
            target_id="dec_002",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_002",
        )

        links = trace_registry.get_by_pdo_id("pdo_001")
        assert len(links) == 1
        assert links[0].pdo_id == "pdo_001"

    def test_forbidden_update(self, trace_registry):
        """Test UPDATE is forbidden."""
        link = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        with pytest.raises(RuntimeError, match="UPDATE FORBIDDEN"):
            trace_registry.update(link.trace_id, pac_id="modified")

    def test_forbidden_delete(self, trace_registry):
        """Test DELETE is forbidden."""
        link = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        with pytest.raises(RuntimeError, match="DELETE FORBIDDEN"):
            trace_registry.delete(link.trace_id)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTraceInvariants:
    """Tests for trace invariant enforcement."""

    def test_inv_trace_001_settlement_requires_pdo(self, trace_registry):
        """INV-TRACE-001: Settlement must trace to exactly one PDO."""
        with pytest.raises(TraceInvariantViolation) as exc_info:
            trace_registry.register_link(
                source_domain=TraceDomain.EXECUTION,
                source_id="exec_001",
                target_domain=TraceDomain.SETTLEMENT,
                target_id="settle_001",
                link_type=TraceLinkType.EXECUTION_TO_SETTLEMENT,
                pac_id="PAC-009",
                pdo_id=None,  # Missing PDO!
            )

        assert exc_info.value.invariant == "INV-TRACE-001"
        assert "must have a PDO reference" in exc_info.value.message

    def test_inv_trace_001_settlement_single_pdo(self, trace_registry):
        """INV-TRACE-001: Settlement cannot link to different PDOs."""
        # First link to PDO_001
        trace_registry.register_link(
            source_domain=TraceDomain.EXECUTION,
            source_id="exec_001",
            target_domain=TraceDomain.SETTLEMENT,
            target_id="settle_001",
            link_type=TraceLinkType.EXECUTION_TO_SETTLEMENT,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        # Try to link same settlement to different PDO
        with pytest.raises(TraceInvariantViolation) as exc_info:
            trace_registry.register_link(
                source_domain=TraceDomain.EXECUTION,
                source_id="exec_002",
                target_domain=TraceDomain.SETTLEMENT,
                target_id="settle_001",  # Same settlement
                link_type=TraceLinkType.EXECUTION_TO_SETTLEMENT,
                pac_id="PAC-009",
                pdo_id="pdo_002",  # Different PDO!
            )

        assert exc_info.value.invariant == "INV-TRACE-001"
        assert "already linked to PDO" in exc_info.value.message

    def test_inv_trace_002_agent_requires_pac(self, trace_registry):
        """INV-TRACE-002: Agent action must reference PAC."""
        with pytest.raises(TraceInvariantViolation) as exc_info:
            trace_registry.register_link(
                source_domain=TraceDomain.DECISION,
                source_id="dec_001",
                target_domain=TraceDomain.EXECUTION,
                target_id="exec_001",
                link_type=TraceLinkType.DECISION_TO_EXECUTION,
                pac_id="",  # Missing PAC!
                pdo_id="pdo_001",
                agent_gid="GID-01",
            )

        assert exc_info.value.invariant == "INV-TRACE-002"


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION RATIONALE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionRationale:
    """Tests for DecisionRationale and RationaleRegistry."""

    def test_create_factor(self):
        """Test factor creation."""
        factor = create_factor(
            factor_type=DecisionFactorType.MARKET_DATA,
            factor_name="BTC Price",
            factor_value=42000.0,
            weight=0.8,
            confidence=0.95,
        )

        assert factor.factor_type == DecisionFactorType.MARKET_DATA
        assert factor.factor_name == "BTC Price"
        assert factor.factor_value == 42000.0
        assert factor.weight == 0.8
        assert factor.confidence == 0.95

    def test_register_rationale(self, rationale_registry, sample_factors):
        """Test rationale registration."""
        rationale = rationale_registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
            pdo_id="pdo_001",
            summary="Buy signal based on multiple indicators",
        )

        assert rationale is not None
        assert rationale.rationale_id.startswith("rationale_")
        assert rationale.decision_id == "dec_001"
        assert len(rationale.factors) == 3
        assert rationale.status == RationaleStatus.LINKED

    def test_confidence_score_calculation(self, rationale_registry, sample_factors):
        """Test confidence score is calculated correctly."""
        rationale = rationale_registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
        )

        # Expected: weighted average
        # (0.8*0.95 + 0.6*0.85 + 0.4*0.90) / (0.8 + 0.6 + 0.4) = 0.906...
        assert 0.9 < rationale.confidence_score < 0.92

    def test_get_by_pdo_id(self, rationale_registry, sample_factors):
        """Test retrieving rationales by PDO ID."""
        rationale_registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        rationales = rationale_registry.get_by_pdo_id("pdo_001")
        assert len(rationales) == 1
        assert rationales[0].pdo_id == "pdo_001"

    def test_rationale_chain_integrity(self, rationale_registry, sample_factors):
        """Test rationale hash chain."""
        r1 = rationale_registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors[:1],
            pac_id="PAC-009",
        )

        r2 = rationale_registry.register_rationale(
            decision_id="dec_002",
            factors=sample_factors[:2],
            pac_id="PAC-009",
        )

        assert r2.previous_hash == r1.rationale_hash
        is_valid, error = rationale_registry.verify_chain()
        assert is_valid is True


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE AGGREGATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTraceAggregator:
    """Tests for TraceGraphAggregator."""

    def test_aggregate_empty_trace(self):
        """Test aggregation with no trace data."""
        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view("pdo_nonexistent")

        assert view.pdo_id == "pdo_nonexistent"
        assert view.status == TraceViewStatus.INCOMPLETE
        assert view.completeness_score < 1.0

    def test_aggregate_with_rationale(self, sample_factors):
        """Test aggregation includes decision rationale."""
        registry = get_rationale_registry()
        registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
            pdo_id="pdo_001",
            summary="Test decision",
        )

        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view("pdo_001")

        assert len(view.decision_nodes) >= 1
        decision_node = view.decision_nodes[0]
        assert decision_node.summary == "Test decision"
        assert decision_node.factor_count == 3

    def test_identify_gaps_missing_execution(self, sample_factors):
        """INV-TRACE-005: Missing execution link is explicit."""
        registry = get_rationale_registry()
        registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view("pdo_001")

        # Should have gaps for missing EXECUTION, SETTLEMENT, LEDGER
        assert len(view.gaps) > 0
        assert view.has_gaps is True

    def test_completeness_score(self):
        """Test completeness score calculation."""
        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view("pdo_empty")

        # No domains present, completeness should be low
        assert view.completeness_score <= 0.25

    def test_aggregate_timeline(self):
        """Test timeline aggregation."""
        trace_registry = get_trace_registry()
        trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        aggregator = get_trace_aggregator()
        timeline = aggregator.aggregate_trace_timeline("pdo_001")

        assert timeline.pdo_id == "pdo_001"
        assert len(timeline.events) >= 1

    def test_pac_trace_summary(self):
        """Test PAC-level summary aggregation."""
        trace_registry = get_trace_registry()
        trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        aggregator = get_trace_aggregator()
        summary = aggregator.aggregate_pac_trace_summary("PAC-009")

        assert summary["pac_id"] == "PAC-009"
        assert summary["pdo_count"] >= 1
        assert "pdo_summaries" in summary


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_register_pdo_to_decision(self):
        """Test PDO → Decision registration."""
        link = register_pdo_to_decision(
            pdo_id="pdo_001",
            decision_id="dec_001",
            pac_id="PAC-009",
        )

        assert link.source_id == "pdo_001"
        assert link.target_id == "dec_001"
        assert link.link_type == TraceLinkType.PDO_TO_DECISION

    def test_register_decision_to_execution(self):
        """Test Decision → Execution registration."""
        link = register_decision_to_execution(
            decision_id="dec_001",
            execution_id="exec_001",
            pac_id="PAC-009",
            pdo_id="pdo_001",
            agent_gid="GID-01",
        )

        assert link.source_id == "dec_001"
        assert link.target_id == "exec_001"
        assert link.link_type == TraceLinkType.DECISION_TO_EXECUTION
        assert link.agent_gid == "GID-01"

    def test_register_execution_to_settlement(self):
        """Test Execution → Settlement registration."""
        link = register_execution_to_settlement(
            execution_id="exec_001",
            settlement_id="settle_001",
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        assert link.source_id == "exec_001"
        assert link.target_id == "settle_001"
        assert link.link_type == TraceLinkType.EXECUTION_TO_SETTLEMENT

    def test_register_settlement_to_ledger(self):
        """Test Settlement → Ledger registration."""
        link = register_settlement_to_ledger(
            settlement_id="settle_001",
            ledger_entry_id="ledger_001",
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        assert link.source_id == "settle_001"
        assert link.target_id == "ledger_001"
        assert link.link_type == TraceLinkType.SETTLEMENT_TO_LEDGER

    def test_full_trace_chain(self):
        """Test registering a complete trace chain."""
        # PDO → Decision
        register_pdo_to_decision("pdo_001", "dec_001", "PAC-009")

        # Decision → Execution
        register_decision_to_execution("dec_001", "exec_001", "PAC-009", "pdo_001")

        # Execution → Settlement
        register_execution_to_settlement("exec_001", "settle_001", "PAC-009", "pdo_001")

        # Settlement → Ledger
        register_settlement_to_ledger("settle_001", "ledger_001", "PAC-009", "pdo_001")

        # Verify full chain
        registry = get_trace_registry()
        links = registry.get_by_pdo_id("pdo_001")
        assert len(links) == 4

        is_valid, error = registry.verify_chain()
        assert is_valid is True


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingletons:
    """Tests for singleton behavior."""

    def test_trace_registry_singleton(self):
        """Test trace registry singleton."""
        r1 = get_trace_registry()
        r2 = get_trace_registry()
        assert r1 is r2

    def test_rationale_registry_singleton(self):
        """Test rationale registry singleton."""
        r1 = get_rationale_registry()
        r2 = get_rationale_registry()
        assert r1 is r2

    def test_trace_aggregator_singleton(self):
        """Test trace aggregator singleton."""
        a1 = get_trace_aggregator()
        a2 = get_trace_aggregator()
        assert a1 is a2


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialization:
    """Tests for DTO serialization."""

    def test_trace_link_to_dict(self, trace_registry):
        """Test TraceLink serialization."""
        link = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        data = link.to_dict()
        assert data["source_domain"] == "DECISION"
        assert data["target_domain"] == "DECISION"
        assert data["link_type"] == "PDO_TO_DECISION"
        assert data["pac_id"] == "PAC-009"

    def test_trace_link_from_dict(self, trace_registry):
        """Test TraceLink deserialization."""
        link = trace_registry.register_link(
            source_domain=TraceDomain.DECISION,
            source_id="pdo_001",
            target_domain=TraceDomain.DECISION,
            target_id="dec_001",
            link_type=TraceLinkType.PDO_TO_DECISION,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        data = link.to_dict()
        restored = TraceLink.from_dict(data)
        
        assert restored.trace_id == link.trace_id
        assert restored.source_domain == link.source_domain
        assert restored.target_domain == link.target_domain

    def test_oc_trace_view_to_dict(self, sample_factors):
        """Test OCTraceView serialization."""
        registry = get_rationale_registry()
        registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
            pdo_id="pdo_001",
        )

        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view("pdo_001")
        data = view.to_dict()

        assert data["pdo_id"] == "pdo_001"
        assert "decision_nodes" in data
        assert "gaps" in data
        assert "completeness_score" in data


# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END INTEGRATION TEST
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEndIntegration:
    """Full integration tests for end-to-end traceability."""

    def test_complete_trace_flow(self, sample_factors):
        """Test complete PDO → Agent → Settlement → Ledger flow."""
        # 1. Register decision rationale
        rationale_registry = get_rationale_registry()
        rationale = rationale_registry.register_rationale(
            decision_id="dec_001",
            factors=sample_factors,
            pac_id="PAC-009",
            pdo_id="pdo_001",
            summary="Buy BTC based on oversold RSI",
        )

        # 2. Create full trace chain
        trace_registry = get_trace_registry()
        
        register_pdo_to_decision("pdo_001", "dec_001", "PAC-009")
        register_decision_to_execution(
            "dec_001", "exec_001", "PAC-009", "pdo_001", "GID-01"
        )
        register_execution_to_settlement(
            "exec_001", "settle_001", "PAC-009", "pdo_001"
        )
        register_settlement_to_ledger(
            "settle_001", "ledger_001", "PAC-009", "pdo_001"
        )

        # 3. Aggregate and verify
        aggregator = get_trace_aggregator()
        view = aggregator.aggregate_trace_view("pdo_001")

        # 4. Assertions
        assert view.pdo_id == "pdo_001"
        assert len(view.decision_nodes) >= 1
        assert view.trace_links is not None
        assert len(view.trace_links) == 4

        # Chain should be valid
        is_valid, error = trace_registry.verify_chain()
        assert is_valid is True

        # Decision data should be present
        decision_node = view.decision_nodes[0]
        assert decision_node.summary == "Buy BTC based on oversold RSI"
        assert decision_node.factor_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
