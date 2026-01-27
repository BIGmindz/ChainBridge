"""
PAC-FIN-P80: Sovereign Treasury Test Suite
===========================================
Comprehensive test coverage for treasury allocation logic.

Tests:
- Allocation math correctness (90/10 split)
- Zero-drift enforcement (TREASURY-01)
- Quantum signature integration (TREASURY-02)
- Mandate verification and tamper detection
- Edge cases and boundary conditions

Created: PAC-FIN-P80
Updated: 2026-01-25
"""

import hashlib
import json
import os
import sys
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.finance.treasury import (
    SovereignTreasury,
    AllocationPolicy,
    AllocationMandate,
    get_global_treasury
)
from core.crypto.quantum_signer import QuantumSigner, QuantumVerifier


# ============================================================================
# Test Suite
# ============================================================================

def test_allocation_policy_creation():
    """Test AllocationPolicy initialization and validation."""
    print("\n🧪 TEST: Allocation Policy Creation")
    
    # Valid policy
    policy = AllocationPolicy(cold_storage_pct=0.90, hot_wallet_pct=0.10)
    assert policy.cold_storage_pct == Decimal("0.90")
    assert policy.hot_wallet_pct == Decimal("0.10")
    assert policy.policy_id == "PAC-P80-V1"
    print("✅ Valid policy created")
    
    # Custom policy
    custom = AllocationPolicy(
        cold_storage_pct=0.80,
        hot_wallet_pct=0.20,
        policy_id="CUSTOM-V2"
    )
    assert custom.cold_storage_pct == Decimal("0.80")
    assert custom.hot_wallet_pct == Decimal("0.20")
    assert custom.policy_id == "CUSTOM-V2"
    print("✅ Custom policy created")
    
    # Invalid policy (doesn't sum to 1.0)
    try:
        invalid = AllocationPolicy(cold_storage_pct=0.85, hot_wallet_pct=0.20)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must sum to 1.0" in str(e)
        print("✅ Invalid policy rejected")
    
    print("✅ PASSED: Allocation Policy Creation\n")


def test_allocation_mandate_hash():
    """Test AllocationMandate hash computation."""
    print("\n🧪 TEST: Allocation Mandate Hash")
    
    mandate1 = AllocationMandate(
        batch_id="BATCH-001",
        total_amount=Decimal("1000.00"),
        cold_storage_amount=Decimal("900.00"),
        hot_wallet_amount=Decimal("100.00"),
        policy_id="PAC-P80-V1"
    )
    
    # Same data should produce same hash
    mandate2 = AllocationMandate(
        batch_id="BATCH-001",
        total_amount=Decimal("1000.00"),
        cold_storage_amount=Decimal("900.00"),
        hot_wallet_amount=Decimal("100.00"),
        policy_id="PAC-P80-V1",
        timestamp=mandate1.timestamp  # Use same timestamp
    )
    
    assert mandate1.mandate_hash == mandate2.mandate_hash
    print(f"✅ Deterministic hash: {mandate1.mandate_hash[:16]}...")
    
    # Different data should produce different hash
    mandate3 = AllocationMandate(
        batch_id="BATCH-002",  # Different batch ID
        total_amount=Decimal("1000.00"),
        cold_storage_amount=Decimal("900.00"),
        hot_wallet_amount=Decimal("100.00"),
        policy_id="PAC-P80-V1",
        timestamp=mandate1.timestamp
    )
    
    assert mandate1.mandate_hash != mandate3.mandate_hash
    print("✅ Different data produces different hash")
    
    print("✅ PASSED: Allocation Mandate Hash\n")


def test_zero_drift_validation():
    """Test TREASURY-01 zero-drift enforcement."""
    print("\n🧪 TEST: TREASURY-01 - Zero Drift Validation")
    
    # Valid allocation (perfect sum)
    valid_mandate = AllocationMandate(
        batch_id="BATCH-VALID",
        total_amount=Decimal("1000.00"),
        cold_storage_amount=Decimal("900.00"),
        hot_wallet_amount=Decimal("100.00"),
        policy_id="PAC-P80-V1"
    )
    
    assert valid_mandate.verify_zero_drift()
    print("✅ Valid mandate passes zero-drift check")
    
    # Invalid allocation (drift)
    invalid_mandate = AllocationMandate(
        batch_id="BATCH-DRIFT",
        total_amount=Decimal("1000.00"),
        cold_storage_amount=Decimal("900.00"),
        hot_wallet_amount=Decimal("100.01"),  # 1 cent drift
        policy_id="PAC-P80-V1"
    )
    
    assert not invalid_mandate.verify_zero_drift()
    print("✅ Invalid mandate fails zero-drift check")
    
    # Edge case: exactly at tolerance
    edge_mandate = AllocationMandate(
        batch_id="BATCH-EDGE",
        total_amount=Decimal("1000.00"),
        cold_storage_amount=Decimal("900.00"),
        hot_wallet_amount=Decimal("100.0000009"),  # Within tolerance
        policy_id="PAC-P80-V1"
    )
    
    assert edge_mandate.verify_zero_drift(tolerance=Decimal("0.000001"))
    print("✅ Edge case within tolerance passes")
    
    print("✅ PASSED: TREASURY-01 - Zero Drift Validation\n")


def test_basic_allocation():
    """Test basic treasury allocation (90/10 split)."""
    print("\n🧪 TEST: Basic Allocation (90/10 Split)")
    
    treasury = SovereignTreasury()
    
    # Allocate $1,000,000
    mandate = treasury.allocate_funds("BATCH-001", 1000000.00)
    
    assert mandate.batch_id == "BATCH-001"
    assert mandate.total_amount == Decimal("1000000.00")
    assert mandate.cold_storage_amount == Decimal("900000.00")
    assert mandate.hot_wallet_amount == Decimal("100000.00")
    
    print(f"  Total: ${mandate.total_amount:,.2f}")
    print(f"  Cold:  ${mandate.cold_storage_amount:,.2f} (90%)")
    print(f"  Hot:   ${mandate.hot_wallet_amount:,.2f} (10%)")
    
    # Verify zero-drift
    assert mandate.verify_zero_drift()
    print("✅ Zero-drift check passed")
    
    # Verify signature
    assert mandate.signature is not None
    assert mandate.signer_pubkey is not None
    print("✅ Mandate signed with Dilithium")
    
    print("✅ PASSED: Basic Allocation\n")


def test_allocation_edge_cases():
    """Test allocation with edge case amounts."""
    print("\n🧪 TEST: Allocation Edge Cases")
    
    treasury = SovereignTreasury()
    
    # Small amount
    small_mandate = treasury.allocate_funds("BATCH-SMALL", 10.00)
    assert small_mandate.cold_storage_amount == Decimal("9.00")
    assert small_mandate.hot_wallet_amount == Decimal("1.00")
    assert small_mandate.verify_zero_drift()
    print("✅ Small amount ($10) allocated correctly")
    
    # Odd amount (rounding test)
    odd_mandate = treasury.allocate_funds("BATCH-ODD", 777.77)
    assert odd_mandate.cold_storage_amount == Decimal("699.99")
    assert odd_mandate.hot_wallet_amount == Decimal("77.78")
    assert odd_mandate.verify_zero_drift()
    print("✅ Odd amount ($777.77) allocated correctly")
    
    # Large amount
    large_mandate = treasury.allocate_funds("BATCH-LARGE", 999999999.99)
    expected_cold = Decimal("899999999.99")
    expected_hot = Decimal("100000000.00")
    assert large_mandate.cold_storage_amount == expected_cold
    assert large_mandate.hot_wallet_amount == expected_hot
    assert large_mandate.verify_zero_drift()
    print("✅ Large amount ($999,999,999.99) allocated correctly")
    
    print("✅ PASSED: Allocation Edge Cases\n")


def test_quantum_signature_integration():
    """Test TREASURY-02 quantum signature integration."""
    print("\n🧪 TEST: TREASURY-02 - Quantum Signature Integration")
    
    # Create treasury with dedicated signer
    signer = QuantumSigner()
    treasury = SovereignTreasury(signer=signer)
    
    # Allocate and sign
    mandate = treasury.allocate_funds("BATCH-SIG-001", 50000.00, sign_mandate=True)
    
    assert mandate.signature is not None
    assert mandate.signer_pubkey is not None
    assert len(mandate.signature) > 0
    print(f"✅ Signature created: {len(mandate.signature)} bytes")
    print(f"✅ Public key: {mandate.signer_pubkey[:32]}...")
    
    # Verify signature
    verifier = QuantumVerifier.from_hex(mandate.signer_pubkey)
    hash_bytes = bytes.fromhex(mandate.mandate_hash)
    is_valid = verifier.verify(hash_bytes, mandate.signature)
    
    assert is_valid
    print("✅ Signature verified successfully")
    
    # Test tampered mandate (modify allocation)
    tampered_mandate = AllocationMandate(
        batch_id=mandate.batch_id,
        total_amount=mandate.total_amount,
        cold_storage_amount=mandate.cold_storage_amount + Decimal("1.00"),  # Tamper
        hot_wallet_amount=mandate.hot_wallet_amount - Decimal("1.00"),
        policy_id=mandate.policy_id,
        signature=mandate.signature,  # Original signature
        signer_pubkey=mandate.signer_pubkey,
        timestamp=mandate.timestamp
    )
    
    # Hash will be different, signature won't verify
    tampered_hash = bytes.fromhex(tampered_mandate.mandate_hash)
    is_tampered_valid = verifier.verify(tampered_hash, mandate.signature)
    
    assert not is_tampered_valid
    print("✅ Tampered mandate signature fails verification")
    
    print("✅ PASSED: TREASURY-02 - Quantum Signature Integration\n")


def test_mandate_verification():
    """Test mandate verification workflow."""
    print("\n🧪 TEST: Mandate Verification Workflow")
    
    treasury = SovereignTreasury()
    
    # Create and verify valid mandate
    mandate = treasury.allocate_funds("BATCH-VERIFY-001", 100000.00)
    
    is_valid = treasury.verify_mandate(mandate)
    assert is_valid
    print("✅ Valid mandate verified")
    
    # Test unsigned mandate
    unsigned_mandate = treasury.allocate_funds(
        "BATCH-UNSIGNED", 50000.00, sign_mandate=False
    )
    
    is_unsigned_valid = treasury.verify_mandate(unsigned_mandate)
    assert is_unsigned_valid  # Still valid (zero-drift OK), just unsigned
    print("✅ Unsigned mandate passes zero-drift check")
    
    # Test mandate with malformed signature (change a byte)
    # This will fail the mock signature format check
    if mandate.signature and len(mandate.signature) > 10:
        # Create invalid signature by corrupting it
        corrupted_sig = b"INVALID" + mandate.signature[7:]
        
        forged_mandate = AllocationMandate(
            batch_id=mandate.batch_id,
            total_amount=mandate.total_amount,
            cold_storage_amount=mandate.cold_storage_amount,
            hot_wallet_amount=mandate.hot_wallet_amount,
            policy_id=mandate.policy_id,
            signature=corrupted_sig,  # Corrupted signature
            signer_pubkey=mandate.signer_pubkey,
            timestamp=mandate.timestamp
        )
        
        # Verify should fail due to corrupted signature
        is_forged_valid = treasury.verify_mandate(forged_mandate)
        assert not is_forged_valid
        print("✅ Forged mandate fails verification")
    else:
        print("⚠️  Skipped forgery test (mock mode)")
    
    print("✅ PASSED: Mandate Verification Workflow\n")


def test_allocation_stats():
    """Test treasury statistics tracking."""
    print("\n🧪 TEST: Treasury Allocation Statistics")
    
    treasury = SovereignTreasury()
    
    # Initial stats
    stats = treasury.get_allocation_stats()
    assert stats["total_batches"] == 0
    assert stats["total_allocated_usd"] == 0.0
    print("✅ Initial stats correct")
    
    # Allocate multiple batches
    treasury.allocate_funds("BATCH-STATS-001", 100000.00)
    treasury.allocate_funds("BATCH-STATS-002", 50000.00)
    treasury.allocate_funds("BATCH-STATS-003", 25000.00)
    
    stats = treasury.get_allocation_stats()
    
    assert stats["total_batches"] == 3
    assert stats["total_allocated_usd"] == 175000.00
    assert stats["total_cold_usd"] == 157500.00  # 90% of 175k
    assert stats["total_hot_usd"] == 17500.00    # 10% of 175k
    assert stats["signed_mandates"] == 3
    
    print(f"  Total Batches: {stats['total_batches']}")
    print(f"  Total Allocated: ${stats['total_allocated_usd']:,.2f}")
    print(f"  Total Cold: ${stats['total_cold_usd']:,.2f}")
    print(f"  Total Hot: ${stats['total_hot_usd']:,.2f}")
    print(f"  Signed Mandates: {stats['signed_mandates']}")
    
    print("✅ PASSED: Treasury Allocation Statistics\n")


def test_mandate_export():
    """Test mandate export to JSON."""
    print("\n🧪 TEST: Mandate Export to JSON")
    
    treasury = SovereignTreasury()
    
    # Create some allocations
    treasury.allocate_funds("BATCH-EXPORT-001", 100000.00)
    treasury.allocate_funds("BATCH-EXPORT-002", 50000.00)
    
    # Export to file
    export_path = "/tmp/test_treasury_export.json"
    treasury.export_mandates(export_path)
    
    # Verify file contents
    assert os.path.exists(export_path)
    
    with open(export_path, 'r') as f:
        data = json.load(f)
    
    assert data["pac_id"] == "PAC-FIN-P80"
    assert len(data["mandates"]) == 2
    assert data["stats"]["total_batches"] == 2
    assert data["stats"]["total_allocated_usd"] == 150000.00
    
    # Verify mandate structure
    mandate = data["mandates"][0]
    assert "batch_id" in mandate
    assert "total_amount" in mandate
    assert "allocations" in mandate
    assert "quantum_signature" in mandate
    assert "mandate_hash" in mandate
    
    print(f"✅ Exported to {export_path}")
    print(f"✅ Verified {len(data['mandates'])} mandates")
    
    # Cleanup
    os.remove(export_path)
    
    print("✅ PASSED: Mandate Export to JSON\n")


def test_custom_policy():
    """Test treasury with custom allocation policy."""
    print("\n🧪 TEST: Custom Allocation Policy")
    
    # Create 80/20 policy
    custom_policy = AllocationPolicy(
        cold_storage_pct=0.80,
        hot_wallet_pct=0.20,
        policy_id="CUSTOM-80-20"
    )
    
    treasury = SovereignTreasury(policy=custom_policy)
    
    # Allocate with custom policy
    mandate = treasury.allocate_funds("BATCH-CUSTOM-001", 100000.00)
    
    assert mandate.cold_storage_amount == Decimal("80000.00")
    assert mandate.hot_wallet_amount == Decimal("20000.00")
    assert mandate.policy_id == "CUSTOM-80-20"
    assert mandate.verify_zero_drift()
    
    print(f"✅ Custom policy applied: 80/20 split")
    print(f"  Cold: ${mandate.cold_storage_amount:,.2f}")
    print(f"  Hot: ${mandate.hot_wallet_amount:,.2f}")
    
    print("✅ PASSED: Custom Allocation Policy\n")


def test_global_treasury_singleton():
    """Test global treasury singleton pattern."""
    print("\n🧪 TEST: Global Treasury Singleton")
    
    # Get global treasury
    treasury1 = get_global_treasury()
    treasury2 = get_global_treasury()
    
    # Should be same instance
    assert treasury1 is treasury2
    print("✅ Singleton pattern enforced")
    
    # Allocate via singleton
    mandate = treasury1.allocate_funds("BATCH-GLOBAL-001", 75000.00)
    
    # Stats should reflect in both references
    stats1 = treasury1.get_allocation_stats()
    stats2 = treasury2.get_allocation_stats()
    
    assert stats1["total_batches"] == stats2["total_batches"]
    assert stats1["total_allocated_usd"] == stats2["total_allocated_usd"]
    
    print("✅ Singleton state shared across references")
    
    print("✅ PASSED: Global Treasury Singleton\n")


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Execute all treasury tests."""
    print("=" * 80)
    print("PAC-FIN-P80: SOVEREIGN TREASURY TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_allocation_policy_creation,
        test_allocation_mandate_hash,
        test_zero_drift_validation,
        test_basic_allocation,
        test_allocation_edge_cases,
        test_quantum_signature_integration,
        test_mandate_verification,
        test_allocation_stats,
        test_mandate_export,
        test_custom_policy,
        test_global_treasury_singleton
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
        except Exception as e:
            failed += 1
            print(f"❌ ERROR: {test_func.__name__}")
            print(f"   Exception: {e}")
    
    print("=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - TREASURY READY FOR DEPLOYMENT")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - REVIEW REQUIRED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
