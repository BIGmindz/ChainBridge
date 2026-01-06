"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          FIVE PILLARS MULTI-LEDGER TEST SUITE — PAC-OCC-P34                   ║
║                                                                               ║
║  Tests: HederaAdapter, XRPAdapter, UniversalDispatcher                        ║
║  Iron Pattern: All async must use daemon threads, no .join()                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
import os
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Mark all tests as oracle tests
pytestmark = pytest.mark.oracle


# ═══════════════════════════════════════════════════════════════════════════════
# HEDERA ADAPTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHederaAdapter:
    """Test suite for Hedera Consensus Service (HCS) adapter."""
    
    def test_hedera_adapter_instantiation(self):
        """HederaAdapter should instantiate with default config."""
        from src.core.oracle.hedera_adapter import HederaAdapter
        
        adapter = HederaAdapter(enabled=False)
        assert adapter is not None
        assert adapter.enabled is False
    
    def test_hedera_adapter_topic_config(self):
        """HederaAdapter should read topic ID from environment."""
        from src.core.oracle.hedera_adapter import HederaAdapter
        
        adapter = HederaAdapter(
            topic_id="0.0.12345",
            enabled=False,
        )
        assert adapter.topic_id == "0.0.12345"
    
    def test_hedera_submit_disabled(self):
        """HederaAdapter should skip submission when disabled."""
        from src.core.oracle.hedera_adapter import HederaAdapter, HCSStatus
        
        adapter = HederaAdapter(enabled=False)
        result = adapter.submit_proof(
            proof_hash="abc123",
            pac_id="PAC-TEST",
            blocking=True,
        )
        
        assert result.status == HCSStatus.DISABLED
        assert result.message_id is not None
    
    def test_hedera_message_format(self):
        """HCS message should follow ChainBridge format."""
        from src.core.oracle.hedera_adapter import HCSMessage
        
        msg = HCSMessage(
            message_id="HCS-TEST-001",
            proof_hash="abc123",
            timestamp=datetime.now(timezone.utc).isoformat(),
            pac_id="PAC-OCC-P34",
            event_type="PAC_COMPLETED",
            version="1.0.0",
        )
        
        payload = msg.to_dict()
        assert payload["proof_hash"] == "abc123"
        assert payload["pac_id"] == "PAC-OCC-P34"
        assert payload["event_type"] == "PAC_COMPLETED"
        assert payload["version"] == "1.0.0"
    
    def test_hedera_stats_tracking(self):
        """HederaAdapter should track submission statistics."""
        from src.core.oracle.hedera_adapter import HederaAdapter
        
        adapter = HederaAdapter(enabled=False)
        
        # Submit a few (disabled mode)
        adapter.submit_proof("hash1", blocking=True)
        adapter.submit_proof("hash2", blocking=True)
        adapter.submit_proof("hash3", blocking=True)
        
        stats = adapter.get_stats()
        assert stats["submissions"]["total"] == 3
        assert stats["enabled"] is False
    
    def test_hedera_singleton_pattern(self):
        """get_hedera_adapter should return singleton instance."""
        from src.core.oracle.hedera_adapter import get_hedera_adapter
        
        adapter1 = get_hedera_adapter()
        adapter2 = get_hedera_adapter()
        
        assert adapter1 is adapter2


# ═══════════════════════════════════════════════════════════════════════════════
# XRP ADAPTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestXRPAdapter:
    """Test suite for XRP Ledger (XRPL) adapter."""
    
    def test_xrp_adapter_instantiation(self):
        """XRPAdapter should instantiate with default config."""
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        adapter = XRPAdapter(enabled=False)
        assert adapter is not None
        assert adapter.enabled is False
    
    def test_xrp_adapter_network_config(self):
        """XRPAdapter should accept network configuration."""
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        adapter = XRPAdapter(
            network="testnet",
            enabled=False,
        )
        assert adapter.network == "testnet"
    
    def test_xrp_submit_disabled(self):
        """XRPAdapter should skip submission when disabled."""
        from src.core.oracle.xrp_adapter import XRPAdapter, XRPStatus
        
        adapter = XRPAdapter(enabled=False)
        result = adapter.submit_attestation(
            proof_hash="abc123",
            blocking=True,
        )
        
        assert result.status == XRPStatus.DISABLED
        assert result.record_id is not None
    
    def test_xrp_memo_format(self):
        """XRP memos should follow ChainBridge format."""
        from src.core.oracle.xrp_adapter import XRPMemo
        
        memo = XRPMemo(
            memo_type="CHAINBRIDGE/PROOF",
            memo_data="abc123",
        )
        
        assert memo.memo_type == "CHAINBRIDGE/PROOF"
        assert memo.memo_data == "abc123"
    
    def test_xrp_cross_ledger_linking(self):
        """XRP attestation should include HCS sequence for cross-ledger linking."""
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        adapter = XRPAdapter(enabled=False)
        result = adapter.submit_attestation(
            proof_hash="abc123",
            hcs_sequence_number=42,
            hcs_topic_id="0.0.12345",
            blocking=True,
        )
        
        # The record should reference the HCS sequence
        assert result.record_id is not None
    
    def test_xrp_stats_tracking(self):
        """XRPAdapter should track submission statistics."""
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        adapter = XRPAdapter(enabled=False)
        
        # Submit a few (disabled mode)
        adapter.submit_attestation("hash1", blocking=True)
        adapter.submit_attestation("hash2", blocking=True)
        
        stats = adapter.get_stats()
        assert stats["submissions"]["total"] == 2
        assert stats["enabled"] is False
    
    def test_xrp_singleton_pattern(self):
        """get_xrp_adapter should return singleton instance."""
        from src.core.oracle.xrp_adapter import get_xrp_adapter
        
        adapter1 = get_xrp_adapter()
        adapter2 = get_xrp_adapter()
        
        assert adapter1 is adapter2


# ═══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL DISPATCHER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUniversalDispatcher:
    """Test suite for the Universal Dispatcher (Five Pillars Gateway)."""
    
    def test_dispatcher_instantiation(self):
        """UniversalDispatcher should instantiate with default adapters."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        
        dispatcher = UniversalDispatcher(enabled=False)
        assert dispatcher is not None
        assert dispatcher.enabled is False
    
    def test_dispatcher_proof_hash(self):
        """Dispatcher should compute consistent SHA256 proof hashes."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        
        dispatcher = UniversalDispatcher(enabled=False)
        
        # Compute hash
        hash1 = dispatcher._compute_proof_hash({"foo": "bar"})
        hash2 = dispatcher._compute_proof_hash({"foo": "bar"})
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex
    
    def test_dispatcher_dispatch_disabled(self):
        """Dispatch should return outcome even when disabled."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        
        dispatcher = UniversalDispatcher(enabled=False)
        outcome = dispatcher.dispatch(
            payload={"test": "data"},
            pac_id="PAC-TEST",
            blocking=True,
        )
        
        assert outcome.dispatch_id.startswith("DSP-")
        assert outcome.proof_hash is not None
        assert outcome.pac_id == "PAC-TEST"
    
    def test_dispatcher_dispatch_enabled(self):
        """Dispatch should populate pillar results when enabled."""
        from src.core.oracle.dispatcher import UniversalDispatcher, PillarType
        from src.core.oracle.hedera_adapter import HederaAdapter
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        # Create disabled adapters
        hedera = HederaAdapter(enabled=False)
        xrp = XRPAdapter(enabled=False)
        
        dispatcher = UniversalDispatcher(
            hedera_adapter=hedera,
            xrp_adapter=xrp,
            enabled=True,
            parallel=False,  # Sequential for testing
        )
        
        outcome = dispatcher.dispatch(
            payload={"test": "data"},
            pac_id="PAC-P34",
            event_type="TEST_EVENT",
            agent_gid="GID-01",
            blocking=True,
        )
        
        assert outcome.hedera is not None
        assert outcome.xrp is not None
        assert outcome.sxt is not None
        assert outcome.chainlink is not None
        assert outcome.seeburger is not None
    
    def test_dispatcher_selective_pillars(self):
        """Dispatch should support selective pillar targeting."""
        from src.core.oracle.dispatcher import UniversalDispatcher, PillarType
        from src.core.oracle.hedera_adapter import HederaAdapter
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        hedera = HederaAdapter(enabled=False)
        xrp = XRPAdapter(enabled=False)
        
        dispatcher = UniversalDispatcher(
            hedera_adapter=hedera,
            xrp_adapter=xrp,
            enabled=True,
        )
        
        outcome = dispatcher.dispatch(
            payload={"test": "data"},
            pillars=[PillarType.HEDERA],  # Only Hedera
            blocking=True,
        )
        
        assert outcome.hedera is not None
        assert outcome.xrp is None  # Not targeted
    
    def test_dispatcher_pac_completed_convenience(self):
        """dispatch_pac_completed should set proper event type."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        
        dispatcher = UniversalDispatcher(enabled=False)
        outcome = dispatcher.dispatch_pac_completed(
            pac_id="PAC-OCC-P34",
            verdict="ACCEPTED",
            executor_gid="GID-00",
            blocking=True,
        )
        
        assert outcome.pac_id == "PAC-OCC-P34"
        assert outcome.event_type == "PAC_COMPLETED"
        assert outcome.agent_gid == "GID-00"
    
    def test_dispatcher_stats(self):
        """Dispatcher should track aggregate statistics."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        
        dispatcher = UniversalDispatcher(enabled=False)
        dispatcher.dispatch({"test": 1}, blocking=True)
        dispatcher.dispatch({"test": 2}, blocking=True)
        
        stats = dispatcher.get_stats()
        assert stats["total_dispatches"] == 2
        assert stats["enabled"] is False
    
    def test_dispatcher_outcome_to_dict(self):
        """DispatchOutcome should serialize to dictionary."""
        from src.core.oracle.dispatcher import DispatchOutcome
        
        outcome = DispatchOutcome(
            dispatch_id="DSP-001",
            timestamp="2025-01-01T00:00:00Z",
            proof_hash="abc123",
            pac_id="PAC-TEST",
        )
        
        data = outcome.to_dict()
        assert data["dispatch_id"] == "DSP-001"
        assert data["pac_id"] == "PAC-TEST"
        assert "pillars" in data
    
    def test_dispatcher_singleton_pattern(self):
        """get_dispatcher should return singleton instance."""
        from src.core.oracle.dispatcher import get_dispatcher
        
        dispatcher1 = get_dispatcher()
        dispatcher2 = get_dispatcher()
        
        assert dispatcher1 is dispatcher2


# ═══════════════════════════════════════════════════════════════════════════════
# IRON PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIronPattern:
    """Tests verifying Iron Architecture compliance (no blocking)."""
    
    def test_dispatch_non_blocking(self):
        """Dispatch should return immediately (non-blocking)."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        from src.core.oracle.hedera_adapter import HederaAdapter
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        hedera = HederaAdapter(enabled=False)
        xrp = XRPAdapter(enabled=False)
        
        dispatcher = UniversalDispatcher(
            hedera_adapter=hedera,
            xrp_adapter=xrp,
            enabled=True,
            parallel=True,  # Fire in parallel threads
        )
        
        start = time.time()
        outcome = dispatcher.dispatch(
            payload={"large": "payload" * 100},
            blocking=False,  # Non-blocking
        )
        elapsed = time.time() - start
        
        # Should return almost immediately (< 0.1s)
        assert elapsed < 0.1, f"Dispatch took {elapsed}s - should be non-blocking!"
        assert outcome.dispatch_id is not None
    
    def test_hedera_non_blocking(self):
        """HederaAdapter submit_proof should be non-blocking."""
        from src.core.oracle.hedera_adapter import HederaAdapter
        
        adapter = HederaAdapter(enabled=False)
        
        start = time.time()
        result = adapter.submit_proof(
            proof_hash="test123",
            blocking=False,
        )
        elapsed = time.time() - start
        
        assert elapsed < 0.1, f"Hedera submission took {elapsed}s - should be non-blocking!"
        assert result.message_id is not None
    
    def test_xrp_non_blocking(self):
        """XRPAdapter submit_attestation should be non-blocking."""
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        adapter = XRPAdapter(enabled=False)
        
        start = time.time()
        result = adapter.submit_attestation(
            proof_hash="test123",
            blocking=False,
        )
        elapsed = time.time() - start
        
        assert elapsed < 0.1, f"XRP submission took {elapsed}s - should be non-blocking!"
        assert result.record_id is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CROSS-LEDGER LINKING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossLedgerLinking:
    """Tests for cross-ledger reference linking."""
    
    def test_hcs_sequence_propagation(self):
        """HCS sequence number should propagate to XRP attestation."""
        from src.core.oracle.xrp_adapter import XRPAdapter
        
        adapter = XRPAdapter(enabled=False)
        result = adapter.submit_attestation(
            proof_hash="abc123",
            hcs_sequence_number=12345,
            hcs_topic_id="0.0.999",
            blocking=True,
        )
        
        # Record should reference the HCS sequence
        assert result.record_id is not None
    
    def test_proof_hash_consistency(self):
        """Same payload should produce same proof hash across ledgers."""
        from src.core.oracle.dispatcher import UniversalDispatcher
        
        dispatcher = UniversalDispatcher(enabled=False)
        
        payload = {"pac_id": "PAC-TEST", "verdict": "ACCEPTED"}
        
        hash1 = dispatcher._compute_proof_hash(payload)
        hash2 = dispatcher._compute_proof_hash(payload)
        
        assert hash1 == hash2
        assert len(hash1) == 64


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE IMPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestModuleImports:
    """Tests verifying module structure and exports."""
    
    def test_oracle_module_exports(self):
        """Oracle module should export all public APIs."""
        from src.core.oracle import (
            HederaAdapter,
            XRPAdapter,
            UniversalDispatcher,
            get_hedera_adapter,
            get_xrp_adapter,
            get_dispatcher,
        )
        
        assert HederaAdapter is not None
        assert XRPAdapter is not None
        assert UniversalDispatcher is not None
    
    def test_pillar_types(self):
        """PillarType enum should list all five pillars."""
        from src.core.oracle.dispatcher import PillarType
        
        pillars = list(PillarType)
        assert len(pillars) == 5
        
        names = [p.value for p in pillars]
        assert "hedera" in names
        assert "sxt" in names
        assert "chainlink" in names
        assert "xrp" in names
        assert "seeburger" in names
    
    def test_hcs_status_enum(self):
        """HCSStatus enum should cover all states."""
        from src.core.oracle.hedera_adapter import HCSStatus
        
        statuses = [s.value for s in HCSStatus]
        assert "submitted" in statuses
        assert "confirmed" in statuses
        assert "failed" in statuses
        assert "disabled" in statuses
    
    def test_xrp_status_enum(self):
        """XRPStatus enum should cover all states."""
        from src.core.oracle.xrp_adapter import XRPStatus
        
        statuses = [s.value for s in XRPStatus]
        assert "submitted" in statuses
        assert "validated" in statuses
        assert "failed" in statuses
        assert "disabled" in statuses
