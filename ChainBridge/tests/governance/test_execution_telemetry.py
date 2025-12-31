#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TEST: BENSON EXECUTION TELEMETRY
PAC-DAN-P53-LIVE-GOVERNANCE-EXECUTION-TELEMETRY-01
═══════════════════════════════════════════════════════════════════════════════

Unit tests validating that structured telemetry is emitted correctly
during Benson Execution runtime operations.

Authority: Dan (GID-07)
Lane: DEVOPS
Mode: FAIL_CLOSED
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add governance tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "governance"))

from benson_execution import (
    TelemetryLogger,
    BensonExecutionEngine,
    ExecutionResult,
    get_telemetry,
)


# ════════════════════════════════════════════════════════════════════════════
# TEST: TELEMETRY LOGGER BASIC FUNCTIONALITY
# ════════════════════════════════════════════════════════════════════════════

def test_telemetry_logger_initialization():
    """Test that TelemetryLogger initializes correctly."""
    logger = TelemetryLogger(enable_stdout=False)
    assert logger is not None
    assert logger.enable_stdout is False
    assert logger._events == []


def test_telemetry_emit_event():
    """Test that emit() creates properly structured event."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.emit("TEST_EVENT", {"key": "value"})
    
    assert event["event_type"] == "TEST_EVENT"
    assert event["telemetry_version"] == "1.0.0"
    assert event["authority"] == "BENSON (GID-00)"
    assert event["data"]["key"] == "value"
    assert "timestamp" in event


def test_telemetry_pac_dispatch_start():
    """Test PAC dispatch start telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.pac_dispatch_start("PAC-TEST-01", "GID-07", "Dan")
    
    assert event["event_type"] == "PAC_DISPATCH_START"
    assert event["data"]["pac_id"] == "PAC-TEST-01"
    assert event["data"]["agent_gid"] == "GID-07"
    assert event["data"]["agent_name"] == "Dan"
    assert event["data"]["phase"] == "DISPATCH"


def test_telemetry_pac_dispatch_end():
    """Test PAC dispatch end telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.pac_dispatch_end("PAC-TEST-01", "COMPLETED", 5000)
    
    assert event["event_type"] == "PAC_DISPATCH_END"
    assert event["data"]["pac_id"] == "PAC-TEST-01"
    assert event["data"]["status"] == "COMPLETED"
    assert event["data"]["duration_ms"] == 5000


def test_telemetry_agent_execution_start():
    """Test agent execution start telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.agent_execution_start("PAC-TEST-01", "GID-07")
    
    assert event["event_type"] == "AGENT_EXECUTION_START"
    assert event["data"]["phase"] == "EXECUTION"


def test_telemetry_agent_execution_end():
    """Test agent execution end telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.agent_execution_end(
        pac_id="PAC-TEST-01",
        agent_gid="GID-07",
        status="COMPLETED",
        tasks_completed=5,
        quality_score=1.0
    )
    
    assert event["event_type"] == "AGENT_EXECUTION_END"
    assert event["data"]["tasks_completed"] == 5
    assert event["data"]["quality_score"] == 1.0


def test_telemetry_schema_validation():
    """Test schema validation telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.schema_validation(
        pac_id="PAC-TEST-01",
        schema_type="AgentExecutionResult",
        valid=True,
        error_code=None
    )
    
    assert event["event_type"] == "SCHEMA_VALIDATION"
    assert event["data"]["valid"] is True
    assert event["data"]["schema_type"] == "AgentExecutionResult"


def test_telemetry_schema_validation_failure():
    """Test schema validation telemetry on failure."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.schema_validation(
        pac_id="PAC-TEST-01",
        schema_type="AgentExecutionResult",
        valid=False,
        error_code="GS_130"
    )
    
    assert event["event_type"] == "SCHEMA_VALIDATION"
    assert event["data"]["valid"] is False
    assert event["data"]["error_code"] == "GS_130"


def test_telemetry_ber_generation_decision():
    """Test BER generation decision telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.ber_generation_decision(
        pac_id="PAC-TEST-01",
        eligible=True,
        reason="All checkpoints passed",
        human_review_required=True
    )
    
    assert event["event_type"] == "BER_GENERATION_DECISION"
    assert event["data"]["eligible"] is True
    assert event["data"]["human_review_required"] is True


def test_telemetry_wrap_generation():
    """Test WRAP generation telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.wrap_generation(
        pac_id="PAC-TEST-01",
        wrap_id="WRAP-TEST-01",
        status="WRAP_GENERATED",
        blocked=False
    )
    
    assert event["event_type"] == "WRAP_GENERATION"
    assert event["data"]["wrap_id"] == "WRAP-TEST-01"
    assert event["data"]["blocked"] is False


def test_telemetry_checkpoint():
    """Test checkpoint telemetry."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.checkpoint(
        checkpoint_id="CP-01",
        checkpoint_name="AGENT_ACTIVATION",
        status="PASS",
        details="Agent activated successfully"
    )
    
    assert event["event_type"] == "CHECKPOINT"
    assert event["data"]["checkpoint_id"] == "CP-01"
    assert event["data"]["status"] == "PASS"


def test_telemetry_get_all_events():
    """Test that all events are collected."""
    logger = TelemetryLogger(enable_stdout=False)
    logger.emit("EVENT_1", {})
    logger.emit("EVENT_2", {})
    logger.emit("EVENT_3", {})
    
    events = logger.get_all_events()
    assert len(events) == 3


def test_telemetry_get_summary():
    """Test telemetry summary generation."""
    logger = TelemetryLogger(enable_stdout=False)
    logger.emit("EVENT_A", {})
    logger.emit("EVENT_B", {})
    logger.emit("EVENT_A", {})
    
    summary = logger.get_telemetry_summary()
    assert summary["total_events"] == 3
    assert "EVENT_A" in summary["event_types"]
    assert "EVENT_B" in summary["event_types"]


# ════════════════════════════════════════════════════════════════════════════
# TEST: BENSON EXECUTION ENGINE TELEMETRY INTEGRATION
# ════════════════════════════════════════════════════════════════════════════

def test_engine_has_telemetry():
    """Test that BensonExecutionEngine has telemetry logger."""
    engine = BensonExecutionEngine(enable_telemetry=False)
    assert hasattr(engine, "telemetry")
    assert isinstance(engine.telemetry, TelemetryLogger)


def test_engine_version_updated():
    """Test that engine version reflects telemetry integration."""
    engine = BensonExecutionEngine(enable_telemetry=False)
    # Version should be 1.2.0 or higher (P53 update)
    version_parts = engine.VERSION.split(".")
    assert int(version_parts[0]) >= 1
    assert int(version_parts[1]) >= 2


def test_engine_schema_validation_emits_telemetry():
    """Test that schema validation emits telemetry."""
    engine = BensonExecutionEngine(enable_telemetry=False)
    
    # Valid execution result
    result = {
        "pac_id": "PAC-TEST-01",
        "agent_gid": "GID-07",
        "agent_name": "Dan",
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks_completed": ["T1"],
        "tasks_total": 1,
        "files_modified": [],
        "quality_score": 1.0,
        "scope_compliance": True,
        "execution_time_ms": 1000,
    }
    
    # Validate (this should emit telemetry)
    validation = engine.validate_execution_result_schema(result)
    
    # Check telemetry was emitted
    events = engine.telemetry.get_all_events()
    schema_events = [e for e in events if e["event_type"] == "SCHEMA_VALIDATION"]
    assert len(schema_events) >= 1
    assert schema_events[0]["data"]["valid"] is True


def test_engine_get_telemetry_for_ber():
    """Test that engine can provide telemetry for BER."""
    engine = BensonExecutionEngine(enable_telemetry=False)
    
    # Emit some test events
    engine.telemetry.emit("TEST_EVENT", {})
    
    # Get telemetry for BER
    ber_telemetry = engine.get_telemetry_for_ber()
    
    assert "telemetry_version" in ber_telemetry
    assert "summary" in ber_telemetry
    assert "events" in ber_telemetry
    assert ber_telemetry["telemetry_version"] == "1.0.0"


# ════════════════════════════════════════════════════════════════════════════
# TEST: FAIL_CLOSED BEHAVIOR
# ════════════════════════════════════════════════════════════════════════════

def test_telemetry_required_fields():
    """Test that telemetry events have all required fields."""
    logger = TelemetryLogger(enable_stdout=False)
    event = logger.emit("TEST", {"test": True})
    
    required_fields = ["telemetry_version", "timestamp", "event_type", "authority", "data"]
    for field in required_fields:
        assert field in event, f"Missing required field: {field}"


def test_telemetry_authority_always_benson():
    """Test that telemetry authority is always BENSON (GID-00)."""
    logger = TelemetryLogger(enable_stdout=False)
    
    # Multiple events
    events = [
        logger.pac_dispatch_start("PAC-1", "GID-07", "Dan"),
        logger.agent_execution_start("PAC-1", "GID-07"),
        logger.schema_validation("PAC-1", "Test", True),
    ]
    
    for event in events:
        assert event["authority"] == "BENSON (GID-00)"


# ════════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ════════════════════════════════════════════════════════════════════════════

def run_all_tests():
    """Run all telemetry tests and report results."""
    tests = [
        test_telemetry_logger_initialization,
        test_telemetry_emit_event,
        test_telemetry_pac_dispatch_start,
        test_telemetry_pac_dispatch_end,
        test_telemetry_agent_execution_start,
        test_telemetry_agent_execution_end,
        test_telemetry_schema_validation,
        test_telemetry_schema_validation_failure,
        test_telemetry_ber_generation_decision,
        test_telemetry_wrap_generation,
        test_telemetry_checkpoint,
        test_telemetry_get_all_events,
        test_telemetry_get_summary,
        test_engine_has_telemetry,
        test_engine_version_updated,
        test_engine_schema_validation_emits_telemetry,
        test_engine_get_telemetry_for_ber,
        test_telemetry_required_fields,
        test_telemetry_authority_always_benson,
    ]
    
    passed = 0
    failed = 0
    
    print("═" * 80)
    print("🧪 TEST SUITE: BENSON EXECUTION TELEMETRY (PAC-DAN-P53)")
    print("═" * 80)
    print()
    
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: EXCEPTION - {e}")
            failed += 1
    
    print()
    print("═" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("═" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
