#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
PAC-BENSON-P44: Ledger WRAP Binding & State Lock Tests
══════════════════════════════════════════════════════════════════════════════

Tests for:
- PAC state machine transitions (ISSUED → EXECUTED → CLOSED)
- WRAP hash binding validation
- Duplicate/replay binding rejection
- PAC closure without WRAP blocking

Error Codes Tested:
- GS_113: PAC_NOT_CLOSED_NO_WRAP
- GS_114: WRAP_PAC_HASH_MISMATCH
- GS_115: PAC_STATE_REGRESSION

Authority: BENSON (GID-00)
Mode: FAIL_CLOSED
Pattern: LEDGER_IS_FINAL
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.governance.ledger_writer import (
    GovernanceLedger,
    PacState,
    VALID_PAC_TRANSITIONS,
    EntryType,
)


class TestPacStateMachine:
    """Tests for PAC state machine transitions."""

    def test_valid_pac_transitions_structure(self):
        """Verify valid transitions are defined correctly."""
        assert PacState.ISSUED in VALID_PAC_TRANSITIONS
        assert PacState.EXECUTED in VALID_PAC_TRANSITIONS
        assert PacState.CLOSED in VALID_PAC_TRANSITIONS

        # ISSUED can only go to EXECUTED
        assert VALID_PAC_TRANSITIONS[PacState.ISSUED] == [PacState.EXECUTED]

        # EXECUTED can only go to CLOSED
        assert VALID_PAC_TRANSITIONS[PacState.EXECUTED] == [PacState.CLOSED]

        # CLOSED is terminal
        assert VALID_PAC_TRANSITIONS[PacState.CLOSED] == []

    def test_new_pac_must_be_issued(self):
        """New PACs must start in ISSUED state."""
        ledger = GovernanceLedger()

        # Valid: new PAC in ISSUED state
        result = ledger.validate_pac_state_transition(
            "PAC-TEST-P99-FAKE-01",
            PacState.ISSUED.value
        )
        assert result["valid"] is True

        # Invalid: new PAC in EXECUTED state
        result = ledger.validate_pac_state_transition(
            "PAC-TEST-P99-FAKE-01",
            PacState.EXECUTED.value
        )
        assert result["valid"] is False
        assert result["error_code"] == "GS_115"

    def test_state_regression_blocked_gs115(self):
        """State regression (CLOSED → EXECUTED) must be blocked."""
        ledger = GovernanceLedger()

        # Mock a PAC in CLOSED state
        with patch.object(ledger, 'get_pac_state', return_value=PacState.CLOSED.value):
            result = ledger.validate_pac_state_transition(
                "PAC-BENSON-P42-TEST-01",
                PacState.EXECUTED.value
            )

            assert result["valid"] is False
            assert result["error_code"] == "GS_115"
            assert "PAC_STATE_REGRESSION" in result["message"]

    def test_valid_issued_to_executed(self):
        """ISSUED → EXECUTED is valid."""
        ledger = GovernanceLedger()

        with patch.object(ledger, 'get_pac_state', return_value=PacState.ISSUED.value):
            result = ledger.validate_pac_state_transition(
                "PAC-TEST-P01-FAKE-01",
                PacState.EXECUTED.value
            )

            assert result["valid"] is True

    def test_valid_executed_to_closed(self):
        """EXECUTED → CLOSED is valid."""
        ledger = GovernanceLedger()

        with patch.object(ledger, 'get_pac_state', return_value=PacState.EXECUTED.value):
            result = ledger.validate_pac_state_transition(
                "PAC-TEST-P01-FAKE-01",
                PacState.CLOSED.value
            )

            assert result["valid"] is True

    def test_invalid_issued_to_closed(self):
        """ISSUED → CLOSED is invalid (must go through EXECUTED)."""
        ledger = GovernanceLedger()

        with patch.object(ledger, 'get_pac_state', return_value=PacState.ISSUED.value):
            result = ledger.validate_pac_state_transition(
                "PAC-TEST-P01-FAKE-01",
                PacState.CLOSED.value
            )

            assert result["valid"] is False
            assert result["error_code"] == "GS_115"


class TestWrapBinding:
    """Tests for WRAP binding validation."""

    def test_wrap_binding_requires_pac_in_ledger(self):
        """WRAP cannot bind to PAC not in ledger."""
        ledger = GovernanceLedger()

        result = ledger.validate_wrap_hash_binding(
            wrap_id="WRAP-TEST-P99-FAKE-01",
            wrap_hash="a" * 64,
            pac_id="PAC-TEST-P99-FAKE-01",
            pac_hash="b" * 64
        )

        # PAC doesn't exist, should fail
        assert result["valid"] is False
        assert result["error_code"] == "GS_114"

    def test_wrap_agent_must_match_pac_agent(self):
        """WRAP agent must match PAC agent."""
        ledger = GovernanceLedger()

        result = ledger.validate_wrap_hash_binding(
            wrap_id="WRAP-ALEX-P42-TEST-01",
            wrap_hash="a" * 64,
            pac_id="PAC-BENSON-P42-TEST-01",  # Different agent!
            pac_hash="b" * 64
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_114"
        assert "mismatch" in result["message"].lower()

    def test_wrap_number_must_match_pac_number(self):
        """WRAP P## must match PAC P##."""
        ledger = GovernanceLedger()

        result = ledger.validate_wrap_hash_binding(
            wrap_id="WRAP-BENSON-P43-TEST-01",  # P43
            wrap_hash="a" * 64,
            pac_id="PAC-BENSON-P42-TEST-01",   # P42 - mismatch!
            pac_hash="b" * 64
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_114"


class TestDuplicateBindingRejection:
    """Tests for duplicate/replay binding rejection."""

    def test_wrap_already_bound_blocked(self):
        """Duplicate WRAP binding must be rejected."""
        ledger = GovernanceLedger()

        # Mock WRAP already bound
        with patch.object(ledger, 'is_wrap_already_bound', return_value=True):
            # Add mock entries for PAC
            with patch.object(ledger, 'get_entries_by_artifact', return_value=[{"artifact_id": "PAC-TEST-P01-FAKE-01"}]):
                result = ledger.validate_wrap_hash_binding(
                    wrap_id="WRAP-TEST-P01-FAKE-01",
                    wrap_hash="a" * 64,
                    pac_id="PAC-TEST-P01-FAKE-01",
                    pac_hash="b" * 64
                )

                assert result["valid"] is False
                assert result["error_code"] == "GS_114"
                assert "already bound" in result["message"]

    def test_is_wrap_already_bound_false_for_new(self):
        """New WRAP should not be flagged as bound."""
        ledger = GovernanceLedger()

        # For a new WRAP not in ledger
        result = ledger.is_wrap_already_bound("WRAP-TEST-P99-NEW-01")
        assert result is False


class TestPacClosure:
    """Tests for PAC closure validation (GS_113)."""

    def test_pac_cannot_close_without_wrap_gs113(self):
        """PAC in EXECUTED state cannot close without WRAP."""
        ledger = GovernanceLedger()

        with patch.object(ledger, 'get_pac_state', return_value=PacState.EXECUTED.value):
            with patch.object(ledger, 'get_wrap_binding_for_pac', return_value=None):
                result = ledger.validate_pac_closure("PAC-TEST-P01-FAKE-01")

                assert result["can_close"] is False
                assert result["error_code"] == "GS_113"
                assert "PAC_NOT_CLOSED_NO_WRAP" in result["message"]

    def test_pac_can_close_with_wrap(self):
        """PAC in EXECUTED state can close if WRAP is bound."""
        ledger = GovernanceLedger()

        mock_binding = {
            "wrap_id": "WRAP-TEST-P01-FAKE-01",
            "wrap_hash": "a" * 64,
            "pac_hash": "b" * 64,
            "bound_at": "2025-12-24T00:00:00Z"
        }

        with patch.object(ledger, 'get_pac_state', return_value=PacState.EXECUTED.value):
            with patch.object(ledger, 'get_wrap_binding_for_pac', return_value=mock_binding):
                result = ledger.validate_pac_closure("PAC-TEST-P01-FAKE-01")

                assert result["can_close"] is True
                assert result["error_code"] is None
                assert result["wrap_binding"] is not None

    def test_pac_cannot_close_from_issued_state(self):
        """PAC in ISSUED state cannot close (must be EXECUTED first)."""
        ledger = GovernanceLedger()

        with patch.object(ledger, 'get_pac_state', return_value=PacState.ISSUED.value):
            result = ledger.validate_pac_closure("PAC-TEST-P01-FAKE-01")

            assert result["can_close"] is False
            assert result["error_code"] == "GS_115"


class TestLedgerSchemaExtension:
    """Tests for ledger schema extensions."""

    def test_ledger_entry_has_pac_state_field(self):
        """LedgerEntry should have pac_state field."""
        from tools.governance.ledger_writer import LedgerEntry

        entry = LedgerEntry(
            sequence=1,
            timestamp="2025-12-24T00:00:00Z",
            entry_type="PAC_ISSUED",
            agent_gid="GID-00",
            agent_name="BENSON",
            artifact_type="PAC",
            artifact_id="PAC-BENSON-P44-TEST-01",
            artifact_status="ISSUED",
            pac_state="ISSUED"
        )

        assert entry.pac_state == "ISSUED"

    def test_ledger_entry_has_wrap_binding_field(self):
        """LedgerEntry should have wrap_binding field."""
        from tools.governance.ledger_writer import LedgerEntry

        binding = {
            "wrap_id": "WRAP-BENSON-P44-TEST-01",
            "wrap_hash": "a" * 64,
            "pac_hash": "b" * 64,
            "bound_at": "2025-12-24T00:00:00Z"
        }

        entry = LedgerEntry(
            sequence=1,
            timestamp="2025-12-24T00:00:00Z",
            entry_type="WRAP_ACCEPTED",
            agent_gid="GID-00",
            agent_name="BENSON",
            artifact_type="WRAP",
            artifact_id="WRAP-BENSON-P44-TEST-01",
            artifact_status="ACCEPTED",
            wrap_binding=binding
        )

        assert entry.wrap_binding is not None
        assert entry.wrap_binding["wrap_id"] == "WRAP-BENSON-P44-TEST-01"


class TestIntegration:
    """Integration tests for full PAC↔WRAP lifecycle."""

    def test_full_pac_lifecycle_enforced(self):
        """Test full PAC lifecycle: ISSUED → EXECUTED → (WRAP) → CLOSED."""
        ledger = GovernanceLedger()

        pac_id = "PAC-INTEGRATION-P99-TEST-01"

        # Step 1: New PAC starts ISSUED
        result = ledger.validate_pac_state_transition(pac_id, PacState.ISSUED.value)
        assert result["valid"] is True

        # Step 2: ISSUED → EXECUTED
        with patch.object(ledger, 'get_pac_state', return_value=PacState.ISSUED.value):
            result = ledger.validate_pac_state_transition(pac_id, PacState.EXECUTED.value)
            assert result["valid"] is True

        # Step 3: EXECUTED → CLOSED (without WRAP) should fail
        with patch.object(ledger, 'get_pac_state', return_value=PacState.EXECUTED.value):
            with patch.object(ledger, 'get_wrap_binding_for_pac', return_value=None):
                result = ledger.validate_pac_closure(pac_id)
                assert result["can_close"] is False
                assert result["error_code"] == "GS_113"

        # Step 4: EXECUTED → CLOSED (with WRAP) should succeed
        mock_binding = {"wrap_id": "WRAP-INTEGRATION-P99-TEST-01", "wrap_hash": "a"*64, "pac_hash": "b"*64, "bound_at": "2025-12-24T00:00:00Z"}
        with patch.object(ledger, 'get_pac_state', return_value=PacState.EXECUTED.value):
            with patch.object(ledger, 'get_wrap_binding_for_pac', return_value=mock_binding):
                result = ledger.validate_pac_closure(pac_id)
                assert result["can_close"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
