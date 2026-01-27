#!/usr/bin/env python3
"""
Test God View V3.0 LIVE MODE activation and telemetry latency.

PAC: CB-UI-RESTORE-2026-01-27
Agent: ATLAS (GID-11)
"""
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.god_view_v3 import GodViewDashboardV3

print("="*60)
print("GOD VIEW V3.0 - LIVE MODE VERIFICATION")
print("="*60)
print()

# Test 1: Live mode initialization
print("[TEST 1/3] Live mode initialization...")
start = time.time()
dashboard = GodViewDashboardV3(is_live=True)
init_time = (time.time() - start) * 1000

print(f"✅ Live mode initialized in {init_time:.2f}ms")
print(f"   Inspector General: {'✅ BOUND' if dashboard.inspector_general else '❌ MISSING'}")
print(f"   Dilithium Kernel: {'✅ BOUND' if dashboard.dilithium_kernel else '❌ MISSING'}")
print(f"   SCRAM Controller: {'✅ BOUND' if dashboard.scram_controller else '❌ MISSING'}")
print()

# Test 2: Telemetry query latency
print("[TEST 2/3] Kernel state telemetry query...")
start = time.time()
kernel_state = dashboard._get_kernel_state()
query_time = (time.time() - start) * 1000

print(f"✅ Kernel state query completed in {query_time:.2f}ms")
print(f"   Internal telemetry latency: {kernel_state['telemetry_latency_ms']}ms")
print(f"   Active GIDs: {len(kernel_state['active_gids'])} ({', '.join(kernel_state['active_gids'][:5])}...)")
print(f"   SCRAM armed: {kernel_state['scram_armed']}")
print(f"   PQC signatures: {kernel_state['pqc_signatures']}")
print()

# Test 3: Latency requirement validation
print("[TEST 3/3] Latency requirement validation...")
latency_ok = query_time < 50
print("   Requirement: <50ms")
print(f"   Actual: {query_time:.2f}ms")
print(f"   Status: {'✅ PASS' if latency_ok else '❌ FAIL'}")
print()

print("="*60)
print("LIVE MODE VERIFICATION COMPLETE")
print("="*60)
print()
print(f"🎯 God View V3.0 is_live: {'✅ TRUE' if dashboard.is_live else '❌ FALSE'}")
print(f"🚀 Telemetry latency: {'✅ VERIFIED (<50ms)' if latency_ok else '⚠️ SLOW (>50ms)'}")
print()
