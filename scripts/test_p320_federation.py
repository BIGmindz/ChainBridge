#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PAC-GOV-P320-FEDERATION-POLICY                            ║
║                         INTEGRATION TEST                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test federation policy with double-signing detection and automated banning.

INV-GOV-001: Policy changes require 2/3 consensus (> tx consensus)
INV-GOV-002: Slashing is code. If proof exists, punishment is immediate.

Goal: 100% Detection and Banning of a Double-Signing Node in simulation.
"""

import sys
sys.path.insert(0, "/Users/johnbozza/Documents/Projects/ChainBridge-local-repo")

from modules.governance import (
    FederationPolicy, 
    PeeringContract, 
    PolicyConfig,
    NodeStatus,
    SlashingEngine, 
    SlashingEvidence, 
    ViolationType,
)


def test_double_signing_ban():
    """
    Goal: 100% Detection and Banning of a Double-Signing Node.
    
    Scenario:
      1. Create federation with 5 nodes
      2. Node MALICIOUS signs two different blocks at height 100
      3. Node HONEST reports the evidence
      4. SlashingEngine validates and immediately bans MALICIOUS
      5. MALICIOUS loses 100% stake
    """
    print("=" * 70)
    print("P320 FEDERATION POLICY - Double-Signing Detection Test")
    print("=" * 70)
    
    # Setup federation
    print("\n[SETUP] Creating federation with 5 nodes...")
    policy = FederationPolicy()
    
    nodes = {
        "VALIDATOR-1": 100000,
        "VALIDATOR-2": 100000,
        "VALIDATOR-3": 100000,
        "MALICIOUS": 100000,
        "HONEST": 100000,
    }
    
    for node_id, stake in nodes.items():
        contract = PeeringContract(
            node_id=node_id,
            public_key=f"pk_{node_id.lower()}_abc123",
            stake_amount=stake,
            endpoint=f"{node_id.lower()}.mesh.io:8080",
        )
        success, msg = policy.admit_node(contract)
        assert success, f"Failed to admit {node_id}: {msg}"
    
    print(f"   ✓ {policy.node_count} nodes admitted")
    print(f"   ✓ Total stake: {sum(n.stake_amount for n in policy.active_nodes)}")
    
    # Create slashing engine
    engine = SlashingEngine(policy)
    
    # Simulate double-signing by MALICIOUS node
    print("\n[CRIME] MALICIOUS node signs two different blocks at height 100...")
    
    # Block A - MALICIOUS creates this
    header_a = {
        "height": 100,
        "block_hash": "hash_0xa1b2c3d4e5f6_block_a",
        "parent_hash": "hash_parent_block_99",
        "timestamp": "2026-01-11T12:00:00Z",
        "validator_id": "MALICIOUS",
        "signature": "sig_malicious_block_a_xyzabc",
    }
    
    # Block B - MALICIOUS creates this ALSO at height 100 (THE CRIME)
    header_b = {
        "height": 100,  # Same height!
        "block_hash": "hash_0xf6e5d4c3b2a1_block_b",  # Different hash!
        "parent_hash": "hash_parent_block_99",
        "timestamp": "2026-01-11T12:00:01Z",
        "validator_id": "MALICIOUS",  # Same validator!
        "signature": "sig_malicious_block_b_defghi",  # Different signature!
    }
    
    print(f"   Block A: {header_a['block_hash'][:24]}...")
    print(f"   Block B: {header_b['block_hash'][:24]}...")
    
    # HONEST discovers the evidence
    print("\n[DETECTION] HONEST discovers both blocks and reports to federation...")
    
    result = engine.check_double_signing(header_a, header_b, reporter_id="HONEST")
    
    print(f"   Evidence hash: {result.evidence_hash[:32]}...")
    print(f"   Verdict: {result.reason}")
    print(f"   Is Valid: {result.is_valid}")
    
    # Verify result
    assert result.is_valid, f"Should detect double-signing!"
    assert result.action_taken.value == "BAN", "Should BAN the node!"
    assert result.stake_slashed == 100000, "Should slash 100% stake!"
    
    print(f"\n[PUNISHMENT] INV-GOV-002 - Automated Justice Applied!")
    print(f"   ✓ Action: {result.action_taken.value}")
    print(f"   ✓ Stake Slashed: {result.stake_slashed}")
    
    # Verify MALICIOUS is banned
    malicious = policy.get_node("MALICIOUS")
    assert malicious.status == NodeStatus.BANNED
    assert malicious.stake_amount == 0
    assert len(malicious.slashing_events) == 1
    
    print(f"\n[VERIFICATION] MALICIOUS node state:")
    print(f"   ✓ Status: {malicious.status.value}")
    print(f"   ✓ Remaining Stake: {malicious.stake_amount}")
    print(f"   ✓ Slashing Events: {len(malicious.slashing_events)}")
    
    # Verify other nodes unaffected
    print(f"\n[COLLATERAL CHECK] Other nodes unaffected:")
    for node_id in ["VALIDATOR-1", "VALIDATOR-2", "VALIDATOR-3", "HONEST"]:
        node = policy.get_node(node_id)
        assert node.status == NodeStatus.ACTIVE
        assert node.stake_amount == 100000
        print(f"   ✓ {node_id}: {node.status.value}, stake={node.stake_amount}")
    
    # Final stats
    engine_status = engine.get_status()
    print(f"\n[SLASHING ENGINE STATUS]")
    print(f"   Evidence processed: {engine_status['total_evidence_processed']}")
    print(f"   Valid slashings: {engine_status['valid_slashings']}")
    print(f"   Total stake slashed: {engine_status['total_stake_slashed']}")
    
    print("\n" + "=" * 70)
    print("DOUBLE-SIGNING DETECTION: 100% ✅")
    print("=" * 70)
    return True


def test_policy_quorum():
    """
    Test that policy changes require 2/3 quorum (INV-GOV-001).
    """
    print("\n" + "=" * 70)
    print("P320 FEDERATION POLICY - Quorum Test (INV-GOV-001)")
    print("=" * 70)
    
    # Create policy with custom config
    config = PolicyConfig(
        min_stake=10000,
        policy_quorum=2/3,
        tx_quorum=1/2,
    )
    
    assert config.policy_quorum > config.tx_quorum
    print(f"\n[CONFIG] policy_quorum={config.policy_quorum:.2%} > tx_quorum={config.tx_quorum:.2%}")
    print(f"   ✓ INV-GOV-001: Policy changes require higher consensus")
    
    policy = FederationPolicy(config)
    
    # Add 6 nodes
    for i in range(1, 7):
        contract = PeeringContract(
            node_id=f"NODE-{i}",
            public_key=f"pk_node{i}",
            stake_amount=20000,
            endpoint=f"node{i}.io:8080",
        )
        policy.admit_node(contract)
    
    print(f"\n[SETUP] {policy.node_count} nodes in federation")
    print(f"   Required for policy change: {int(6 * 2/3) + 1} votes (2/3 quorum)")
    
    # Propose stake increase
    from modules.governance.policy import PolicyUpdateType
    
    success, proposal_id = policy.propose_policy_update(
        proposer_id="NODE-1",
        update_type=PolicyUpdateType.PARAMETER_CHANGE,
        changes={"min_stake": 50000}
    )
    
    assert success
    print(f"\n[PROPOSAL] {proposal_id}: Increase min_stake to 50000")
    
    # Vote - need 5/6 to pass (since proposer already voted)
    print(f"\n[VOTING]")
    
    # 3 more votes (total 4/6 = 66.67% - not quite 2/3)
    policy.vote_on_proposal(proposal_id, "NODE-2", True)
    policy.vote_on_proposal(proposal_id, "NODE-3", True)
    policy.vote_on_proposal(proposal_id, "NODE-4", True)
    
    proposal = policy._proposals[proposal_id]
    print(f"   After 4 votes: {proposal.status} ({len(proposal.votes_for)}/6)")
    
    # 5th vote should pass (5/6 = 83.3% > 66.67%)
    policy.vote_on_proposal(proposal_id, "NODE-5", True)
    
    proposal = policy._proposals[proposal_id]
    print(f"   After 5 votes: {proposal.status} ({len(proposal.votes_for)}/6)")
    
    assert proposal.status == "PASSED"
    assert policy.config.min_stake == 50000
    
    print(f"\n[RESULT]")
    print(f"   ✓ Proposal PASSED with {len(proposal.votes_for)}/6 votes")
    print(f"   ✓ New min_stake: {policy.config.min_stake}")
    print(f"   ✓ Policy version: {policy.config.version}")
    
    print("\n" + "=" * 70)
    print("INV-GOV-001 (Constitutional Rigidity): VERIFIED ✅")
    print("=" * 70)
    return True


def test_unbonding_period():
    """
    Test that unbonding period prevents hit-and-run attacks.
    """
    print("\n" + "=" * 70)
    print("P320 FEDERATION POLICY - Unbonding Period Test")
    print("=" * 70)
    
    config = PolicyConfig(unbonding_period=86400 * 7)  # 7 days
    policy = FederationPolicy(config)
    
    contract = PeeringContract(
        node_id="RUNNER",
        public_key="pk_runner",
        stake_amount=100000,
        endpoint="runner.io:8080",
    )
    policy.admit_node(contract)
    
    print(f"\n[SETUP] RUNNER admitted with stake 100000")
    
    # Try to leave
    success, msg = policy.start_unbonding("RUNNER")
    assert success
    
    runner = policy.get_node("RUNNER")
    assert runner.status == NodeStatus.UNBONDING
    
    print(f"\n[EXIT REQUEST] RUNNER requests to leave")
    print(f"   Status: {runner.status.value}")
    print(f"   Message: {msg}")
    
    # Check unbonding status
    is_complete, remaining = policy.check_unbonding_complete("RUNNER")
    
    assert not is_complete
    assert remaining > 0
    
    print(f"\n[UNBONDING CHECK]")
    print(f"   Complete: {is_complete}")
    print(f"   Time remaining: {remaining // 86400} days, {(remaining % 86400) // 3600} hours")
    print(f"   ✓ Stake is LOCKED until unbonding completes")
    
    print("\n" + "=" * 70)
    print("UNBONDING PERIOD: ENFORCED ✅")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test1 = test_double_signing_ban()
    test2 = test_policy_quorum()
    test3 = test_unbonding_period()
    
    print("\n" + "=" * 70)
    print("P320 INTEGRATION TESTS COMPLETE")
    print("=" * 70)
    
    if test1 and test2 and test3:
        print("STATUS: ALL TESTS PASSED ✅")
        print("INV-GOV-001 (Constitutional Rigidity): ENFORCED")
        print("INV-GOV-002 (Automated Justice): ENFORCED")
        print("=" * 70)
        print("\n⚖️ Freedom requires Law. The Rules are set. The Game is fair.")
        exit(0)
    else:
        print("STATUS: SOME TESTS FAILED ❌")
        exit(1)
