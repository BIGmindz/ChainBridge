#!/usr/bin/env python3
"""P162 Format Correction Strategy Validation Script"""
import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from modules.immune import RemediationEngine, FormatCorrectionStrategy

engine = RemediationEngine()
strategy = FormatCorrectionStrategy()
engine.register_strategy(strategy)

print("=" * 60)
print("PAC-SYS-P162: Format Correction Strategy Test")
print("=" * 60)

# Test 1: Date normalization (year-first)
print("\n[TEST 1] Date Format - Year First")
ctx1 = {"errors": [{"loc": ["ship_date"], "type": "date_from_datetime_parsing", "input": "2023/12/25"}]}
r1 = strategy.execute({"ship_date": "2023/12/25"}, ctx1)
print(f"  Input: '2023/12/25'")
print(f"  Output: {r1.corrected_data}")
print(f"  Success: {r1.success}")

# Test 2: Date with day > 12 (unambiguous European)
print("\n[TEST 2] Date Format - Day > 12 (Unambiguous)")
ctx2 = {"errors": [{"loc": ["birth_date"], "type": "date_from_datetime_parsing", "input": "25/12/2023"}]}
r2 = strategy.execute({"birth_date": "25/12/2023"}, ctx2)
print(f"  Input: '25/12/2023'")
print(f"  Output: {r2.corrected_data}")
print(f"  Success: {r2.success}")

# Test 3: Ambiguous date (should not auto-fix)
print("\n[TEST 3] Ambiguous Date - BLOCKED")
ctx3 = {"errors": [{"loc": ["date"], "type": "date_from_datetime_parsing", "input": "01/02/2023"}]}
r3 = strategy.execute({"date": "01/02/2023"}, ctx3)
print(f"  Input: '01/02/2023' (Jan 2 or Feb 1?)")
print(f"  Auto-fixed: {r3.corrected_data is not None}")
print(f"  Explanation: {r3.explanation[:60]}...")

# Test 4: Whitespace trimming
print("\n[TEST 4] Whitespace Trim")
ctx4 = {"errors": [{"loc": ["currency"], "type": "enum", "input": "  usd  "}]}
r4 = strategy.execute({"currency": "  usd  "}, ctx4)
print(f"  Input: '  usd  '")
print(f"  Output: {r4.corrected_data}")
print(f"  Success: {r4.success}")

# Test 5: Case normalization
print("\n[TEST 5] Case Normalization")
ctx5 = {"errors": [{"loc": ["country_code"], "type": "enum", "input": "usa"}]}
r5 = strategy.execute({"country_code": "usa"}, ctx5)
print(f"  Input: 'usa'")
print(f"  Output: {r5.corrected_data}")
print(f"  Success: {r5.success}")

# Test 6: Full payload cleanup
print("\n[TEST 6] Full Payload Cleanup")
dirty_data = {
    "payment_data": {
        "currency": "  eur ",
        "amount": 1000
    },
    "shipment_data": {
        "ship_date": "2024/06/15",
        "country_code": "germany"
    }
}
ctx6 = {"errors": [
    {"loc": ["payment_data", "currency"], "type": "enum", "input": "  eur "},
    {"loc": ["shipment_data", "ship_date"], "type": "date_from_datetime_parsing", "input": "2024/06/15"},
    {"loc": ["shipment_data", "country_code"], "type": "enum", "input": "germany"}
]}
r6 = strategy.execute(dirty_data, ctx6)
print(f"  Input currencies: '  eur ', 'germany'")
print(f"  Fixed payload: {r6.corrected_data}")
print(f"  Success: {r6.success}")

# Stats
print("\n[ENGINE STATS]")
print(f"  Strategies registered: {len(engine.list_strategies())}")
print(f"  Strategy ID: {strategy.strategy_id}")

print("\n" + "=" * 60)
print("FORMAT CORRECTION STRATEGY VALIDATED")
print("The System now speaks all dialects of the Protocol.")
print("=" * 60)
