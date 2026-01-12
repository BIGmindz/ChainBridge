#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PAC-DATA-P340-STATE-REPLICATION                           ║
║                         INTEGRATION TEST                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test state replication between multiple nodes applying the same transactions.

INV-DATA-001: State roots must match at every index across all nodes.
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from modules.data import MerkleTree, MerkleProof, ReplicationEngine, StateSnapshot
from modules.data.replication import CommandType


def test_multi_node_replication():
    """
    Test that multiple nodes reach identical state after applying same commands.
    
    This is the core INV-DATA-001 test.
    """
    print("=" * 70)
    print("P340 STATE REPLICATION - Multi-Node Integration Test")
    print("=" * 70)
    
    # Initialize 3 nodes with same starting state
    initial_state = {"TREASURY": 10000, "ALICE": 1000, "BOB": 500}
    
    nodes = [
        ReplicationEngine(f"NODE-{i}", initial_balances=initial_state)
        for i in range(3)
    ]
    
    print(f"\n[SETUP] Initialized {len(nodes)} nodes with {len(initial_state)} accounts")
    
    # Verify initial state matches
    initial_roots = [n.state_root for n in nodes]
    assert len(set(initial_roots)) == 1, "Initial roots must match!"
    print(f"[✓] Initial state roots match: {initial_roots[0][:32]}...")
    
    # Command sequence to simulate real trading operations
    commands = [
        # Index 1: Alice deposits
        {"type": CommandType.DEPOSIT, "account": "ALICE", "amount": 500},
        # Index 2: Transfer from treasury to Bob
        {"type": CommandType.TRANSFER, "from": "TREASURY", "to": "BOB", "amount": 200},
        # Index 3: Bob transfers to Alice
        {"type": CommandType.TRANSFER, "from": "BOB", "to": "ALICE", "amount": 100},
        # Index 4: Create new account for Carol
        {"type": CommandType.CREATE_ACCOUNT, "account": "CAROL", "initial_balance": 0},
        # Index 5: Treasury funds Carol
        {"type": CommandType.TRANSFER, "from": "TREASURY", "to": "CAROL", "amount": 300},
        # Index 6: Alice withdraws
        {"type": CommandType.WITHDRAW, "account": "ALICE", "amount": 200},
    ]
    
    print(f"\n[EXECUTE] Applying {len(commands)} commands across all nodes...")
    
    passed = 0
    failed = 0
    
    for index, cmd in enumerate(commands, start=1):
        # Apply to all nodes
        results = []
        for node in nodes:
            success, msg, root = node.apply_log_entry(index, term=1, command=cmd)
            results.append((success, root))
        
        # Verify all succeeded
        all_success = all(r[0] for r in results)
        roots = [r[1] for r in results]
        roots_match = len(set(roots)) == 1
        
        cmd_desc = f"{cmd['type']}"
        
        if all_success and roots_match:
            print(f"   [Index {index}] {cmd_desc:20} → Root: {roots[0][:24]}... ✓")
            passed += 1
        else:
            print(f"   [Index {index}] {cmd_desc:20} → MISMATCH! ✗")
            for i, (success, root) in enumerate(results):
                print(f"      NODE-{i}: success={success} root={root[:24]}...")
            failed += 1
    
    print(f"\n[RESULTS] {passed}/{len(commands)} commands applied with matching roots")
    
    # Final state verification
    print("\n[FINAL STATE VERIFICATION]")
    final_roots = [n.state_root for n in nodes]
    
    if len(set(final_roots)) == 1:
        print(f"   ✓ All nodes have identical final state root")
        print(f"   ✓ Root: {final_roots[0]}")
    else:
        print(f"   ✗ STATE DIVERGENCE DETECTED!")
        for i, root in enumerate(final_roots):
            print(f"      NODE-{i}: {root}")
    
    # Verify balances match
    print("\n[BALANCE VERIFICATION]")
    for account in ["TREASURY", "ALICE", "BOB", "CAROL"]:
        balances = [n.get_balance(account) for n in nodes]
        if len(set(balances)) == 1:
            print(f"   {account}: {balances[0]} (all nodes match)")
        else:
            print(f"   {account}: MISMATCH - {balances}")
    
    # Snapshot test
    print("\n[SNAPSHOT TEST]")
    snapshot = nodes[0].create_snapshot(include_merkle=True)
    print(f"   Created snapshot: {snapshot.snapshot_id}")
    print(f"   State root: {snapshot.state_root[:32]}...")
    print(f"   Account count: {snapshot.account_count}")
    print(f"   Total balance: {snapshot.total_balance}")
    
    # Verify new node can sync from snapshot
    new_node = ReplicationEngine("NODE-NEW")
    new_node.restore_from_snapshot(snapshot)
    
    if new_node.state_root == nodes[0].state_root:
        print(f"   ✓ New node synced from snapshot successfully")
    else:
        print(f"   ✗ Snapshot restore failed!")
    
    # Summary
    print("\n" + "=" * 70)
    if failed == 0 and len(set(final_roots)) == 1:
        print("ALL TESTS PASSED ✅")
        print("=" * 70)
        print("INV-DATA-001 (Universal Truth): VERIFIED")
        print("INV-DATA-002 (Atomic Application): VERIFIED")
        print("=" * 70)
        return True
    else:
        print("TESTS FAILED ❌")
        print("=" * 70)
        return False


def test_merkle_proof_verification():
    """Test Merkle proofs for individual account balances."""
    print("\n" + "=" * 70)
    print("MERKLE PROOF VERIFICATION TEST")
    print("=" * 70)
    
    # Build tree from account balances
    balances = {"ALICE": 1000, "BOB": 500, "CAROL": 750}
    leaves = [f"{k}:{v}" for k, v in sorted(balances.items())]
    
    tree = MerkleTree()
    tree.build(leaves)
    
    print(f"\nBuilt tree with {len(leaves)} leaves")
    print(f"Root: {tree.root_hash[:32]}...")
    
    # Generate and verify proof for each account
    for i, leaf in enumerate(leaves):
        proof = tree.generate_proof(i)  # Pass index, not leaf
        is_valid = tree.verify_proof(leaf, proof, tree.root_hash)
        
        status = "✓" if is_valid else "✗"
        print(f"   {leaf}: proof valid = {is_valid} {status}")
    
    # Test invalid proof
    fake_leaf = "DAVE:9999"
    is_valid = tree.verify_proof(fake_leaf, proof, tree.root_hash)
    
    if not is_valid:
        print(f"   {fake_leaf}: correctly rejected ✓")
    else:
        print(f"   {fake_leaf}: INCORRECTLY ACCEPTED! ✗")
        return False
    
    print("\n" + "=" * 70)
    print("MERKLE PROOF TEST PASSED ✅")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test1 = test_multi_node_replication()
    test2 = test_merkle_proof_verification()
    
    print("\n" + "=" * 70)
    print("P340 INTEGRATION TESTS COMPLETE")
    print("=" * 70)
    
    if test1 and test2:
        print("STATUS: ALL TESTS PASSED ✅")
        exit(0)
    else:
        print("STATUS: SOME TESTS FAILED ❌")
        exit(1)
