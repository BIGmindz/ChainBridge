#!/usr/bin/env python3
"""
PAC-FIN-P201 Validation Script
==============================

Tests the Settlement Engine for:
1. Create Intent
2. Authorization (Hold funds)
3. Capture (Execute transfer)
4. Idempotency (INV-FIN-003)
5. Lifecycle Safety (INV-FIN-004)
6. Void/Cancel flow
7. Insufficient funds handling
8. Duplicate capture protection
9. Amount exceeds authorization

PAC: PAC-FIN-P201-SETTLEMENT-ENGINE
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from decimal import Decimal
from modules.finance import (
    Ledger, AccountType,
    SettlementEngine, IntentStatus,
    IdempotencyViolationError, LifecycleViolationError,
    AmountExceedsAuthorizationError, InsufficientFundsError,
)


def run_tests():
    print("=" * 60)
    print("PAC-FIN-P201: SETTLEMENT ENGINE VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    
    # Setup: Create ledger and fund accounts
    ledger = Ledger(ledger_id="SETTLEMENT-TEST-001")
    engine = SettlementEngine(ledger)
    
    # Create test accounts
    ledger.create_account(
        account_id="MERCHANT-001",
        name="Merchant Account",
        account_type=AccountType.ASSET,
    )
    ledger.create_account(
        account_id="CUSTOMER-001",
        name="Customer Account",
        account_type=AccountType.ASSET,
    )
    ledger.create_account(
        account_id="PLATFORM-FEES",
        name="Platform Fees",
        account_type=AccountType.FEE_REVENUE,
    )
    
    # Fund source (customer) account
    funding = ledger.create_account(
        account_id="FUNDING",
        name="Funding Source",
        account_type=AccountType.LIABILITY,
        allow_negative=True,
    )
    ledger.transfer("FUNDING", "CUSTOMER-001", Decimal("5000.00"), "Initial funding")
    
    print(f"Setup: Customer funded with $5000.00")
    print()
    
    # =========================================================================
    # TEST 1: Create Intent
    # =========================================================================
    print("TEST 1: Create Payment Intent")
    try:
        intent = engine.create_intent(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("100.00"),
            idempotency_key="ORDER-001",
            description="Payment for Order #001",
        )
        
        assert intent.status == IntentStatus.CREATED
        assert intent.amount == Decimal("100.00")
        assert intent.idempotency_key == "ORDER-001"
        
        print(f"   ✅ PASS: Intent created - {intent.intent_id[:8]}...")
        print(f"      Status: {intent.status.value}")
        results.append(("Create Intent", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Create Intent", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 2: Authorize (Hold Funds)
    # =========================================================================
    print("TEST 2: Authorize (Hold Funds)")
    try:
        customer_before = ledger.get_balance("CUSTOMER-001")
        escrow_before = ledger.get_balance("SYSTEM-ESCROW-001")
        
        intent = engine.authorize(intent.intent_id)
        
        customer_after = ledger.get_balance("CUSTOMER-001")
        escrow_after = ledger.get_balance("SYSTEM-ESCROW-001")
        
        assert intent.status == IntentStatus.AUTHORIZED
        assert intent.hold_transaction_id is not None
        assert customer_after == customer_before - Decimal("100.00")
        assert escrow_after == escrow_before + Decimal("100.00")
        
        print(f"   ✅ PASS: Authorization successful")
        print(f"      Customer: ${customer_before} → ${customer_after}")
        print(f"      Escrow: ${escrow_before} → ${escrow_after}")
        results.append(("Authorize", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Authorize", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 3: Capture (Execute Transfer)
    # =========================================================================
    print("TEST 3: Capture (Execute Transfer)")
    try:
        escrow_before = ledger.get_balance("SYSTEM-ESCROW-001")
        merchant_before = ledger.get_balance("MERCHANT-001")
        
        intent = engine.capture(intent.intent_id)
        
        escrow_after = ledger.get_balance("SYSTEM-ESCROW-001")
        merchant_after = ledger.get_balance("MERCHANT-001")
        
        assert intent.status == IntentStatus.CAPTURED
        assert intent.capture_transaction_id is not None
        assert escrow_after == escrow_before - Decimal("100.00")
        assert merchant_after == merchant_before + Decimal("100.00")
        
        print(f"   ✅ PASS: Capture successful")
        print(f"      Escrow: ${escrow_before} → ${escrow_after}")
        print(f"      Merchant: ${merchant_before} → ${merchant_after}")
        results.append(("Capture", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Capture", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 4: Idempotency - Same Key Returns Same Intent (INV-FIN-003)
    # =========================================================================
    print("TEST 4: Idempotency - Replay Returns Same Intent (INV-FIN-003)")
    try:
        # Try to create with same idempotency key
        replay_intent = engine.create_intent(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("100.00"),
            idempotency_key="ORDER-001",  # Same key!
        )
        
        assert replay_intent.intent_id == intent.intent_id
        assert replay_intent.status == IntentStatus.CAPTURED
        
        print(f"   ✅ PASS: Idempotent replay returned same intent")
        print(f"      Original: {intent.intent_id[:8]}...")
        print(f"      Replay: {replay_intent.intent_id[:8]}...")
        results.append(("Idempotency (Same Params)", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Idempotency (Same Params)", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 5: Idempotency Violation - Different Params (INV-FIN-003)
    # =========================================================================
    print("TEST 5: Idempotency Violation - Different Params (INV-FIN-003)")
    try:
        try:
            engine.create_intent(
                source_account="CUSTOMER-001",
                destination_account="MERCHANT-001",
                amount=Decimal("200.00"),  # Different amount!
                idempotency_key="ORDER-001",  # Same key!
            )
            print(f"   ❌ FAIL: Should have raised IdempotencyViolationError")
            results.append(("Idempotency Violation", "FAIL"))
        except IdempotencyViolationError as e:
            print(f"   ✅ PASS: Idempotency violation detected")
            print(f"      Key: {e.idempotency_key}")
            results.append(("Idempotency Violation", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Idempotency Violation", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 6: Lifecycle Safety - Capture Without Auth (INV-FIN-004)
    # =========================================================================
    print("TEST 6: Lifecycle Safety - Capture Without Auth (INV-FIN-004)")
    try:
        new_intent = engine.create_intent(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("50.00"),
            idempotency_key="ORDER-002",
        )
        
        try:
            engine.capture(new_intent.intent_id)  # Skip authorization!
            print(f"   ❌ FAIL: Should have raised LifecycleViolationError")
            results.append(("Lifecycle Safety", "FAIL"))
        except LifecycleViolationError as e:
            print(f"   ✅ PASS: Lifecycle violation detected")
            print(f"      Attempted: {e.attempted_action} on {e.current_state}")
            results.append(("Lifecycle Safety", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Lifecycle Safety", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 7: Void/Cancel Flow
    # =========================================================================
    print("TEST 7: Void/Cancel Flow")
    try:
        # First authorize
        engine.authorize(new_intent.intent_id)
        
        customer_before = ledger.get_balance("CUSTOMER-001")
        escrow_before = ledger.get_balance("SYSTEM-ESCROW-001")
        
        # Then void
        voided = engine.void(new_intent.intent_id, reason="Customer cancelled")
        
        customer_after = ledger.get_balance("CUSTOMER-001")
        escrow_after = ledger.get_balance("SYSTEM-ESCROW-001")
        
        assert voided.status == IntentStatus.VOIDED
        assert voided.void_reason == "Customer cancelled"
        assert customer_after == customer_before + Decimal("50.00")
        assert escrow_after == escrow_before - Decimal("50.00")
        
        print(f"   ✅ PASS: Void successful - funds released")
        print(f"      Customer: ${customer_before} → ${customer_after}")
        results.append(("Void/Cancel", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Void/Cancel", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 8: Insufficient Funds
    # =========================================================================
    print("TEST 8: Insufficient Funds Protection")
    try:
        big_intent = engine.create_intent(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("99999.00"),  # More than customer has
            idempotency_key="ORDER-003",
        )
        
        try:
            engine.authorize(big_intent.intent_id)
            print(f"   ❌ FAIL: Should have raised InsufficientFundsError")
            results.append(("Insufficient Funds", "FAIL"))
        except InsufficientFundsError as e:
            assert big_intent.status == IntentStatus.FAILED
            print(f"   ✅ PASS: Insufficient funds detected")
            print(f"      Required: ${e.required}, Available: ${e.available}")
            results.append(("Insufficient Funds", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Insufficient Funds", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 9: Duplicate Capture (Idempotency)
    # =========================================================================
    print("TEST 9: Duplicate Capture (Idempotency)")
    try:
        # Create and complete a new payment
        dup_intent = engine.create_intent(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("75.00"),
            idempotency_key="ORDER-004",
        )
        engine.authorize(dup_intent.intent_id)
        engine.capture(dup_intent.intent_id)
        
        merchant_before = ledger.get_balance("MERCHANT-001")
        
        # Try to capture again
        replay = engine.capture(dup_intent.intent_id)
        
        merchant_after = ledger.get_balance("MERCHANT-001")
        
        # Balance should NOT change (idempotent)
        assert merchant_after == merchant_before
        assert replay.status == IntentStatus.CAPTURED
        
        print(f"   ✅ PASS: Duplicate capture returned same result, no side effects")
        print(f"      Merchant balance unchanged: ${merchant_after}")
        results.append(("Duplicate Capture", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Duplicate Capture", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 10: Amount Exceeds Authorization
    # =========================================================================
    print("TEST 10: Capture Amount Exceeds Authorization")
    try:
        partial_intent = engine.create_intent(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("100.00"),
            idempotency_key="ORDER-005",
        )
        engine.authorize(partial_intent.intent_id)
        
        try:
            engine.capture(partial_intent.intent_id, amount=Decimal("150.00"))  # More than authorized!
            print(f"   ❌ FAIL: Should have raised AmountExceedsAuthorizationError")
            results.append(("Amount Exceeds Auth", "FAIL"))
        except AmountExceedsAuthorizationError as e:
            print(f"   ✅ PASS: Over-capture prevented")
            print(f"      Authorized: ${e.authorized}, Requested: ${e.requested}")
            results.append(("Amount Exceeds Auth", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Amount Exceeds Auth", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 11: Authorize-and-Capture Convenience Method
    # =========================================================================
    print("TEST 11: Authorize-and-Capture Convenience")
    try:
        customer_before = ledger.get_balance("CUSTOMER-001")
        merchant_before = ledger.get_balance("MERCHANT-001")
        
        quick_intent = engine.authorize_and_capture(
            source_account="CUSTOMER-001",
            destination_account="MERCHANT-001",
            amount=Decimal("25.00"),
            idempotency_key="QUICK-001",
            description="Quick payment",
        )
        
        customer_after = ledger.get_balance("CUSTOMER-001")
        merchant_after = ledger.get_balance("MERCHANT-001")
        
        assert quick_intent.status == IntentStatus.CAPTURED
        assert customer_after == customer_before - Decimal("25.00")
        assert merchant_after == merchant_before + Decimal("25.00")
        
        print(f"   ✅ PASS: Single-call payment completed")
        print(f"      Customer: ${customer_before} → ${customer_after}")
        print(f"      Merchant: ${merchant_before} → ${merchant_after}")
        results.append(("Auth-and-Capture", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Auth-and-Capture", "FAIL"))
    print()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    total = len(results)
    
    for test_name, status in results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"   {icon} {test_name}: {status}")
    
    print()
    print(f"RESULT: {passed}/{total} tests passed")
    print()
    
    # Print metrics
    print("SETTLEMENT METRICS:")
    metrics = engine.get_metrics()
    print(f"   Total Intents: {metrics['total_intents']}")
    print(f"   By Status: {metrics['by_status']}")
    print(f"   Total Authorized: ${metrics['total_authorized']}")
    print(f"   Total Captured: ${metrics['total_captured']}")
    print(f"   Total Voided: ${metrics['total_voided']}")
    print(f"   Escrow Balance: ${metrics['escrow_balance']}")
    
    if passed == total:
        print()
        print("🎉 SETTLEMENT ENGINE VALIDATED SUCCESSFULLY")
        print("   INV-FIN-003 (Idempotency): ENFORCED")
        print("   INV-FIN-004 (Lifecycle Safety): ENFORCED")
        return 0
    else:
        print()
        print("⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
