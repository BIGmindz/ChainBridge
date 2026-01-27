#!/usr/bin/env python3
"""
PAC-48 Legion Test Execution Script
"""
import sys
sys.path.insert(0, '.')

from core.swarm.legion_commander import quick_legion_test

if __name__ == "__main__":
    print("=" * 70)
    print("PAC-48: LEGION SWARM ACTIVATION TEST")
    print("=" * 70)
    
    result = quick_legion_test(
        batch_amount=100_000_000,
        transaction_count=100_000
    )
    
    print()
    print("=" * 70)
    print("🏆 FINAL RESULTS")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"TPS: {result['tps']:,.0f}")
    print(f"Volume: ${result['volume_usd']:,.2f}")
    print(f"LEGION-02: {'✅ SATISFIED' if result['legion_02_satisfied'] else '❌ NOT MET'}")
    print("=" * 70)
