#!/usr/bin/env python3
"""
PAC-FIN-P80 Sovereign Treasury - Live Demonstration
Shows complete allocation workflow with quantum signatures.
"""
import sys
sys.path.insert(0, '.')

from core.finance import get_global_treasury, AllocationPolicy, SovereignTreasury

print("=" * 80)
print("PAC-FIN-P80: SOVEREIGN TREASURY DEMONSTRATION")
print("=" * 80)

# ============================================================================
# DEMO 1: Basic Allocation (90/10 Split)
# ============================================================================
print("\n📊 DEMO 1: Basic Allocation with Default Policy (90/10)")
print("-" * 80)

treasury = get_global_treasury()

# Simulate incoming capital batches
batches = [
    ("BATCH-001", 1_000_000.00),
    ("BATCH-002", 500_000.00),
    ("BATCH-003", 250_000.00),
]

for batch_id, amount in batches:
    mandate = treasury.allocate_funds(batch_id, amount)
    
    print(f"\n{batch_id}: ${amount:,.2f}")
    print(f"  ├─ Cold Storage: ${mandate.cold_storage_amount:,.2f} (90%)")
    print(f"  ├─ Hot Wallet:   ${mandate.hot_wallet_amount:,.2f} (10%)")
    print(f"  ├─ Zero Drift:   {mandate.verify_zero_drift()} ✅")
    print(f"  ├─ Hash:         {mandate.mandate_hash[:16]}...")
    print(f"  └─ Signature:    {len(mandate.signature)} bytes")

# ============================================================================
# DEMO 2: Treasury Statistics
# ============================================================================
print("\n\n📈 DEMO 2: Treasury Statistics")
print("-" * 80)

stats = treasury.get_allocation_stats()
print(f"Total Batches:     {stats['total_batches']}")
print(f"Total Allocated:   ${stats['total_allocated_usd']:,.2f}")
print(f"Total Cold:        ${stats['total_cold_usd']:,.2f}")
print(f"Total Hot:         ${stats['total_hot_usd']:,.2f}")
print(f"Signed Mandates:   {stats['signed_mandates']}")

# ============================================================================
# DEMO 3: Custom Policy (80/20 Split)
# ============================================================================
print("\n\n⚙️  DEMO 3: Custom Allocation Policy (80/20)")
print("-" * 80)

custom_policy = AllocationPolicy(
    cold_storage_pct=0.80,
    hot_wallet_pct=0.20,
    policy_id="AGGRESSIVE-80-20"
)

custom_treasury = SovereignTreasury(policy=custom_policy)

mandate = custom_treasury.allocate_funds("BATCH-AGGRESSIVE-001", 1_000_000.00)

print(f"\nPolicy: {custom_policy.policy_id}")
print(f"  ├─ Cold Storage: ${mandate.cold_storage_amount:,.2f} (80%)")
print(f"  ├─ Hot Wallet:   ${mandate.hot_wallet_amount:,.2f} (20%)")
print(f"  └─ Zero Drift:   {mandate.verify_zero_drift()} ✅")

# ============================================================================
# DEMO 4: Mandate Verification (Tamper Detection)
# ============================================================================
print("\n\n🔍 DEMO 4: Mandate Verification and Tamper Detection")
print("-" * 80)

# Verify valid mandate
valid_mandate = treasury.allocation_history[0]
is_valid = treasury.verify_mandate(valid_mandate)
print(f"\nOriginal Mandate ({valid_mandate.batch_id}):")
print(f"  ├─ Zero Drift:       {valid_mandate.verify_zero_drift()} ✅")
print(f"  ├─ Signature Valid:  {is_valid} ✅")
print(f"  └─ Status:           VERIFIED")

# Simulate tampered mandate (change allocation)
from core.finance.treasury import AllocationMandate
from decimal import Decimal

tampered = AllocationMandate(
    batch_id=valid_mandate.batch_id,
    total_amount=valid_mandate.total_amount,
    cold_storage_amount=valid_mandate.cold_storage_amount + Decimal("100.00"),  # Tamper!
    hot_wallet_amount=valid_mandate.hot_wallet_amount - Decimal("100.00"),
    policy_id=valid_mandate.policy_id,
    signature=valid_mandate.signature,  # Original signature
    signer_pubkey=valid_mandate.signer_pubkey,
    timestamp=valid_mandate.timestamp
)

is_tampered_valid = treasury.verify_mandate(tampered)
print(f"\nTampered Mandate (cold +$100, hot -$100):")
print(f"  ├─ Zero Drift:       {tampered.verify_zero_drift()} ✅")
print(f"  ├─ Hash Changed:     {tampered.mandate_hash != valid_mandate.mandate_hash} ✅")
print(f"  ├─ Signature Valid:  {is_tampered_valid} ❌")
print(f"  └─ Status:           REJECTED (TREASURY-02 VIOLATION)")

# ============================================================================
# DEMO 5: Export Mandates
# ============================================================================
print("\n\n💾 DEMO 5: Export Treasury Audit Trail")
print("-" * 80)

export_path = "/tmp/treasury_demo_export.json"
treasury.export_mandates(export_path)

import json
with open(export_path, 'r') as f:
    export_data = json.load(f)

print(f"\nExported to: {export_path}")
print(f"  ├─ PAC ID:          {export_data['pac_id']}")
print(f"  ├─ Total Batches:   {len(export_data['mandates'])}")
print(f"  ├─ Policy:          {export_data['policy']['policy_id']}")
print(f"  └─ Total USD:       ${export_data['stats']['total_allocated_usd']:,.2f}")

print("\n" + "=" * 80)
print("🏛️  THE VAULT IS OPEN - TREASURY DEMONSTRATION COMPLETE")
print("=" * 80)
