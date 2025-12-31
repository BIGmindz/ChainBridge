#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
SEQUENTIAL PAC↔WRAP ENFORCEMENT TESTS
PAC-BENSON-P42-SEQUENTIAL-PAC-WRAP-GATING-AND-CAUSAL-ADVANCEMENT-ENFORCEMENT-01
══════════════════════════════════════════════════════════════════════════════

Tests for:
1. PAC without WRAP blocks next PAC (GS_096)
2. Skipped PAC numbers are rejected (GS_097)
3. WRAP cannot exist without matching PAC (GS_098/GS_099)
4. Causal advancement enforcement

Authority: BENSON (GID-00)
Mode: FAIL_CLOSED
Pattern: CAUSALITY_OVER_CONVENIENCE
══════════════════════════════════════════════════════════════════════════════
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add repo root to path for imports
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.governance.ledger_writer import GovernanceLedger, EntryType


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def temp_ledger():
    """Create a temporary ledger for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Initialize empty ledger
        initial_data = {
            "ledger_metadata": {
                "version": "1.1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "authority": "BENSON (GID-00)",
                "format": "APPEND_ONLY_HASH_CHAINED",
                "schema_version": "1.1.0",
                "hash_algorithm": "SHA256"
            },
            "sequence_state": {
                "next_sequence": 1,
                "last_entry_timestamp": None,
                "total_entries": 0,
                "last_entry_hash": None
            },
            "agent_sequences": {},
            "entries": []
        }
        json.dump(initial_data, f, indent=2)
        temp_path = Path(f.name)

    ledger = GovernanceLedger(temp_path)
    yield ledger

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def ledger_with_complete_sequence(temp_ledger):
    """Ledger with PACs and their corresponding WRAPs."""
    # P40: PAC + WRAP (complete)
    temp_ledger.record_pac_issued(
        artifact_id="PAC-BENSON-P40-COMPLETE-01",
        agent_gid="GID-00",
        agent_name="BENSON"
    )
    temp_ledger.record_wrap_submitted(
        artifact_id="WRAP-BENSON-P40-COMPLETE-01",
        agent_gid="GID-00",
        agent_name="BENSON",
        parent_pac_id="PAC-BENSON-P40-COMPLETE-01"
    )

    # P41: PAC + WRAP (complete)
    temp_ledger.record_pac_issued(
        artifact_id="PAC-BENSON-P41-COMPLETE-01",
        agent_gid="GID-00",
        agent_name="BENSON"
    )
    temp_ledger.record_wrap_submitted(
        artifact_id="WRAP-BENSON-P41-COMPLETE-01",
        agent_gid="GID-00",
        agent_name="BENSON",
        parent_pac_id="PAC-BENSON-P41-COMPLETE-01"
    )

    return temp_ledger


@pytest.fixture
def ledger_with_open_pac(temp_ledger):
    """Ledger with a PAC that has no WRAP (open)."""
    # P40: PAC + WRAP (complete)
    temp_ledger.record_pac_issued(
        artifact_id="PAC-BENSON-P40-COMPLETE-01",
        agent_gid="GID-00",
        agent_name="BENSON"
    )
    temp_ledger.record_wrap_submitted(
        artifact_id="WRAP-BENSON-P40-COMPLETE-01",
        agent_gid="GID-00",
        agent_name="BENSON",
        parent_pac_id="PAC-BENSON-P40-COMPLETE-01"
    )

    # P41: PAC only (OPEN - no WRAP)
    temp_ledger.record_pac_issued(
        artifact_id="PAC-BENSON-P41-OPEN-01",
        agent_gid="GID-00",
        agent_name="BENSON"
    )

    return temp_ledger


# ============================================================================
# CAUSAL ADVANCEMENT TESTS (GS_096)
# ============================================================================

class TestCausalAdvancement:
    """Tests for causal advancement enforcement (GS_096)."""

    def test_pac_without_wrap_blocks_next_pac(self, ledger_with_open_pac):
        """
        PAC without WRAP should block issuance of next PAC.

        P41 has no WRAP → P42 should be BLOCKED with GS_096
        """
        result = ledger_with_open_pac.validate_causal_advancement(
            pac_id="PAC-BENSON-P42-NEW-01",
            agent_gid="GID-00"
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_096"
        assert "Missing WRAP for prior PAC" in result["message"]
        assert "PAC-BENSON-P41-OPEN-01" in result["message"]

    def test_complete_sequence_allows_advancement(self, ledger_with_complete_sequence):
        """
        All PACs have WRAPs → Next PAC should be ALLOWED.
        """
        result = ledger_with_complete_sequence.validate_causal_advancement(
            pac_id="PAC-BENSON-P42-NEW-01",
            agent_gid="GID-00"
        )

        assert result["valid"] is True
        assert result["error_code"] is None

    def test_different_agent_not_blocked(self, ledger_with_open_pac):
        """
        BENSON's open PAC should NOT block ATLAS's PAC.

        Agent sequences are independent.
        """
        result = ledger_with_open_pac.validate_causal_advancement(
            pac_id="PAC-ATLAS-P10-INDEPENDENT-01",
            agent_gid="GID-11"
        )

        # ATLAS has no prior PACs, so this should pass
        assert result["valid"] is True


# ============================================================================
# SEQUENTIAL ADVANCEMENT TESTS (GS_097)
# ============================================================================

class TestSequentialAdvancement:
    """Tests for sequential PAC numbering enforcement (GS_097)."""

    def test_skip_pac_number_rejected(self, ledger_with_complete_sequence):
        """
        Skipping P42 to issue P44 should be REJECTED.
        """
        result = ledger_with_complete_sequence.validate_causal_advancement(
            pac_id="PAC-BENSON-P44-SKIP-01",
            agent_gid="GID-00"
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_097"
        assert "gap" in result["message"].lower() or "skip" in result["message"].lower()

    def test_regression_pac_number_rejected(self, ledger_with_complete_sequence):
        """
        Issuing P40 when P41 exists should be REJECTED.
        """
        result = ledger_with_complete_sequence.validate_causal_advancement(
            pac_id="PAC-BENSON-P40-REGRESSION-01",
            agent_gid="GID-00"
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_097"

    def test_next_sequential_allowed(self, ledger_with_complete_sequence):
        """
        P41 exists → P42 should be ALLOWED.
        """
        result = ledger_with_complete_sequence.validate_causal_advancement(
            pac_id="PAC-BENSON-P42-SEQUENTIAL-01",
            agent_gid="GID-00"
        )

        assert result["valid"] is True


# ============================================================================
# PAC↔WRAP BINDING TESTS (GS_098)
# ============================================================================

class TestPacWrapBinding:
    """Tests for PAC↔WRAP binding enforcement (GS_098)."""

    def test_wrap_pac_number_mismatch_rejected(self, temp_ledger):
        """
        WRAP-P42 cannot bind to PAC-P41.
        """
        result = temp_ledger.bind_wrap_to_pac(
            wrap_id="WRAP-BENSON-P42-TEST-01",
            pac_id="PAC-BENSON-P41-TEST-01"
        )

        assert result["success"] is False
        assert result["error_code"] == "GS_098"
        assert "mismatch" in result["message"].lower()

    def test_wrap_pac_agent_mismatch_rejected(self, temp_ledger):
        """
        WRAP-BENSON cannot bind to PAC-ATLAS.
        """
        result = temp_ledger.bind_wrap_to_pac(
            wrap_id="WRAP-BENSON-P42-TEST-01",
            pac_id="PAC-ATLAS-P42-TEST-01"
        )

        assert result["success"] is False
        assert result["error_code"] == "GS_098"
        assert "agent" in result["message"].lower() or "mismatch" in result["message"].lower()

    def test_matching_wrap_pac_binding_accepted(self, temp_ledger):
        """
        WRAP-BENSON-P42 binds to PAC-BENSON-P42 successfully.
        """
        result = temp_ledger.bind_wrap_to_pac(
            wrap_id="WRAP-BENSON-P42-TEST-01",
            pac_id="PAC-BENSON-P42-TEST-01"
        )

        assert result["success"] is True
        assert result["error_code"] is None


# ============================================================================
# OPEN PAC TRACKING TESTS
# ============================================================================

class TestOpenPacTracking:
    """Tests for tracking PACs awaiting WRAPs."""

    def test_get_pacs_awaiting_wrap_returns_open_pacs(self, ledger_with_open_pac):
        """
        Should return PACs that have no corresponding WRAP.
        """
        open_pacs = ledger_with_open_pac.get_pacs_awaiting_wrap()

        assert "PAC-BENSON-P41-OPEN-01" in open_pacs
        assert "PAC-BENSON-P40-COMPLETE-01" not in open_pacs

    def test_get_pacs_awaiting_wrap_filters_by_agent(self, ledger_with_open_pac):
        """
        Should filter open PACs by agent GID.
        """
        # Add an open PAC for another agent
        ledger_with_open_pac.record_pac_issued(
            artifact_id="PAC-ATLAS-P10-OPEN-01",
            agent_gid="GID-11",
            agent_name="ATLAS"
        )

        # Filter by BENSON
        benson_open = ledger_with_open_pac.get_pacs_awaiting_wrap(agent_gid="GID-00")
        assert "PAC-BENSON-P41-OPEN-01" in benson_open
        assert "PAC-ATLAS-P10-OPEN-01" not in benson_open

        # Filter by ATLAS
        atlas_open = ledger_with_open_pac.get_pacs_awaiting_wrap(agent_gid="GID-11")
        assert "PAC-ATLAS-P10-OPEN-01" in atlas_open
        assert "PAC-BENSON-P41-OPEN-01" not in atlas_open

    def test_no_open_pacs_returns_empty(self, ledger_with_complete_sequence):
        """
        Complete sequence should return no open PACs.
        """
        open_pacs = ledger_with_complete_sequence.get_pacs_awaiting_wrap()

        assert len(open_pacs) == 0

    def test_wrap_closes_pac(self, ledger_with_open_pac):
        """
        Submitting WRAP should close the PAC.
        """
        # Before WRAP
        open_pacs_before = ledger_with_open_pac.get_pacs_awaiting_wrap()
        assert "PAC-BENSON-P41-OPEN-01" in open_pacs_before

        # Submit WRAP
        ledger_with_open_pac.record_wrap_submitted(
            artifact_id="WRAP-BENSON-P41-OPEN-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            parent_pac_id="PAC-BENSON-P41-OPEN-01"
        )

        # After WRAP
        open_pacs_after = ledger_with_open_pac.get_pacs_awaiting_wrap()
        assert "PAC-BENSON-P41-OPEN-01" not in open_pacs_after


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestCausalSequencingIntegration:
    """End-to-end tests for causal sequencing."""

    def test_full_causal_sequence(self, temp_ledger):
        """
        Test a complete causal sequence: P40 → WRAP → P41 → WRAP → P42.
        """
        # Issue P40
        temp_ledger.record_pac_issued(
            artifact_id="PAC-BENSON-P40-FULL-01",
            agent_gid="GID-00",
            agent_name="BENSON"
        )

        # P41 should be BLOCKED (P40 has no WRAP)
        result = temp_ledger.validate_causal_advancement(
            pac_id="PAC-BENSON-P41-FULL-01",
            agent_gid="GID-00"
        )
        assert result["valid"] is False
        assert result["error_code"] == "GS_096"

        # Submit WRAP for P40
        temp_ledger.record_wrap_submitted(
            artifact_id="WRAP-BENSON-P40-FULL-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            parent_pac_id="PAC-BENSON-P40-FULL-01"
        )

        # P41 should now be ALLOWED
        result = temp_ledger.validate_causal_advancement(
            pac_id="PAC-BENSON-P41-FULL-01",
            agent_gid="GID-00"
        )
        assert result["valid"] is True

        # Issue P41
        temp_ledger.record_pac_issued(
            artifact_id="PAC-BENSON-P41-FULL-01",
            agent_gid="GID-00",
            agent_name="BENSON"
        )

        # P42 should be BLOCKED (P41 has no WRAP)
        result = temp_ledger.validate_causal_advancement(
            pac_id="PAC-BENSON-P42-FULL-01",
            agent_gid="GID-00"
        )
        assert result["valid"] is False

        # Submit WRAP for P41
        temp_ledger.record_wrap_submitted(
            artifact_id="WRAP-BENSON-P41-FULL-01",
            agent_gid="GID-00",
            agent_name="BENSON",
            parent_pac_id="PAC-BENSON-P41-FULL-01"
        )

        # P42 should now be ALLOWED
        result = temp_ledger.validate_causal_advancement(
            pac_id="PAC-BENSON-P42-FULL-01",
            agent_gid="GID-00"
        )
        assert result["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
