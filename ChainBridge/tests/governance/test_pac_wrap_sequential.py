#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
PAC↔WRAP SEQUENTIAL DEPENDENCY TESTS
PAC-ALEX-P43-PAC-WRAP-SEQUENTIAL-GATE-IMPLEMENTATION-01
══════════════════════════════════════════════════════════════════════════════

Tests for:
1. PAC↔WRAP sequential validation (GS_111)
2. First PAC exception (no prior WRAP required)
3. BENSON override capability
4. Ledger-backed enforcement (no filesystem inference)

Authority: ALEX (GID-08)
Mode: FAIL_CLOSED
Pattern: PAC_WRAP_SEQUENTIAL_IS_LAW
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
from tools.governance.gate_pack import (
    validate_pac_sequence_and_reservations,
    is_pac_artifact,
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
def ledger_with_pac_and_wrap(temp_ledger):
    """Ledger with PAC P42 issued and WRAP P42 accepted."""
    # Record PAC P42 issued
    temp_ledger.record_pac_issued(
        artifact_id="PAC-ALEX-P42-TEST-01",
        agent_gid="GID-08",
        agent_name="ALEX"
    )
    # Record WRAP P42 accepted
    temp_ledger.record_wrap_accepted(
        artifact_id="WRAP-ALEX-P42-TEST-01",
        agent_gid="GID-08",
        agent_name="ALEX",
        ratified_by="BENSON (GID-00)"
    )
    return temp_ledger


@pytest.fixture
def ledger_with_pac_no_wrap(temp_ledger):
    """Ledger with PAC P42 issued but NO WRAP accepted."""
    # Record PAC P42 issued
    temp_ledger.record_pac_issued(
        artifact_id="PAC-ALEX-P42-TEST-01",
        agent_gid="GID-08",
        agent_name="ALEX"
    )
    return temp_ledger


@pytest.fixture
def sample_pac_content_p43():
    """Sample PAC content for P43 testing."""
    return """# PAC-ALEX-P43-TEST-01

> **PAC — Test PAC**
> **Agent:** ALEX (GID-08)
> **Color:** ⚪ WHITE

---

## 0. RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "GOVERNANCE"
  mode: "ENFORCEMENT_HARDENING"
  executes_for_agent: "ALEX (GID-08)"
  agent_color: "WHITE"
  status: "ACTIVE"
  fail_closed: true
```

---

## 1. AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "ALEX"
  gid: "GID-08"
  role: "Governance & Alignment Engine"
  color: "WHITE"
  icon: "⚪"
  authority: "GOVERNANCE"
  execution_lane: "GOVERNANCE"
  mode: "EXECUTABLE"
  activation_scope: "EXECUTABLE"
  registry_binding_verified: true
```

---

## 2. PAC_HEADER

```yaml
PAC_HEADER:
  pac_id: "PAC-ALEX-P43-TEST-01"
  agent: "ALEX"
  gid: "GID-08"
  color: "WHITE"
  icon: "⚪"
  authority: "Governance"
  execution_lane: "GOVERNANCE"
  mode: "EXECUTABLE"
  drift_tolerance: "ZERO"
  funnel_stage: "P43"
  governance_mode: "FAIL_CLOSED"
```

---

## 10. TRAINING_SIGNAL

```yaml
TRAINING_SIGNAL:
  signal_type: "TEST"
  pattern: "TEST_PATTERN"
  learning:
    - "Test learning item"
```

---

## 13. FINAL_STATE

```yaml
FINAL_STATE:
  artifact_id: "PAC-ALEX-P43-TEST-01"
  artifact_status: "ISSUED"
  closure_type: "PENDING"
```

---

## 14. FOOTER

```
═══════════════════════════════════════════════════════════════════════════════
PAC-ALEX-P43-TEST-01
⚪ ALEX — Governance & Alignment Engine
═══════════════════════════════════════════════════════════════════════════════
```
"""


@pytest.fixture
def sample_pac_content_p1():
    """Sample PAC content for P1 testing (first PAC)."""
    return """# PAC-ATLAS-P01-TEST-01

> **PAC — Test PAC**
> **Agent:** ATLAS (GID-11)
> **Color:** ⚪ WHITE

---

## 0. RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "GOVERNANCE"
  mode: "ENFORCEMENT_HARDENING"
  executes_for_agent: "ATLAS (GID-11)"
  agent_color: "WHITE"
  status: "ACTIVE"
  fail_closed: true
```

---

## 1. AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "ATLAS"
  gid: "GID-11"
  role: "Test Agent"
  color: "WHITE"
  icon: "⚪"
  authority: "TEST"
  execution_lane: "TEST"
  mode: "EXECUTABLE"
  activation_scope: "EXECUTABLE"
  registry_binding_verified: true
```

---

## 2. PAC_HEADER

```yaml
PAC_HEADER:
  pac_id: "PAC-ATLAS-P01-TEST-01"
  agent: "ATLAS"
  gid: "GID-11"
  color: "WHITE"
  icon: "⚪"
  authority: "Test"
  execution_lane: "TEST"
  mode: "EXECUTABLE"
  drift_tolerance: "ZERO"
  funnel_stage: "P01"
  governance_mode: "FAIL_CLOSED"
```

---

## 10. TRAINING_SIGNAL

```yaml
TRAINING_SIGNAL:
  signal_type: "TEST"
  pattern: "TEST_PATTERN"
  learning:
    - "Test learning item"
```

---

## 13. FINAL_STATE

```yaml
FINAL_STATE:
  artifact_id: "PAC-ATLAS-P01-TEST-01"
  artifact_status: "ISSUED"
  closure_type: "PENDING"
```

---

## 14. FOOTER

```
═══════════════════════════════════════════════════════════════════════════════
PAC-ATLAS-P01-TEST-01
⚪ ATLAS — Test Agent
═══════════════════════════════════════════════════════════════════════════════
```
"""


# ============================================================================
# TEST: validate_pac_wrap_sequential()
# ============================================================================

class TestValidatePacWrapSequential:
    """Tests for ledger-backed PAC↔WRAP sequential validation."""
    
    def test_sequential_valid_when_wrap_accepted(self, ledger_with_pac_and_wrap):
        """PAC P43 should validate when WRAP P42 is accepted."""
        result = ledger_with_pac_and_wrap.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["valid"] is True
        assert result["error_code"] is None
        assert "WRAP P42 is ACCEPTED" in result["message"]
    
    def test_sequential_blocked_when_wrap_missing(self, ledger_with_pac_no_wrap):
        """PAC P43 should be blocked when WRAP P42 is missing."""
        result = ledger_with_pac_no_wrap.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["valid"] is False
        assert result["error_code"] == "GS_111"
        assert "WRAP P42" in result["message"]
        assert result["required_wrap_number"] == 42
    
    def test_first_pac_allowed_without_prior_wrap(self, temp_ledger):
        """First PAC (P1) should be allowed without any prior WRAP."""
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ATLAS-P01-TEST-01",
            agent_gid="GID-11"
        )
        
        assert result["valid"] is True
        assert result["error_code"] is None
        assert "no prior WRAP required" in result["message"]
    
    def test_benson_override_allowed(self, ledger_with_pac_no_wrap):
        """BENSON (GID-00) should bypass sequential check."""
        # Even without WRAP P42, BENSON can issue P43
        result = ledger_with_pac_no_wrap.validate_pac_wrap_sequential(
            pac_id="PAC-BENSON-P43-TEST-01",
            agent_gid="GID-00"
        )
        
        assert result["valid"] is True
        assert result["error_code"] is None
        assert "BENSON" in result["message"]
    
    def test_invalid_pac_id_format(self, temp_ledger):
        """Invalid PAC ID format should return error."""
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="INVALID-ID",
            agent_gid="GID-08"
        )
        
        assert result["valid"] is False
        assert result["error_code"] == "GS_111"
        assert "Cannot extract PAC number" in result["message"]
    
    def test_wrap_from_different_agent_not_counted(self, temp_ledger):
        """WRAP from different agent should not satisfy dependency."""
        # Issue PAC P42 for ALEX
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )
        # Accept WRAP P42 for ATLAS (different agent!)
        temp_ledger.record_wrap_accepted(
            artifact_id="WRAP-ATLAS-P42-TEST-01",
            agent_gid="GID-11",  # ATLAS, not ALEX
            agent_name="ATLAS",
            ratified_by="BENSON (GID-00)"
        )
        
        # ALEX P43 should still be blocked (ALEX's WRAP P42 is missing)
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["valid"] is False
        assert result["error_code"] == "GS_111"
    
    def test_wrap_submitted_not_accepted_not_counted(self, temp_ledger):
        """WRAP_SUBMITTED (not ACCEPTED) should not satisfy dependency."""
        # Issue PAC P42 for ALEX
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )
        # Submit WRAP P42 (not accepted yet)
        temp_ledger.record_wrap_submitted(
            artifact_id="WRAP-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX",
            parent_pac_id="PAC-ALEX-P42-TEST-01"
        )
        
        # P43 should still be blocked
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["valid"] is False
        assert result["error_code"] == "GS_111"


# ============================================================================
# TEST: Integration with gate_pack.py
# ============================================================================

class TestGatePackIntegration:
    """Tests for sequential validation integration with gate_pack.py."""
    
    def test_gate_pack_calls_sequential_validation(
        self, 
        sample_pac_content_p43, 
        ledger_with_pac_no_wrap
    ):
        """gate_pack should call validate_pac_wrap_sequential."""
        # Patch the ledger module to return our test ledger
        with patch('tools.governance.ledger_writer.GovernanceLedger') as MockLedger:
            MockLedger.return_value = ledger_with_pac_no_wrap
            
            registry = {}
            errors = validate_pac_sequence_and_reservations(
                sample_pac_content_p43, 
                registry
            )
            
            # Should have GS_111 error
            gs_111_errors = [e for e in errors if e.code == ErrorCode.GS_111]
            assert len(gs_111_errors) >= 1
    
    def test_gate_pack_passes_when_wrap_accepted(
        self,
        sample_pac_content_p43,
        ledger_with_pac_and_wrap
    ):
        """gate_pack should pass when WRAP is accepted."""
        # Patch the ledger module to return our test ledger  
        with patch('tools.governance.ledger_writer.GovernanceLedger') as MockLedger:
            MockLedger.return_value = ledger_with_pac_and_wrap
            
            registry = {}
            errors = validate_pac_sequence_and_reservations(
                sample_pac_content_p43,
                registry
            )
            
            # Should NOT have GS_111 error for sequential validation
            gs_111_errors = [e for e in errors if e.code == ErrorCode.GS_111]
            # Note: May still have other errors from other validations
            # We're checking that sequential validation specifically passes
            sequential_messages = [
                e for e in gs_111_errors 
                if "sequential" in str(e.message).lower() or "WRAP P42" in str(e.message)
            ]
            assert len(sequential_messages) == 0


# ============================================================================
# TEST: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Edge case tests for PAC↔WRAP sequential validation."""
    
    def test_multiple_wraps_for_same_pac(self, temp_ledger):
        """Multiple WRAP_ACCEPTED entries for same P## should work."""
        # Issue PAC P42
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )
        # Accept WRAP P42 multiple times (edge case)
        for i in range(3):
            temp_ledger.record_wrap_accepted(
                artifact_id=f"WRAP-ALEX-P42-TEST-{i+1:02d}",
                agent_gid="GID-08",
                agent_name="ALEX",
                ratified_by="BENSON (GID-00)"
            )
        
        # P43 should be valid
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["valid"] is True
    
    def test_pac_sequence_gap(self, temp_ledger):
        """PAC P44 should require WRAP P43, not P42."""
        # Issue PAC P42 and accept WRAP P42
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )
        temp_ledger.record_wrap_accepted(
            artifact_id="WRAP-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX",
            ratified_by="BENSON (GID-00)"
        )
        
        # Try to issue P44 (skipping P43)
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P44-TEST-01",
            agent_gid="GID-08"
        )
        
        # Should fail because WRAP P43 is missing
        assert result["valid"] is False
        assert result["required_wrap_number"] == 43
    
    def test_ledger_only_no_filesystem(self, temp_ledger):
        """Validation must only check ledger, not filesystem."""
        # Issue PAC P42, no WRAP
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )
        
        # Even if a WRAP file exists on filesystem, it shouldn't count
        # The validation only checks the ledger
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        # Should fail — no WRAP_ACCEPTED in ledger
        assert result["valid"] is False
        assert result["error_code"] == "GS_111"


# ============================================================================
# TEST: Required WRAP Number Reporting
# ============================================================================

class TestRequiredWrapNumber:
    """Tests for required_wrap_number reporting."""
    
    def test_reports_correct_required_wrap_number(self, temp_ledger):
        """Should report the correct required WRAP number."""
        # Issue PAC P42
        temp_ledger.record_pac_issued(
            artifact_id="PAC-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX"
        )
        
        # Try P43 — requires WRAP P42
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P43-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["required_wrap_number"] == 42
        
        # Accept WRAP P42, try P44 — requires WRAP P43
        temp_ledger.record_wrap_accepted(
            artifact_id="WRAP-ALEX-P42-TEST-01",
            agent_gid="GID-08",
            agent_name="ALEX",
            ratified_by="BENSON (GID-00)"
        )
        
        result = temp_ledger.validate_pac_wrap_sequential(
            pac_id="PAC-ALEX-P44-TEST-01",
            agent_gid="GID-08"
        )
        
        assert result["required_wrap_number"] == 43


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
