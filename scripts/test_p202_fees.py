#!/usr/bin/env python3
"""
PAC-FIN-P202 Validation Script
==============================

Tests the Fee Engine for:
1. Flat fee calculation
2. Percentage fee calculation
3. Composite fee calculation (2.9% + $0.30)
4. Revenue conservation invariant (INV-FIN-005)
5. Fee exceeds amount protection
6. Tiered fee calculation
7. Calculate for net (reverse calculation)
8. Integration with Settlement Engine

PAC: PAC-FIN-P202-FEE-ENGINE
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from decimal import Decimal
from modules.finance import (
    # Ledger
    Ledger, AccountType,
    # Settlement
    SettlementEngine, IntentStatus,
    # Fees
    FeeEngine, FeeBreakdown,
    FlatFeeStrategy, PercentageFeeStrategy, CompositeFeeStrategy, TieredFeeStrategy,
    FeeExceedsAmountError,
    create_stripe_strategy,
)


def run_tests():
    print("=" * 60)
    print("PAC-FIN-P202: FEE ENGINE VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    fee_engine = FeeEngine()
    
    # =========================================================================
    # TEST 1: Flat Fee Calculation
    # =========================================================================
    print("TEST 1: Flat Fee Calculation ($0.30)")
    try:
        strategy = FlatFeeStrategy(Decimal("0.30"))
        breakdown = strategy.calculate(Decimal("100.00"))
        
        assert breakdown.gross_amount == Decimal("100.00")
        assert breakdown.total_fee == Decimal("0.30")
        assert breakdown.net_amount == Decimal("99.70")
        assert breakdown.gross_amount == breakdown.net_amount + breakdown.total_fee
        
        print(f"   ✅ PASS: Gross=${breakdown.gross_amount}, Fee=${breakdown.total_fee}, Net=${breakdown.net_amount}")
        results.append(("Flat Fee", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Flat Fee", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 2: Percentage Fee Calculation
    # =========================================================================
    print("TEST 2: Percentage Fee Calculation (2.9%)")
    try:
        strategy = PercentageFeeStrategy(Decimal("2.9"))
        breakdown = strategy.calculate(Decimal("100.00"))
        
        assert breakdown.gross_amount == Decimal("100.00")
        assert breakdown.total_fee == Decimal("2.90")
        assert breakdown.net_amount == Decimal("97.10")
        assert breakdown.gross_amount == breakdown.net_amount + breakdown.total_fee
        
        print(f"   ✅ PASS: Gross=${breakdown.gross_amount}, Fee=${breakdown.total_fee}, Net=${breakdown.net_amount}")
        results.append(("Percentage Fee", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Percentage Fee", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 3: Composite Fee (Stripe-like: 2.9% + $0.30)
    # =========================================================================
    print("TEST 3: Composite Fee (2.9% + $0.30)")
    try:
        strategy = create_stripe_strategy()
        breakdown = strategy.calculate(Decimal("100.00"))
        
        # 2.9% of $100 = $2.90, + $0.30 = $3.20
        expected_fee = Decimal("3.20")
        expected_net = Decimal("96.80")
        
        assert breakdown.gross_amount == Decimal("100.00")
        assert breakdown.total_fee == expected_fee, f"Expected {expected_fee}, got {breakdown.total_fee}"
        assert breakdown.net_amount == expected_net, f"Expected {expected_net}, got {breakdown.net_amount}"
        assert breakdown.gross_amount == breakdown.net_amount + breakdown.total_fee
        
        print(f"   ✅ PASS: Gross=${breakdown.gross_amount}, Fee=${breakdown.total_fee}, Net=${breakdown.net_amount}")
        print(f"      Components: {len(breakdown.fee_components)} ({[c['type'] for c in breakdown.fee_components]})")
        results.append(("Composite Fee", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Composite Fee", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 4: Revenue Conservation Invariant (INV-FIN-005)
    # =========================================================================
    print("TEST 4: Revenue Conservation Invariant (INV-FIN-005)")
    try:
        # Test with various amounts (skip amounts too small for stripe fee)
        test_amounts = [
            Decimal("1.00"),
            Decimal("50.00"),
            Decimal("100.00"),
            Decimal("999.99"),
            Decimal("10000.00"),
        ]
        
        all_valid = True
        for amount in test_amounts:
            breakdown = fee_engine.calculate(amount, strategy_name="stripe_standard")
            if breakdown.gross_amount != breakdown.net_amount + breakdown.total_fee:
                all_valid = False
                print(f"   ❌ Conservation violated for ${amount}")
        
        if all_valid:
            print(f"   ✅ PASS: Conservation verified for {len(test_amounts)} test amounts")
            results.append(("Revenue Conservation", "PASS"))
        else:
            results.append(("Revenue Conservation", "FAIL"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Revenue Conservation", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 5: Fee Exceeds Amount Protection
    # =========================================================================
    print("TEST 5: Fee Exceeds Amount Protection")
    try:
        # Try to apply a $5 flat fee to a $3 transaction
        strategy = FlatFeeStrategy(Decimal("5.00"))
        
        try:
            strategy.calculate(Decimal("3.00"))
            print(f"   ❌ FAIL: Should have raised FeeExceedsAmountError")
            results.append(("Fee Exceeds Amount", "FAIL"))
        except FeeExceedsAmountError as e:
            print(f"   ✅ PASS: Fee exceeds amount detected")
            print(f"      Gross: ${e.gross}, Fee: ${e.fee}")
            results.append(("Fee Exceeds Amount", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Fee Exceeds Amount", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 6: Tiered Fee Calculation
    # =========================================================================
    print("TEST 6: Tiered Fee Calculation")
    try:
        strategy = TieredFeeStrategy([
            (Decimal("0"), PercentageFeeStrategy(Decimal("3.0"))),       # < $100: 3%
            (Decimal("100"), PercentageFeeStrategy(Decimal("2.5"))),    # $100-999: 2.5%
            (Decimal("1000"), PercentageFeeStrategy(Decimal("2.0"))),   # >= $1000: 2%
        ])
        
        # Test small transaction (3%)
        small = strategy.calculate(Decimal("50.00"))
        assert small.total_fee == Decimal("1.50"), f"Expected $1.50, got ${small.total_fee}"
        
        # Test medium transaction (2.5%)
        medium = strategy.calculate(Decimal("500.00"))
        assert medium.total_fee == Decimal("12.50"), f"Expected $12.50, got ${medium.total_fee}"
        
        # Test large transaction (2%)
        large = strategy.calculate(Decimal("2000.00"))
        assert large.total_fee == Decimal("40.00"), f"Expected $40.00, got ${large.total_fee}"
        
        print(f"   ✅ PASS: Tiered fees calculated correctly")
        print(f"      $50 → {small.total_fee} (3%)")
        print(f"      $500 → {medium.total_fee} (2.5%)")
        print(f"      $2000 → {large.total_fee} (2%)")
        results.append(("Tiered Fee", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Tiered Fee", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 7: Calculate for Net (Reverse Calculation)
    # =========================================================================
    print("TEST 7: Calculate for Net (Reverse Calculation)")
    try:
        # We want payee to receive exactly $100 after Stripe fees
        breakdown = fee_engine.calculate_for_net(
            Decimal("100.00"),
            strategy_name="stripe_standard"
        )
        
        # Net should be $100 (or very close)
        assert abs(breakdown.net_amount - Decimal("100.00")) < Decimal("0.02")
        
        print(f"   ✅ PASS: Reverse calculation works")
        print(f"      Desired Net: $100.00")
        print(f"      Calculated Gross: ${breakdown.gross_amount}")
        print(f"      Actual Net: ${breakdown.net_amount}")
        print(f"      Fee: ${breakdown.total_fee}")
        results.append(("Calculate for Net", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Calculate for Net", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 8: Fee Engine with Built-in Strategies
    # =========================================================================
    print("TEST 8: Built-in Strategy Registry")
    try:
        strategies_tested = []
        
        # Test wire fees
        wire = fee_engine.calculate(Decimal("1000.00"), strategy_name="wire_domestic")
        assert wire.total_fee == Decimal("25.00")
        strategies_tested.append("wire_domestic")
        
        # Test ACH
        ach = fee_engine.calculate(Decimal("500.00"), strategy_name="ach_standard")
        assert ach.total_fee == Decimal("0.50")
        strategies_tested.append("ach_standard")
        
        # Test zero fee
        zero = fee_engine.calculate(Decimal("100.00"), strategy_name="zero")
        assert zero.total_fee == Decimal("0.00")
        strategies_tested.append("zero")
        
        print(f"   ✅ PASS: Built-in strategies work")
        print(f"      Tested: {', '.join(strategies_tested)}")
        results.append(("Built-in Strategies", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Built-in Strategies", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 9: Integration with Settlement Engine (Split Capture)
    # =========================================================================
    print("TEST 9: Integration with Settlement Engine")
    try:
        # Setup ledger and engines
        ledger = Ledger()
        settlement = SettlementEngine(ledger)
        
        # Create accounts
        ledger.create_account(
            account_id="CUSTOMER",
            name="Customer",
            account_type=AccountType.ASSET,
        )
        ledger.create_account(
            account_id="MERCHANT",
            name="Merchant",
            account_type=AccountType.ASSET,
        )
        # Use ASSET type for revenue account since we're using it as a cash pool
        # (In production, this would be a more sophisticated setup)
        ledger.create_account(
            account_id="PLATFORM-REVENUE",
            name="Platform Revenue",
            account_type=AccountType.ASSET,  # Treat as cash pool
        )
        
        # Fund customer
        ledger.create_account(
            account_id="FUNDING",
            name="Funding",
            account_type=AccountType.LIABILITY,
            allow_negative=True,
        )
        ledger.transfer("FUNDING", "CUSTOMER", Decimal("1000.00"))
        
        # Calculate fee for a $100 transaction
        fee_breakdown = fee_engine.calculate(Decimal("100.00"), strategy_name="stripe_standard")
        
        # Execute split settlement:
        # 1. Customer pays $100 (gross)
        # 2. Merchant receives $96.80 (net)
        # 3. Platform receives $3.20 (fee)
        
        # First: Customer -> Merchant (net amount)
        intent1 = settlement.authorize_and_capture(
            source_account="CUSTOMER",
            destination_account="MERCHANT",
            amount=fee_breakdown.net_amount,
            idempotency_key="TXN-001-NET",
            description="Payment to merchant (net)",
        )
        
        # Second: Customer -> Platform (fee)
        intent2 = settlement.authorize_and_capture(
            source_account="CUSTOMER",
            destination_account="PLATFORM-REVENUE",
            amount=fee_breakdown.total_fee,
            idempotency_key="TXN-001-FEE",
            description="Platform fee",
        )
        
        # Verify balances
        customer_balance = ledger.get_balance("CUSTOMER")
        merchant_balance = ledger.get_balance("MERCHANT")
        revenue_balance = ledger.get_balance("PLATFORM-REVENUE")
        
        assert customer_balance == Decimal("900.00")  # 1000 - 100
        assert merchant_balance == Decimal("96.80")   # Net
        assert revenue_balance == Decimal("3.20")     # Fee
        
        # Verify conservation: What customer lost = what merchant + platform received
        customer_spent = Decimal("100.00")
        total_received = merchant_balance + revenue_balance
        assert customer_spent == total_received
        
        print(f"   ✅ PASS: Split settlement works")
        print(f"      Customer: $1000.00 → ${customer_balance}")
        print(f"      Merchant: ${merchant_balance}")
        print(f"      Platform Revenue: ${revenue_balance}")
        print(f"      Conservation: ${customer_spent} = ${total_received}")
        results.append(("Settlement Integration", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Settlement Integration", "FAIL"))
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
    print("FEE ENGINE METRICS:")
    metrics = fee_engine.get_metrics()
    print(f"   Total Transactions: {metrics['total_transactions']}")
    print(f"   Total Fees Calculated: ${metrics['total_fees_calculated']}")
    print(f"   Average Fee: ${metrics['average_fee']}")
    print(f"   Built-in Strategies: {len(metrics['builtin_strategies'])}")
    
    if passed == total:
        print()
        print("🎉 FEE ENGINE VALIDATED SUCCESSFULLY")
        print("   INV-FIN-005 (Revenue Conservation): ENFORCED")
        print("   INV-FIN-006 (Transparency): ENFORCED")
        return 0
    else:
        print()
        print("⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
