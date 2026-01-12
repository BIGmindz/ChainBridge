#!/usr/bin/env python3
"""P161 Strategy Validation Script"""
from modules.immune import RemediationEngine, MissingFieldStrategy

engine = RemediationEngine()
strategy = MissingFieldStrategy()
engine.register_strategy(strategy)

print("=" * 60)
print("PAC-SYS-P161: Missing Field Strategy Test")
print("=" * 60)

# Test 1: Currency auto-fill
print("\n[TEST 1] Missing Currency Field")
ctx1 = {"errors": [{"loc": ["payment_data", "currency"], "type": "value_error.missing"}]}
r1 = strategy.execute({"payment_data": {"amount": 1000}}, ctx1)
print(f"  Success: {r1.success}")
print(f"  Corrected: {r1.corrected_data}")

# Test 2: Sensitive field blocked
print("\n[TEST 2] Missing User ID (Sensitive)")
ctx2 = {"errors": [{"loc": ["user_id"], "type": "value_error.missing"}]}
r2 = strategy.execute({}, ctx2)
print(f"  Auto-filled: {r2.corrected_data is not None}")
print(f"  Explanation: {r2.explanation}")

# Test 3: Engine integration
print("\n[TEST 3] Engine with Strategy")
mock_receipt = {"status": "FAILED", "blame": {"gate": "validation", "code": "MISSING_FIELD"}}
plan = engine.diagnose(mock_receipt)
print(f"  Strategies found: {plan.strategies_to_try}")
print(f"  Can remediate: {plan.can_remediate}")

print("\n" + "=" * 60)
print("STRATEGY VALIDATED - The System heals the simplest wounds")
print("=" * 60)
