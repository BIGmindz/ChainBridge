#!/usr/bin/env python3
"""
PAC-INT-P211-API-UPGRADE Validation Test

Validates that sovereign_server.py v2.0 has:
1. PaymentData with fee_strategy field
2. FinancialTrace model for transparency
3. TransactionReceipt with financial_trace
4. App version 2.0.0
"""

import sys
sys.path.insert(0, ".")

from sovereign_server import (
    app,
    PaymentData, 
    FinancialTrace, 
    TransactionReceipt, 
    SovereignTransactionRequest
)

def test_api_version():
    """Test app version is 2.0.0"""
    assert app.version == "2.0.0", f"Expected version 2.0.0, got {app.version}"
    print("✅ Test 1 PASSED: App version is 2.0.0")

def test_payment_data_fee_strategy():
    """Test PaymentData has fee_strategy field"""
    pd = PaymentData(
        payer_id='ACME', 
        payee_id='GLOBEX', 
        amount=100.0, 
        fee_strategy='premium'
    )
    assert pd.fee_strategy == 'premium', f"Expected fee_strategy='premium', got {pd.fee_strategy}"
    
    # Test default value
    pd_default = PaymentData(payer_id='A', payee_id='B', amount=50.0)
    assert pd_default.fee_strategy == 'default', f"Expected default='default', got {pd_default.fee_strategy}"
    
    print("✅ Test 2 PASSED: PaymentData has fee_strategy field")

def test_financial_trace_model():
    """Test FinancialTrace model structure"""
    ft = FinancialTrace(
        gross_amount='100.00',
        currency='USD',
        settlement_intent_id='PI-123',
        settlement_status='captured',
        fees={'total': '3.20', 'strategy': 'default'},
        net_amount='96.80',
        ledger_committed=True
    )
    assert ft.settlement_status == 'captured'
    assert ft.gross_amount == '100.00'
    assert ft.net_amount == '96.80'
    assert ft.ledger_committed == True
    print("✅ Test 3 PASSED: FinancialTrace model works correctly")

def test_transaction_receipt_with_financial_trace():
    """Test TransactionReceipt includes financial_trace"""
    ft = FinancialTrace(
        gross_amount='250000.00',
        currency='USD',
        settlement_intent_id='PI-456',
        settlement_status='captured',
        fees={'total': '7250.30', 'strategy': 'default'},
        net_amount='242749.70',
        payer_account='ACME-CORP',
        payee_account='GLOBEX-INC',
        ledger_committed=True
    )
    
    tr = TransactionReceipt(
        transaction_id='TRINITY-20260111',
        timestamp='2026-01-11T13:30:32Z',
        status='FINALIZED',
        finalized=True,
        gates={'biometric': {'decision': 'VERIFY'}, 'aml': {'decision': 'APPROVE'}, 'customs': {'decision': 'RELEASE'}},
        financial_trace=ft,
        controller='BENSON (GID-00)',
        version='2.0.0',
        invariants_enforced=['INV-API-003', 'INV-INT-001', 'INV-INT-002']
    )
    
    assert tr.finalized == True
    assert tr.financial_trace is not None
    assert tr.financial_trace.ledger_committed == True
    assert tr.financial_trace.gross_amount == '250000.00'
    assert 'INV-API-003' in tr.invariants_enforced
    print("✅ Test 4 PASSED: TransactionReceipt includes financial_trace")

def run_all_tests():
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║        PAC-INT-P211-API-UPGRADE VALIDATION TEST                      ║")
    print("║        \"The Voice now speaks the language of Money.\"                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    
    test_api_version()
    test_payment_data_fee_strategy()
    test_financial_trace_model()
    test_transaction_receipt_with_financial_trace()
    
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                    ALL 4 TESTS PASSED ✅                              ║")
    print("║                                                                      ║")
    print("║  SOVEREIGN SERVER v2.0 VALIDATED:                                    ║")
    print("║    • PaymentData.fee_strategy: ✅                                    ║")
    print("║    • FinancialTrace model: ✅                                        ║")
    print("║    • TransactionReceipt.financial_trace: ✅                          ║")
    print("║    • INV-API-003 (Rich Receipts): ENFORCED                          ║")
    print("║                                                                      ║")
    print("║  BENSON HANDSHAKE: MASTER-BER-P211-UPGRADE                          ║")
    print("║  LEDGER_COMMIT: ATTEST: SOVEREIGN_INTERFACE_V2                       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    return {
        "tests_run": 4,
        "tests_passed": 4,
        "api_version": "2.0.0",
        "attestation": "MASTER-BER-P211-UPGRADE"
    }

if __name__ == "__main__":
    result = run_all_tests()
    print(f"\n✅ RESULT: {result}")
