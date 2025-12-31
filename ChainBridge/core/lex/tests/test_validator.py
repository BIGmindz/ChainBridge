#!/usr/bin/env python3
"""
Lex Validator Test Suite
========================

Validates the Lex runtime law engine with deterministic enforcement tests.

Usage:
    python -m core.lex.tests.test_validator
"""

import hashlib
import json
import sys
from datetime import datetime, timezone

from core.lex.validator import LexValidator
from core.lex.schema import VerdictStatus, RuleSeverity
from core.lex.rules.signature_rule import SIGNATURE_RULES
from core.lex.rules.hash_rule import HASH_RULES
from core.lex.rules.limit_rule import LIMIT_RULES
from core.lex.rules.jurisdiction_rule import JURISDICTION_RULES
from core.lex.override import OverrideManager, OverrideAuthority


def compute_hash(data: dict) -> str:
    """Helper to compute PDO hash."""
    data_copy = {k: v for k, v in data.items() if k != "hash"}
    return hashlib.sha256(json.dumps(data_copy, sort_keys=True).encode()).hexdigest()


def create_valid_pdo() -> dict:
    """Create a fully valid PDO that passes all rules."""
    pdo = {
        "proof": {
            "type": "execution_proof",
            "hash": "abc123",
            "data": {"gate_results": []},
        },
        "decision": "Execute payment transfer",
        "outcome": "pending",
        "signature": {
            "value": "a" * 64,  # Valid hex signature
            "signer": "agent-cody-01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "signer": "agent-cody-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": "1000.00",
        "source_jurisdiction": "US",
        "destination_jurisdiction": "US",
    }
    # Add valid hash
    pdo["hash"] = compute_hash(pdo)
    return pdo


def test_valid_pdo_approved():
    """Test that a valid PDO is approved."""
    print("\n" + "=" * 70)
    print("TEST: Valid PDO Approved")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    
    # Register only signature and limit rules for this test
    validator.register_rules(SIGNATURE_RULES)
    validator.register_rules(LIMIT_RULES)
    
    pdo = create_valid_pdo()
    
    verdict = validator.validate(pdo)
    
    assert verdict.status == VerdictStatus.APPROVED, f"Expected APPROVED, got {verdict.status.value}"
    assert verdict.is_approved, "Expected is_approved to be True"
    assert not verdict.is_blocked, "Expected is_blocked to be False"
    assert len(verdict.violations) == 0, f"Expected 0 violations, got {len(verdict.violations)}"
    
    print("\n✅ VALID PDO APPROVED TEST PASSED")
    return True


def test_missing_signature_rejected():
    """Test that PDO without signature is rejected."""
    print("\n" + "=" * 70)
    print("TEST: Missing Signature Rejected")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(SIGNATURE_RULES)
    
    pdo = {
        "proof": {"data": {}},
        "decision": "Test",
        "outcome": "pending",
        # No signature!
    }
    
    verdict = validator.validate(pdo)
    
    assert verdict.status == VerdictStatus.REJECTED, f"Expected REJECTED, got {verdict.status.value}"
    assert verdict.is_blocked, "Expected is_blocked to be True"
    assert "LEX-SIG-001" in verdict.blocking_rules, "Expected LEX-SIG-001 in blocking rules"
    
    print("\n✅ MISSING SIGNATURE REJECTED TEST PASSED")
    return True


def test_hash_integrity_failure():
    """Test that tampered PDO is rejected."""
    print("\n" + "=" * 70)
    print("TEST: Hash Integrity Failure")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(HASH_RULES)
    
    pdo = create_valid_pdo()
    # Tamper with the data after hash was computed
    pdo["amount"] = "999999.00"  # Changed!
    
    verdict = validator.validate(pdo)
    
    assert verdict.status == VerdictStatus.REJECTED, f"Expected REJECTED, got {verdict.status.value}"
    assert "LEX-HASH-003" in verdict.blocking_rules, "Expected LEX-HASH-003 (integrity) in blocking rules"
    
    print("\n✅ HASH INTEGRITY FAILURE TEST PASSED")
    return True


def test_limit_exceeded_rejected():
    """Test that amount exceeding limit is rejected."""
    print("\n" + "=" * 70)
    print("TEST: Limit Exceeded Rejected")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(LIMIT_RULES)
    
    pdo = {
        "amount": "50000.00",  # Exceeds default single_tx_limit of 10000
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    verdict = validator.validate(pdo)
    
    assert verdict.is_blocked, "Expected verdict to be blocked"
    assert "LEX-LIM-002" in verdict.blocking_rules, "Expected LEX-LIM-002 (single tx limit) in blocking rules"
    
    print("\n✅ LIMIT EXCEEDED REJECTED TEST PASSED")
    return True


def test_blocked_jurisdiction_rejected():
    """Test that blocked jurisdiction is rejected."""
    print("\n" + "=" * 70)
    print("TEST: Blocked Jurisdiction Rejected")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(JURISDICTION_RULES)
    
    pdo = {
        "source_jurisdiction": "US",
        "destination_jurisdiction": "KP",  # North Korea - blocked
    }
    
    # Disable jurisdiction requirement for non-blocked test
    verdict = validator.validate(pdo, context={"require_jurisdiction": False})
    
    assert verdict.status == VerdictStatus.REJECTED, f"Expected REJECTED, got {verdict.status.value}"
    assert "LEX-JUR-001" in verdict.blocking_rules, "Expected LEX-JUR-001 in blocking rules"
    
    # Verify non-overrideable (CRITICAL)
    violation = next((v for v in verdict.violations if v.rule.rule_id == "LEX-JUR-001"), None)
    assert violation is not None, "Expected LEX-JUR-001 violation"
    assert not violation.rule.override_allowed, "LEX-JUR-001 should not be overrideable"
    
    print("\n✅ BLOCKED JURISDICTION REJECTED TEST PASSED")
    return True


def test_override_workflow():
    """Test the override request and approval workflow."""
    print("\n" + "=" * 70)
    print("TEST: Override Workflow")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(LIMIT_RULES)
    
    # Create PDO that exceeds single tx limit (overrideable)
    pdo = {
        "amount": "15000.00",  # Exceeds 10000 limit
    }
    
    verdict = validator.validate(pdo)
    
    assert verdict.status == VerdictStatus.PENDING_OVERRIDE, f"Expected PENDING_OVERRIDE, got {verdict.status.value}"
    
    # Create override request
    override_mgr = OverrideManager()
    
    request = override_mgr.create_request(
        verdict_id=verdict.verdict_id,
        pdo_hash=verdict.pdo_hash,
        rule_ids=verdict.blocking_rules,
        requester_id="operator-001",
        reason="Approved by business for large payment",
        requires_senior=True,  # LEX-LIM-002 requires senior
    )
    
    print(override_mgr.render_request_terminal(request))
    
    # Approve with senior authority
    approved_request = override_mgr.approve_request(
        request_id=request.request_id,
        approver_id="supervisor-001",
        approver_authority=OverrideAuthority.SENIOR,
    )
    
    print(override_mgr.render_request_terminal(approved_request))
    
    # Apply override to verdict
    overridden_verdict = validator.apply_override(verdict, request.request_id)
    
    assert overridden_verdict.status == VerdictStatus.OVERRIDDEN, f"Expected OVERRIDDEN, got {overridden_verdict.status.value}"
    assert overridden_verdict.is_approved, "Overridden verdict should be approved"
    assert overridden_verdict.override_id == request.request_id, "Override ID mismatch"
    
    # Verify audit trail
    audit_log = override_mgr.get_audit_log(request.request_id)
    assert len(audit_log) == 2, f"Expected 2 audit entries (CREATED, APPROVED), got {len(audit_log)}"
    
    print("\n✅ OVERRIDE WORKFLOW TEST PASSED")
    return True


def test_critical_no_override():
    """Test that CRITICAL violations cannot be overridden."""
    print("\n" + "=" * 70)
    print("TEST: Critical No Override")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(LIMIT_RULES)
    
    # Create PDO that exceeds HARD CAP (critical, no override)
    pdo = {
        "amount": "2000000.00",  # Exceeds 1000000 hard cap
    }
    
    verdict = validator.validate(pdo)
    
    # Should be REJECTED, not PENDING_OVERRIDE
    assert verdict.status == VerdictStatus.REJECTED, f"Expected REJECTED, got {verdict.status.value}"
    assert "LEX-LIM-003" in verdict.blocking_rules, "Expected LEX-LIM-003 (hard cap) in blocking rules"
    
    # Verify the rule is not overrideable
    violation = next((v for v in verdict.violations if v.rule.rule_id == "LEX-LIM-003"), None)
    assert violation is not None, "Expected LEX-LIM-003 violation"
    assert not violation.rule.override_allowed, "LEX-LIM-003 should not be overrideable"
    
    print("\n✅ CRITICAL NO OVERRIDE TEST PASSED")
    return True


def test_all_rules_integrated():
    """Test with all rules integrated."""
    print("\n" + "=" * 70)
    print("TEST: All Rules Integrated")
    print("=" * 70)
    
    validator = LexValidator(terminal_output=True)
    validator.register_rules(SIGNATURE_RULES)
    validator.register_rules(HASH_RULES)
    validator.register_rules(LIMIT_RULES)
    validator.register_rules(JURISDICTION_RULES)
    
    pdo = create_valid_pdo()
    
    context = {
        "require_jurisdiction": True,
    }
    
    verdict = validator.validate(pdo, context)
    
    # Should pass all rules
    assert verdict.status == VerdictStatus.APPROVED, f"Expected APPROVED, got {verdict.status.value}"
    assert len(verdict.rules_evaluated) >= 10, f"Expected at least 10 rules evaluated, got {len(verdict.rules_evaluated)}"
    
    print(f"\nRules Evaluated: {len(verdict.rules_evaluated)}")
    print(f"Rules Passed: {len(verdict.rules_passed)}")
    
    print("\n✅ ALL RULES INTEGRATED TEST PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "═" * 70)
    print("🟥🟥🟥 LEX VALIDATOR TEST SUITE 🟥🟥🟥")
    print("═" * 70)
    
    tests = [
        ("Valid PDO Approved", test_valid_pdo_approved),
        ("Missing Signature Rejected", test_missing_signature_rejected),
        ("Hash Integrity Failure", test_hash_integrity_failure),
        ("Limit Exceeded Rejected", test_limit_exceeded_rejected),
        ("Blocked Jurisdiction Rejected", test_blocked_jurisdiction_rejected),
        ("Override Workflow", test_override_workflow),
        ("Critical No Override", test_critical_no_override),
        ("All Rules Integrated", test_all_rules_integrated),
    ]
    
    results = []
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ {name} FAILED: {e}")
    
    # Summary
    print("\n" + "═" * 70)
    print("TEST SUMMARY")
    print("═" * 70)
    
    passed = sum(1 for _, r, _ in results if r)
    failed = len(results) - passed
    
    for name, result, error in results:
        icon = "✅" if result else "❌"
        status = "PASS" if result else f"FAIL: {error}"
        print(f"  {icon} {name}: {status}")
    
    print("─" * 70)
    print(f"  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("═" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
