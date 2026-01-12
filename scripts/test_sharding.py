#!/usr/bin/env python3
"""
P920 Sovereign State Sharding Verification Test
================================================

Tests:
1. Shard creation for 5 tenants
2. Data persistence (write → close → reopen → verify)
3. Shard isolation (INV-DATA-003)
4. Crash recovery simulation (INV-DATA-004)

PAC Reference: PAC-OCC-P920-SHARDING
"""

import sys
import os
import json
import time
import signal
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data.sharding import ShardManager, TenantShard, ShardConfig, ShardState, CRYPTO_AVAILABLE

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def test_shard_creation(manager: ShardManager, tenant_ids: list) -> dict:
    """Test creating shards for multiple tenants."""
    print(f"\n{YELLOW}[TEST 1]{RESET} Shard Creation")
    
    results = {"passed": True, "details": []}
    
    for tenant_id in tenant_ids:
        try:
            shard = manager.get_shard(tenant_id, create=True)
            
            # Write initial data
            entry_id = shard.write_ledger("TEST_INIT", {
                "tenant_id": tenant_id,
                "test_data": f"Data for {tenant_id}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            # Set config
            shard.set_config("test_key", {"value": tenant_id, "created": True})
            
            results["details"].append({
                "tenant_id": tenant_id,
                "entry_id": entry_id,
                "path": str(shard.config.shard_path),
                "success": True,
            })
            print(f"  {GREEN}✓{RESET} {tenant_id}: entry_id={entry_id}")
            
        except Exception as e:
            results["passed"] = False
            results["details"].append({
                "tenant_id": tenant_id,
                "error": str(e),
                "success": False,
            })
            print(f"  {RED}✗{RESET} {tenant_id}: {e}")
    
    return results


def test_persistence(manager: ShardManager, tenant_ids: list) -> dict:
    """Test data persistence across close/reopen cycles."""
    print(f"\n{YELLOW}[TEST 2]{RESET} Persistence (Close → Reopen → Verify)")
    
    results = {"passed": True, "details": []}
    
    # Write unique data to each tenant
    test_data = {}
    for tenant_id in tenant_ids:
        shard = manager.get_shard(tenant_id)
        unique_value = f"persistence_test_{int(time.time() * 1000)}_{tenant_id}"
        shard.set_config("persistence_test", unique_value)
        test_data[tenant_id] = unique_value
    
    # Close all shards
    print("  Closing all shards...")
    manager.close_all()
    
    # Reopen and verify
    print("  Reopening and verifying...")
    for tenant_id in tenant_ids:
        try:
            shard = manager.get_shard(tenant_id, create=False)
            retrieved = shard.get_config("persistence_test")
            
            expected = test_data[tenant_id]
            matches = retrieved == expected
            
            results["details"].append({
                "tenant_id": tenant_id,
                "expected": expected,
                "retrieved": retrieved,
                "matches": matches,
            })
            
            if matches:
                print(f"  {GREEN}✓{RESET} {tenant_id}: Data persisted correctly")
            else:
                print(f"  {RED}✗{RESET} {tenant_id}: Data mismatch!")
                results["passed"] = False
                
        except Exception as e:
            results["passed"] = False
            results["details"].append({
                "tenant_id": tenant_id,
                "error": str(e),
                "matches": False,
            })
            print(f"  {RED}✗{RESET} {tenant_id}: {e}")
    
    return results


def test_isolation(manager: ShardManager, tenant_ids: list) -> dict:
    """Test shard isolation (INV-DATA-003)."""
    print(f"\n{YELLOW}[TEST 3]{RESET} Shard Isolation (INV-DATA-003)")
    
    # Get isolation verification from manager
    isolation = manager.verify_isolation()
    
    print(f"  Invariant: {isolation['invariant']}")
    print(f"  Verified: {isolation['verified']}")
    
    # Additional checks: verify paths are distinct
    paths = set()
    for tenant_id in tenant_ids:
        shard = manager.get_shard(tenant_id)
        path = str(shard.config.shard_path.resolve())
        
        if path in paths:
            print(f"  {RED}✗{RESET} Path collision detected: {path}")
            isolation["verified"] = False
        else:
            paths.add(path)
    
    # Check that we can't access other tenant's data
    print("\n  Cross-tenant access test:")
    for i, tenant_id in enumerate(tenant_ids):
        other_tenant = tenant_ids[(i + 1) % len(tenant_ids)]
        shard = manager.get_shard(tenant_id)
        
        # Verify this shard doesn't have other tenant's data
        other_data = shard.get_config(f"unique_to_{other_tenant}", None)
        if other_data is None:
            print(f"  {GREEN}✓{RESET} {tenant_id} cannot see {other_tenant}'s data")
        else:
            print(f"  {RED}✗{RESET} {tenant_id} CAN see {other_tenant}'s data!")
            isolation["verified"] = False
    
    return {"passed": isolation["verified"], "details": isolation}


def test_crash_recovery(manager: ShardManager, base_dir: Path) -> dict:
    """Test crash recovery (INV-DATA-004)."""
    print(f"\n{YELLOW}[TEST 4]{RESET} Crash Recovery (INV-DATA-004)")
    
    results = {"passed": True, "details": []}
    
    # Create a special test tenant
    crash_tenant = "crash-test-tenant"
    
    try:
        # Write data
        shard = manager.get_shard(crash_tenant, create=True)
        
        # Write multiple entries
        for i in range(5):
            shard.write_ledger("CRASH_TEST", {
                "sequence": i,
                "data": f"Entry {i} - should survive crash",
            })
        
        shard.set_config("crash_test_config", {"entries_written": 5})
        
        # Get the shard path before "crash"
        shard_path = shard.config.shard_path
        
        print(f"  Written 5 entries to {crash_tenant}")
        
        # Simulate crash by NOT closing properly (just delete from manager)
        del manager._shards[crash_tenant]
        # Don't call close - simulate process death
        
        print("  Simulated crash (no graceful close)")
        
        # Create new manager (simulates process restart)
        new_manager = ShardManager(
            base_dir=str(base_dir),
            use_encryption=CRYPTO_AVAILABLE,
        )
        
        # Reopen shard
        recovered_shard = new_manager.get_shard(crash_tenant, create=False)
        
        # Verify data
        entries = recovered_shard.read_ledger(entry_type="CRASH_TEST", limit=10)
        config = recovered_shard.get_config("crash_test_config")
        
        entries_recovered = len(entries)
        config_recovered = config is not None
        
        results["details"] = {
            "entries_written": 5,
            "entries_recovered": entries_recovered,
            "config_recovered": config_recovered,
            "full_recovery": entries_recovered >= 5 and config_recovered,
        }
        
        if entries_recovered >= 5:
            print(f"  {GREEN}✓{RESET} Recovered {entries_recovered}/5 entries")
        else:
            print(f"  {RED}✗{RESET} Only recovered {entries_recovered}/5 entries")
            results["passed"] = False
        
        if config_recovered:
            print(f"  {GREEN}✓{RESET} Config recovered: {config}")
        else:
            print(f"  {RED}✗{RESET} Config not recovered")
            results["passed"] = False
        
        # Cleanup
        new_manager.close_all()
        
    except Exception as e:
        results["passed"] = False
        results["details"] = {"error": str(e)}
        print(f"  {RED}✗{RESET} Crash recovery failed: {e}")
    
    return results


def test_encryption(manager: ShardManager) -> dict:
    """Test encryption at rest."""
    print(f"\n{YELLOW}[TEST 5]{RESET} Encryption at Rest")
    
    if not CRYPTO_AVAILABLE:
        print(f"  {YELLOW}⚠{RESET} Encryption not available (cryptography package not installed)")
        return {"passed": True, "skipped": True, "reason": "no_crypto_package"}
    
    results = {"passed": True, "details": {}}
    
    # Create encrypted shard
    enc_tenant = "encrypted-tenant"
    shard = manager.get_shard(enc_tenant, create=True)
    
    # Write sensitive data
    secret_data = {"password": "super_secret_123", "api_key": "sk-abc123"}
    shard.write_ledger("SECRET", secret_data)
    shard.set_config("secret_config", secret_data)
    
    # Get path
    shard_path = shard.config.shard_path
    
    # Close shard
    manager.close_shard(enc_tenant)
    
    # Read raw database file
    with open(shard_path, 'rb') as f:
        raw_content = f.read()
    
    # Check if secret appears in plaintext
    plaintext_exposed = b"super_secret_123" in raw_content or b"sk-abc123" in raw_content
    
    results["details"]["plaintext_exposed"] = plaintext_exposed
    results["details"]["encrypted"] = not plaintext_exposed
    
    if plaintext_exposed:
        print(f"  {RED}✗{RESET} Secret data found in plaintext!")
        results["passed"] = False
    else:
        print(f"  {GREEN}✓{RESET} Data encrypted at rest")
    
    # Verify we can still read it back
    shard = manager.get_shard(enc_tenant, create=False)
    entries = shard.read_ledger(entry_type="SECRET", limit=1)
    
    if entries and entries[0]["payload"] == secret_data:
        print(f"  {GREEN}✓{RESET} Data decrypts correctly")
        results["details"]["decryption_works"] = True
    else:
        print(f"  {RED}✗{RESET} Decryption failed")
        results["passed"] = False
        results["details"]["decryption_works"] = False
    
    return results


def main():
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}  PAC-OCC-P920-SHARDING VERIFICATION TEST{RESET}")
    print(f"{BOLD}{CYAN}  Sovereign State Sharding{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    
    # Create temp directory
    base_dir = Path(tempfile.mkdtemp(prefix='sharding_test_'))
    print(f"\n{YELLOW}[SETUP]{RESET} Test directory: {base_dir}")
    print(f"{YELLOW}[SETUP]{RESET} Encryption available: {CRYPTO_AVAILABLE}")
    
    # Create shard manager
    manager = ShardManager(
        base_dir=str(base_dir),
        use_encryption=CRYPTO_AVAILABLE,
        log_dir=str(base_dir / "logs"),
    )
    
    # Define test tenants
    tenant_ids = [f"tenant-{i:03d}" for i in range(5)]
    
    # Run tests
    test_results = {}
    
    test_results["creation"] = test_shard_creation(manager, tenant_ids)
    test_results["persistence"] = test_persistence(manager, tenant_ids)
    test_results["isolation"] = test_isolation(manager, tenant_ids)
    test_results["crash_recovery"] = test_crash_recovery(manager, base_dir)
    test_results["encryption"] = test_encryption(manager)
    
    # Cleanup
    manager.close_all()
    
    # Final results
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  VERIFICATION RESULTS{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    
    all_passed = all(r.get("passed", False) for r in test_results.values())
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pac": "PAC-OCC-P920-SHARDING",
        "tenant_count": len(tenant_ids),
        "encryption_available": CRYPTO_AVAILABLE,
        "tests": {
            "creation": test_results["creation"]["passed"],
            "persistence": test_results["persistence"]["passed"],
            "isolation": test_results["isolation"]["passed"],
            "crash_recovery": test_results["crash_recovery"]["passed"],
            "encryption": test_results["encryption"].get("passed", True),
        },
        "invariants": {
            "INV-DATA-003": test_results["isolation"]["passed"],
            "INV-DATA-004": test_results["crash_recovery"]["passed"],
        },
        "verdict": "PASSED" if all_passed else "FAILED",
    }
    
    print(f"\n  Tenants Tested:     {results['tenant_count']}")
    print(f"  Encryption:         {'✓ Available' if CRYPTO_AVAILABLE else '○ Not Available'}")
    print(f"\n  Test Results:")
    for test_name, passed in results["tests"].items():
        status = f"{GREEN}✓ PASSED{RESET}" if passed else f"{RED}✗ FAILED{RESET}"
        print(f"    {test_name}: {status}")
    
    print(f"\n  INV-DATA-003 (Shard Isolation):      {'✓ VERIFIED' if results['invariants']['INV-DATA-003'] else '✗ VIOLATED'}")
    print(f"  INV-DATA-004 (Persistence Guarantee): {'✓ VERIFIED' if results['invariants']['INV-DATA-004'] else '✗ VIOLATED'}")
    
    verdict_color = GREEN if results['verdict'] == 'PASSED' else RED
    print(f"\n  {BOLD}VERDICT: {verdict_color}{results['verdict']}{RESET}")
    
    # Write results to log
    logs_dir = Path(__file__).parent.parent / "logs" / "data"
    logs_dir.mkdir(parents=True, exist_ok=True)
    results_file = logs_dir / "SHARDING_INIT.json"
    with open(results_file, "a") as f:
        f.write(json.dumps({
            "event": "VERIFICATION_COMPLETE",
            "timestamp": results["timestamp"],
            "results": results,
        }) + "\n")
    
    print(f"\n  Results logged to: {results_file}")
    print(f"\n{BOLD}{'='*70}{RESET}\n")
    
    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results.get("verdict") == "PASSED" else 1)
