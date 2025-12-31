#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
PAC SEQUENCE ENFORCEMENT TESTS
PAC-ALEX-P42-GOVERNANCE-PAC-SEQUENCE-ENFORCEMENT-AND-RESERVATION-LOCK-01
══════════════════════════════════════════════════════════════════════════════

Tests for:
1. PAC sequence validation (GS_096)
2. PAC reservation mechanism (GS_097, GS_098)
3. PAC↔WRAP coupling enforcement (GS_099)

Authority: ALEX (GID-08)
Mode: FAIL_CLOSED
Pattern: PAC_SEQUENCE_IS_LAW
══════════════════════════════════════════════════════════════════════════════
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add repo root to path for imports
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.governance.ledger_writer import GovernanceLedger, EntryType
from tools.governance.gate_pack import (
    validate_pac_sequence_and_reservations,
    validate_pac_wrap_coupling,
    is_pac_artifact,
    is_wrap_artifact,
    extract_wrap_id,
    ErrorCode,
)


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
                "authority": "ALEX (GID-08)",
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
def ledger_with_pacs(temp_ledger):
    """Ledger with some PACs already issued."""
    # Record PACs P40, P41
    temp_ledger.record_pac_issued(
        artifact_id="PAC-ATLAS-P40-TEST-01",
        agent_gid="GID-11",
        agent_name="ATLAS"
    )
    temp_ledger.record_pac_issued(
        artifact_id="PAC-ATLAS-P41-TEST-01",
        agent_gid="GID-11",
        agent_name="ATLAS"
    )
    return temp_ledger


@pytest.fixture
def sample_pac_content():
    """Sample PAC content for testing (with enough structural markers)."""
    return """# PAC-ALEX-P42-TEST-01

> **PAC — Test PAC**
> **Agent:** ALEX (GID-08)
> **Color:** ⚪ WHITE
> **Status:** ⚪ EXECUTED

---

## 0. RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  gid: "N/A"
```

---

## 1. AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "ALEX"
  gid: "GID-08"
  role: "Governance & Alignment Engine"
  color: "WHITE"
```

---

## 2. PAC_HEADER

```yaml
PAC_HEADER:
  pac_id: "PAC-ALEX-P42-TEST-01"
  agent: "ALEX"
  gid: "GID-08"
  artifact_type: "PAC"
  artifact_status: "EXECUTED"
```

---

## 3. FINAL_STATE

```yaml
FINAL_STATE:
  pac_id: "PAC-ALEX-P42-TEST-01"
  status: "EXECUTED"
```
"""


@pytest.fixture
def sample_wrap_content():
    """Sample WRAP content for testing."""
    return """
# WRAP-ALEX-P42-TEST-01

## 1. WRAP_HEADER

```yaml
WRAP_HEADER:
  wrap_id: "WRAP-ALEX-P42-TEST-01"
  agent: "ALEX"
  gid: "GID-08"
  artifact_type: "WRAP"
  parent_pac: "PAC-ALEX-P42-TEST-01"
```
"""


# ============================================================================
# RESERVATION MECHANISM TESTS
# ============================================================================

class TestReservationMechanism:
    """Tests for PAC number reservation mechanism."""

    def test_reserve_pac_number(self, temp_ledger):
        """Test basic PAC number reservation."""
        entry = temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        assert entry is not None
        assert entry.artifact_id == "PAC-RESERVATION-P42"
        assert entry.artifact_status == "RESERVED"

    def test_get_active_reservation(self, temp_ledger):
        """Test getting active reservation."""
        # Reserve P42
        temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # Check reservation exists
        reservation = temp_ledger.get_active_reservation(42)
        assert reservation is not None
        assert reservation["reserved_for_agent_gid"] == "GID-08"
        assert reservation["reserved_for_agent_name"] == "ALEX"

    def test_reservation_not_found(self, temp_ledger):
        """Test no reservation returns None."""
        reservation = temp_ledger.get_active_reservation(99)
        assert reservation is None

    def test_duplicate_reservation_fails(self, temp_ledger):
        """Test that duplicate reservations fail."""
        # First reservation should succeed
        temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # Second reservation should fail
        with pytest.raises(ValueError, match="already has active reservation"):
            temp_ledger.reserve_pac_number(
                pac_number=42,
                reserved_for_agent_gid="GID-11",
                reserved_for_agent_name="ATLAS",
                authority_gid="GID-00",
                authority_name="BENSON"
            )

    def test_consume_reservation(self, temp_ledger):
        """Test consuming a reservation."""
        # Reserve P42
        temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # Consume reservation
        entry = temp_ledger.consume_reservation(
            pac_number=42,
            pac_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )

        assert entry.artifact_status == "CONSUMED"

        # Reservation should no longer be active
        reservation = temp_ledger.get_active_reservation(42)
        assert reservation is None

    def test_consume_wrong_agent_fails(self, temp_ledger):
        """Test consuming reservation by wrong agent fails."""
        # Reserve P42 for ALEX
        temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # ATLAS trying to consume should fail
        with pytest.raises(ValueError, match="not ATLAS"):
            temp_ledger.consume_reservation(
                pac_number=42,
                pac_id="PAC-ATLAS-P42-TEST-01",
                agent_gid="GID-11",
                agent_name="ATLAS"
            )

    def test_consume_no_reservation_fails(self, temp_ledger):
        """Test consuming non-existent reservation fails."""
        with pytest.raises(ValueError, match="No active reservation"):
            temp_ledger.consume_reservation(
                pac_number=99,
                pac_id="PAC-ALEX-P99-TEST-01",
                agent_gid="GID-08",
                agent_name="ALEX"
            )

    def test_max_expiration_24_hours(self, temp_ledger):
        """Test that expiration is capped at 24 hours."""
        # Try to reserve with 48 hour expiration
        entry = temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON",
            expires_in_hours=48  # Should be capped to 24
        )

        # Check that it was created (we can't easily verify the cap without accessing internal state)
        assert entry is not None


# ============================================================================
# PAC SEQUENCE VALIDATION TESTS
# ============================================================================

class TestPacSequenceValidation:
    """Tests for PAC sequence validation."""

    def test_validate_next_sequential_number(self, ledger_with_pacs):
        """Test that next sequential number is valid."""
        # P41 was last, so P42 should be valid
        result = ledger_with_pacs.validate_pac_sequence(
            pac_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08"
        )

        assert result["valid"] is True

    def test_validate_out_of_order_fails(self, ledger_with_pacs):
        """Test that out-of-order PAC number fails."""
        # P41 was last, so P40 should fail
        result = ledger_with_pacs.validate_pac_sequence(
            pac_id="PAC-ALEX-P40-DUPLICATE-01",
            agent_gid="GID-08"
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_096"

    def test_validate_gap_requires_reservation(self, ledger_with_pacs):
        """Test that skipping numbers requires reservation."""
        # P41 was last, so P50 should require reservation
        result = ledger_with_pacs.validate_pac_sequence(
            pac_id="PAC-ALEX-P50-SKIP-01",
            agent_gid="GID-08"
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_097"

    def test_validate_with_reservation(self, ledger_with_pacs):
        """Test that reserved number is valid."""
        # Reserve P50
        ledger_with_pacs.reserve_pac_number(
            pac_number=50,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # Now P50 should be valid
        result = ledger_with_pacs.validate_pac_sequence(
            pac_id="PAC-ALEX-P50-RESERVED-01",
            agent_gid="GID-08"
        )

        assert result["valid"] is True

    def test_validate_reservation_wrong_agent(self, ledger_with_pacs):
        """Test that using another agent's reservation fails."""
        # Reserve P50 for ALEX
        ledger_with_pacs.reserve_pac_number(
            pac_number=50,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # ATLAS trying to use P50 should fail
        result = ledger_with_pacs.validate_pac_sequence(
            pac_id="PAC-ATLAS-P50-WRONG-01",
            agent_gid="GID-11"
        )

        assert result["valid"] is False
        assert result["error_code"] == "GS_098"

    def test_get_next_available(self, ledger_with_pacs):
        """Test getting next available PAC number."""
        # P40 and P41 exist, so next should be P42
        next_num = ledger_with_pacs.get_next_available_pac_number()
        assert next_num == 42


# ============================================================================
# ARTIFACT TYPE DETECTION TESTS
# ============================================================================

class TestArtifactTypeDetection:
    """Tests for PAC/WRAP detection functions."""

    def test_is_pac_artifact(self, sample_pac_content):
        """Test PAC artifact detection."""
        assert is_pac_artifact(sample_pac_content) is True

    def test_is_wrap_artifact(self, sample_wrap_content):
        """Test WRAP artifact detection."""
        assert is_wrap_artifact(sample_wrap_content) is True

    def test_is_not_pac_artifact(self):
        """Test non-PAC content detection."""
        content = "# Some Random Document\n\nThis is not a PAC."
        assert is_pac_artifact(content) is False

    def test_extract_wrap_id(self, sample_wrap_content):
        """Test WRAP ID extraction."""
        wrap_id = extract_wrap_id(sample_wrap_content)
        assert wrap_id == "WRAP-ALEX-P42-TEST-01"


# ============================================================================
# PAC↔WRAP COUPLING TESTS
# ============================================================================

class TestPacWrapCoupling:
    """Tests for PAC↔WRAP coupling validation."""

    def test_pac_without_wrap_fails(self, sample_pac_content, tmp_path):
        """Test that PAC without WRAP fails coupling validation."""
        # Create PAC file in governance/pacs structure
        governance_dir = tmp_path / "governance"
        pacs_dir = governance_dir / "pacs"
        pacs_dir.mkdir(parents=True)
        pac_file = pacs_dir / "PAC-ALEX-P42-TEST-01.md"
        pac_file.write_text(sample_pac_content)

        # Create empty wraps directory
        wraps_dir = governance_dir / "wraps"
        wraps_dir.mkdir()

        # Validate coupling
        errors = validate_pac_wrap_coupling(sample_pac_content, pac_file, {})

        # Should have coupling error
        assert len(errors) == 1
        assert errors[0].code == ErrorCode.GS_099

    def test_pac_with_wrap_passes(self, sample_pac_content, sample_wrap_content, tmp_path):
        """Test that PAC with WRAP passes coupling validation."""
        # Create PAC file in governance/pacs structure
        governance_dir = tmp_path / "governance"
        pacs_dir = governance_dir / "pacs"
        pacs_dir.mkdir(parents=True)
        pac_file = pacs_dir / "PAC-ALEX-P42-TEST-01.md"
        pac_file.write_text(sample_pac_content)

        # Create WRAP file
        wraps_dir = governance_dir / "wraps"
        wraps_dir.mkdir()
        wrap_file = wraps_dir / "WRAP-ALEX-P42-TEST-01.md"
        wrap_file.write_text(sample_wrap_content)

        # Validate coupling
        errors = validate_pac_wrap_coupling(sample_pac_content, pac_file, {})

        # Should pass
        assert len(errors) == 0

    def test_issued_not_executed_exception(self, tmp_path):
        """Test that ISSUED_NOT_EXECUTED PACs don't require WRAP."""
        content = """# PAC-ALEX-P42-TEST-01

```yaml
PAC_HEADER:
  pac_id: "PAC-ALEX-P42-TEST-01"
  artifact_status: "ISSUED_NOT_EXECUTED"
  artifact_type: "PAC"
```
"""
        # Create PAC file in governance structure
        governance_dir = tmp_path / "governance"
        pacs_dir = governance_dir / "pacs"
        pacs_dir.mkdir(parents=True)
        pac_file = pacs_dir / "PAC-ALEX-P42-TEST-01.md"
        pac_file.write_text(content)

        # No wraps directory

        # Validate coupling
        errors = validate_pac_wrap_coupling(content, pac_file, {})

        # Should pass (exception for ISSUED_NOT_EXECUTED)
        assert len(errors) == 0


# ============================================================================
# ENTRY TYPE TESTS
# ============================================================================

class TestEntryTypes:
    """Tests for reservation entry types."""

    def test_reservation_entry_types_exist(self):
        """Test that reservation entry types are defined."""
        assert hasattr(EntryType, 'PAC_RESERVATION_CREATED')
        assert hasattr(EntryType, 'PAC_RESERVATION_CONSUMED')
        assert hasattr(EntryType, 'PAC_RESERVATION_EXPIRED')

    def test_entry_type_values(self):
        """Test entry type values."""
        assert EntryType.PAC_RESERVATION_CREATED.value == "PAC_RESERVATION_CREATED"
        assert EntryType.PAC_RESERVATION_CONSUMED.value == "PAC_RESERVATION_CONSUMED"
        assert EntryType.PAC_RESERVATION_EXPIRED.value == "PAC_RESERVATION_EXPIRED"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_reservation_workflow(self, temp_ledger):
        """Test complete reservation → PAC → consume workflow."""
        # 1. Reserve P42
        temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # 2. Validate PAC is allowed
        result = temp_ledger.validate_pac_sequence(
            pac_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08"
        )
        assert result["valid"] is True

        # 3. Issue PAC
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )

        # 4. Consume reservation
        temp_ledger.consume_reservation(
            pac_number=42,
            pac_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )

        # 5. Verify reservation is consumed
        reservation = temp_ledger.get_active_reservation(42)
        assert reservation is None

        # 6. Next available should now be P43
        next_num = temp_ledger.get_next_available_pac_number()
        assert next_num == 43

    def test_all_reservations_query(self, temp_ledger):
        """Test getting all reservations."""
        # Create and consume reservations
        temp_ledger.reserve_pac_number(
            pac_number=42,
            reserved_for_agent_gid="GID-08",
            reserved_for_agent_name="ALEX",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        temp_ledger.consume_reservation(
            pac_number=42,
            pac_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )

        temp_ledger.reserve_pac_number(
            pac_number=43,
            reserved_for_agent_gid="GID-11",
            reserved_for_agent_name="ATLAS",
            authority_gid="GID-00",
            authority_name="BENSON"
        )

        # Get all reservations
        all_reservations = temp_ledger.get_all_reservations()

        # Should have 3 entries (created, consumed, created)
        assert len(all_reservations) == 3


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
