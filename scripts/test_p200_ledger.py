#!/usr/bin/env python3
"""
PAC-FIN-P200 Validation Script
==============================

Tests the Double-Entry Ledger for:
1. Account creation
2. Basic transfer (A → B)
3. Conservation of Value (INV-FIN-001)
4. Immutability enforcement (INV-FIN-002)
5. Insufficient funds protection
6. Hash chain integrity
7. Transaction reversal

PAC: PAC-FIN-P200-INVISIBLE-BANK-INIT
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from decimal import Decimal
from modules.finance import (
    Ledger, AccountType, TransactionStatus,
    BalanceViolationError, InsufficientFundsError, ImmutabilityViolationError
)


def run_tests():
    print("=" * 60)
    print("PAC-FIN-P200: INVISIBLE BANK VALIDATION")
    print("=" * 60)
    print()
    
    results = []
    ledger = Ledger(ledger_id="TEST-LEDGER-001")
    
    # =========================================================================
    # TEST 1: Account Creation
    # =========================================================================
    print("TEST 1: Account Creation")
    try:
        alice = ledger.create_account(
            name="Alice Wallet",
            account_type=AccountType.ASSET,
            account_id="ALICE-001",
        )
        bob = ledger.create_account(
            name="Bob Wallet",
            account_type=AccountType.ASSET,
            account_id="BOB-001",
        )
        fees = ledger.create_account(
            name="Platform Fees",
            account_type=AccountType.FEE_REVENUE,
            account_id="FEES-001",
        )
        
        assert len(ledger.accounts) == 3
        assert alice.balance == Decimal("0.00")
        print(f"   ✅ PASS: Created 3 accounts (Alice, Bob, Fees)")
        results.append(("Account Creation", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Account Creation", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 2: Fund Account (Initial Deposit)
    # =========================================================================
    print("TEST 2: Fund Account (Simulate External Deposit)")
    try:
        # Create a funding source (represents external money coming in)
        funding = ledger.create_account(
            name="External Funding",
            account_type=AccountType.LIABILITY,  # We owe this to the customer
            account_id="FUNDING-001",
            allow_negative=True,  # Can go negative to represent inflows
        )
        
        # Fund Alice with $1000
        txn = ledger.create_transaction(
            description="Initial deposit for Alice",
            reference="DEP-001",
        )
        txn.debit("ALICE-001", Decimal("1000.00"), "Deposit received")
        txn.credit("FUNDING-001", Decimal("1000.00"), "Customer deposit")
        
        ledger.post_transaction(txn.transaction_id)
        
        assert ledger.get_balance("ALICE-001") == Decimal("1000.00")
        assert txn.status == TransactionStatus.POSTED
        print(f"   ✅ PASS: Alice funded with $1000.00")
        results.append(("Fund Account", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Fund Account", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 3: Simple Transfer (A → B)
    # =========================================================================
    print("TEST 3: Simple Transfer (Alice → Bob)")
    try:
        txn = ledger.transfer(
            from_account="ALICE-001",
            to_account="BOB-001",
            amount=Decimal("250.00"),
            description="Payment for services",
            reference="PAY-001",
        )
        
        assert ledger.get_balance("ALICE-001") == Decimal("750.00")
        assert ledger.get_balance("BOB-001") == Decimal("250.00")
        assert txn.is_balanced
        print(f"   ✅ PASS: Alice=$750.00, Bob=$250.00")
        results.append(("Simple Transfer", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Simple Transfer", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 4: Conservation of Value (INV-FIN-001)
    # =========================================================================
    print("TEST 4: Conservation of Value (INV-FIN-001)")
    try:
        # Try to create an unbalanced transaction
        bad_txn = ledger.create_transaction(description="Unbalanced test")
        bad_txn.debit("ALICE-001", Decimal("100.00"))
        bad_txn.credit("BOB-001", Decimal("50.00"))  # Intentionally unbalanced!
        
        try:
            ledger.post_transaction(bad_txn.transaction_id)
            print(f"   ❌ FAIL: Unbalanced transaction should have been rejected")
            results.append(("Conservation of Value", "FAIL"))
        except BalanceViolationError as e:
            print(f"   ✅ PASS: Unbalanced transaction rejected")
            print(f"      Error: {e}")
            results.append(("Conservation of Value", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Conservation of Value", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 5: Insufficient Funds Protection
    # =========================================================================
    print("TEST 5: Insufficient Funds Protection")
    try:
        try:
            ledger.transfer(
                from_account="BOB-001",
                to_account="ALICE-001",
                amount=Decimal("500.00"),  # Bob only has $250
            )
            print(f"   ❌ FAIL: Overdraft should have been rejected")
            results.append(("Insufficient Funds", "FAIL"))
        except InsufficientFundsError as e:
            print(f"   ✅ PASS: Overdraft rejected")
            print(f"      Error: Account {e.account_id} - required ${e.required}, available ${e.available}")
            results.append(("Insufficient Funds", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Insufficient Funds", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 6: Immutability Enforcement (INV-FIN-002)
    # =========================================================================
    print("TEST 6: Immutability Enforcement (INV-FIN-002)")
    try:
        # Get a posted transaction
        posted_txn = ledger.transactions[ledger.posted_transactions[0]]
        
        try:
            # Try to add an entry to a posted transaction
            posted_txn.debit("ALICE-001", Decimal("100.00"))
            print(f"   ❌ FAIL: Modification of posted transaction should be blocked")
            results.append(("Immutability", "FAIL"))
        except ImmutabilityViolationError as e:
            print(f"   ✅ PASS: Modification blocked")
            print(f"      Error: {e}")
            results.append(("Immutability", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Immutability", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 7: Transaction Reversal
    # =========================================================================
    print("TEST 7: Transaction Reversal")
    try:
        alice_before = ledger.get_balance("ALICE-001")
        bob_before = ledger.get_balance("BOB-001")
        
        # Find the transfer transaction and reverse it
        transfer_txn_id = ledger.posted_transactions[1]  # The Alice→Bob transfer
        
        reversal = ledger.reverse_transaction(
            transaction_id=transfer_txn_id,
            reason="Customer requested refund"
        )
        
        alice_after = ledger.get_balance("ALICE-001")
        bob_after = ledger.get_balance("BOB-001")
        
        assert alice_after == alice_before + Decimal("250.00")
        assert bob_after == bob_before - Decimal("250.00")
        assert reversal.status == TransactionStatus.POSTED
        
        print(f"   ✅ PASS: Reversal completed")
        print(f"      Alice: ${alice_before} → ${alice_after}")
        print(f"      Bob: ${bob_before} → ${bob_after}")
        results.append(("Transaction Reversal", "PASS"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Transaction Reversal", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 8: Hash Chain Integrity
    # =========================================================================
    print("TEST 8: Hash Chain Integrity")
    try:
        is_valid, message = ledger.verify_chain_integrity()
        
        if is_valid:
            print(f"   ✅ PASS: {message}")
            results.append(("Hash Chain Integrity", "PASS"))
        else:
            print(f"   ❌ FAIL: {message}")
            results.append(("Hash Chain Integrity", "FAIL"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Hash Chain Integrity", "FAIL"))
    print()
    
    # =========================================================================
    # TEST 9: Global Conservation Audit
    # =========================================================================
    print("TEST 9: Global Conservation Audit")
    try:
        is_valid, message = ledger.verify_conservation()
        
        if is_valid:
            print(f"   ✅ PASS: {message}")
            results.append(("Global Conservation", "PASS"))
        else:
            print(f"   ❌ FAIL: {message}")
            results.append(("Global Conservation", "FAIL"))
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        results.append(("Global Conservation", "FAIL"))
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
    
    # Print audit summary
    print("AUDIT SUMMARY:")
    audit = ledger.get_audit_summary()
    print(f"   Ledger ID: {audit['ledger_id']}")
    print(f"   Genesis Hash: {audit['genesis_hash'][:16]}...")
    print(f"   Accounts: {audit['total_accounts']}")
    print(f"   Posted Transactions: {audit['posted_transactions']}")
    print(f"   Total Debits: ${audit['total_debits']}")
    print(f"   Total Credits: ${audit['total_credits']}")
    print(f"   Chain Integrity: {'✅' if audit['chain_integrity']['valid'] else '❌'}")
    print(f"   Conservation: {'✅' if audit['conservation_of_value']['valid'] else '❌'}")
    
    if passed == total:
        print()
        print("🎉 INVISIBLE BANK INITIALIZED SUCCESSFULLY")
        print("   INV-FIN-001 (Conservation of Value): ENFORCED")
        print("   INV-FIN-002 (Immutability): ENFORCED")
        return 0
    else:
        print()
        print("⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
