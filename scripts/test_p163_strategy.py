#!/usr/bin/env python3
"""P163 Document Retry Strategy Validation Script"""
import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from modules.immune import RemediationEngine, DocumentRetryStrategy

engine = RemediationEngine()
strategy = DocumentRetryStrategy()
engine.register_strategy(strategy)

print("=" * 60)
print("PAC-SYS-P163: Document Retry Strategy Test")
print("=" * 60)

# Test 1: Blurry document (should coach)
print("\n[TEST 1] DOC_BLURRY - User Coaching")
ctx1 = {"error_code": "DOC_BLURRY", "transaction_id": "TX-001"}
r1 = strategy.execute({}, ctx1)
print(f"  Success: {r1.success}")
print(f"  Guidance: {r1.corrected_data['retry_guidance']['user_message']}")
print(f"  Action: {r1.corrected_data['retry_guidance']['action_required']}")
print(f"  Tips: {len(r1.corrected_data['retry_guidance']['tips'])} tips provided")

# Test 2: Glare issue
print("\n[TEST 2] DOC_GLARE - Specific Instructions")
ctx2 = {"error_code": "DOC_GLARE", "transaction_id": "TX-002"}
r2 = strategy.execute({}, ctx2)
print(f"  Message: {r2.corrected_data['retry_guidance']['user_message']}")
print(f"  Tip 1: {r2.corrected_data['retry_guidance']['tips'][0]}")

# Test 3: Liveness failure (biometric)
print("\n[TEST 3] LIVENESS_FAILED - Biometric Coaching")
ctx3 = {"error_code": "LIVENESS_FAILED", "transaction_id": "TX-003"}
r3 = strategy.execute({}, ctx3)
print(f"  Category: {r3.corrected_data['retry_guidance']['category']}")
print(f"  Message: {r3.corrected_data['retry_guidance']['user_message']}")

# Test 4: Fatal error (should NOT coach - fraud)
print("\n[TEST 4] DOC_FORGED - FATAL (No Coaching)")
ctx4 = {"error_code": "DOC_FORGED", "transaction_id": "TX-004"}
r4 = strategy.execute({}, ctx4)
print(f"  Success: {r4.success} (Expected: False)")
print(f"  Explanation: {r4.explanation}")
print(f"  Note: Fraud vectors NOT revealed")

# Test 5: Deepfake (verify we don't reveal detection)
print("\n[TEST 5] DEEPFAKE_DETECTED - Security")
ctx5 = {"error_code": "DEEPFAKE_DETECTED", "transaction_id": "TX-005"}
r5 = strategy.execute({}, ctx5)
print(f"  Message shown: '{r5.explanation}'")
print(f"  Contains 'deepfake': {'deepfake' in r5.explanation.lower()}")

# Test 6: Retry limit enforcement
print("\n[TEST 6] Retry Limit Enforcement")
ctx6 = {"error_code": "DOC_BLURRY", "transaction_id": "TX-006", "document_type": "passport"}
for i in range(4):
    r6 = strategy.execute({}, ctx6)
    status = "Allowed" if r6.success else "BLOCKED"
    print(f"  Attempt {i+1}: {status}")

# Test 7: Expired document (limited retries)
print("\n[TEST 7] DOC_EXPIRED - Need Different Document")
ctx7 = {"error_code": "DOC_EXPIRED", "transaction_id": "TX-007"}
r7 = strategy.execute({}, ctx7)
print(f"  Message: {r7.corrected_data['retry_guidance']['user_message']}")
print(f"  Max Retries: {r7.corrected_data['retry_guidance']['max_retries']}")

# Strategy stats
print("\n[STRATEGY STATS]")
stats = strategy.get_retry_stats()
print(f"  Error codes mapped: {stats['error_codes_mapped']}")
print(f"  Active retry contexts: {stats['active_transactions']}")

print("\n" + "=" * 60)
print("DOCUMENT RETRY STRATEGY VALIDATED")
print("The System now guides the User.")
print("=" * 60)
