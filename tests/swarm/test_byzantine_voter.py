"""
Test Suite for Byzantine Consensus Voter (P822)
===============================================

PAC-P822-AGENT-COORDINATION-LAYER | LAW-TIER
Constitutional Mandate: PAC-CAMPAIGN-P820-P825

Test Coverage:
- VOTE-01: 2/3+1 supermajority consensus enforcement
- VOTE-02: SCRAM pre-flight check (fail-closed behavior)
- VOTE-03: Byzantine attack detection (>33% invalid proofs)
- Integration with existing PAC-44 diversity parity and NIST compliance
"""

import pytest
import asyncio
import threading
from typing import List
from core.swarm.byzantine_voter import (
    ByzantineVoter,
    AgentProof,
    AgentCore,
    ConsensusStatus,
    ConsensusResult
)
from core.swarm.agent import Agent
from core.governance.scram import get_scram_controller, SCRAMController


@pytest.fixture
def reset_scram():
    """Reset SCRAM singleton before each test to ensure ARMED state."""
    # Reset singleton to get fresh ARMED instance
    SCRAMController._instance = None
    SCRAMController._lock = threading.RLock()
    scram = get_scram_controller()  # Now in ARMED state
    yield scram
    # Cleanup
    SCRAMController._instance = None


@pytest.fixture
def voter():
    """Create ByzantineVoter for 100 agents (simplified for tests)."""
    return ByzantineVoter(swarm_size=100)


@pytest.fixture
def voter_10k():
    """Create ByzantineVoter for 10,000 agents (PAC-44 production scale)."""
    return ByzantineVoter(swarm_size=10000)


class TestVoteInvariant01_SupermajorityConsensus:
    """
    VOTE-01 Verification: 2/3+1 Supermajority Threshold
    
    Constitutional requirement: Consensus requires 2/3+1 of swarm_size valid proofs.
    For 100 agents: threshold = 2*100//3 + 1 = 67
    For 10,000 agents: threshold = 2*10000//3 + 1 = 6,667
    """
    
    @pytest.mark.asyncio
    async def test_consensus_with_exact_threshold(self, voter: ByzantineVoter):
        """VOTE-01.1: Consensus succeeds with exactly 2/3+1 valid proofs."""
        # 67 valid proofs (exactly threshold for 100 agents)
        # Balanced diversity: 34 LATTICE, 33 HEURISTIC (50.7% vs 49.3% ≈ 50/50)
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 34 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(67)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert result.quorum_count == 67
        assert result.threshold == 67
    
    @pytest.mark.asyncio
    async def test_consensus_fails_below_threshold(self, voter: ByzantineVoter):
        """VOTE-01.2: Consensus fails with 66 valid proofs (1 below threshold)."""
        # 66 valid proofs (below threshold of 67)
        # Balanced diversity: 33 LATTICE, 33 HEURISTIC
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 33 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(66)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.QUORUM_FAILURE
        assert result.quorum_count == 66
        assert result.threshold == 67
        assert "Quorum failure" in result.reason
    
    @pytest.mark.asyncio
    async def test_consensus_with_above_threshold(self, voter: ByzantineVoter):
        """VOTE-01.3: Consensus succeeds with 80 valid proofs (above threshold)."""
        # 80 valid proofs (well above threshold of 67)
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 40 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(80)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert result.quorum_count == 80
    
    @pytest.mark.asyncio
    async def test_10k_agent_threshold(self, voter_10k: ByzantineVoter):
        """VOTE-01.4: Verify 2/3+1 threshold for 10,000 agents = 6,667."""
        assert voter_10k.threshold == 6667
        
        # 6,667 valid proofs (exactly threshold)
        # Balanced diversity: 3334 LATTICE, 3333 HEURISTIC (50.0% vs 49.98% ≈ 50/50)
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 3334 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(6667)
        ]
        
        result = await voter_10k.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert result.quorum_count == 6667


class TestVoteInvariant02_SCRAMPreFlight:
    """
    VOTE-02 Verification: SCRAM Pre-Flight Check
    
    Constitutional requirement: verify_consensus() MUST check SCRAM status
    before processing proofs. If SCRAM is ACTIVE (activated), immediately return SCRAM_ABORT.
    Note: SCRAM starts in ARMED state (ready) - must be activated to trigger abort.
    """
    
    @pytest.mark.asyncio
    async def test_scram_abort_when_activated(self, voter: ByzantineVoter, reset_scram):
        """VOTE-02.1: Consensus aborts immediately when SCRAM is activated."""
        from core.governance.scram import SCRAMReason
        
        # Activate SCRAM (transitions from ARMED to ACTIVATING/EXECUTING)
        reset_scram.activate(reason=SCRAMReason.SECURITY_BREACH, metadata={"test": "P822"})
        
        # Prepare 100 valid proofs (should be ignored due to SCRAM activation)
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 50 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(100)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.SCRAM_ABORT
        assert result.quorum_count == 0  # No proofs processed
        assert "SCRAM_ABORT" in result.reason
        assert "security_breach" in result.reason.lower()  # Enum value is lowercase
    
    @pytest.mark.asyncio
    async def test_scram_fail_closed_behavior(self, voter: ByzantineVoter, reset_scram):
        """VOTE-02.2: SCRAM fail-closed - even perfect consensus rejected when activated."""
        from core.governance.scram import SCRAMReason
        
        # Activate SCRAM
        reset_scram.activate(reason=SCRAMReason.INVARIANT_VIOLATION, metadata={"invariant": "VOTE-01"})
        
        # 100% perfect consensus (all valid, perfect diversity, NIST compliant)
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 50 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(100)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.SCRAM_ABORT
        assert result.nist_compliant is False
        assert "invariant_violation" in result.reason.lower()  # Enum value is lowercase
    
    @pytest.mark.asyncio
    async def test_normal_operation_when_scram_armed_only(self, voter: ByzantineVoter, reset_scram):
        """VOTE-02.3: Normal consensus when SCRAM is ARMED but NOT activated."""
        # Ensure SCRAM is ARMED (ready) but not ACTIVE
        assert reset_scram.is_armed
        assert not reset_scram.is_active
        
        # 80 valid proofs (above threshold)
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 40 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(80)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert result.quorum_count == 80


class TestVoteInvariant03_ByzantineAttackDetection:
    """
    VOTE-03 Verification: Byzantine Attack Detection
    
    Constitutional requirement: Detect when >33% of proofs are invalid.
    Byzantine fault tolerance requires <33% traitors for consensus validity.
    """
    
    @pytest.mark.asyncio
    async def test_byzantine_detection_at_34_percent_invalid(self, voter: ByzantineVoter):
        """VOTE-03.1: Detect Byzantine attack with 34% invalid proofs."""
        # 67 valid, 34 invalid = 34% invalid (above 33% threshold)
        # Balanced diversity: 34 LATTICE, 33 HEURISTIC valid
        valid_proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 34 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(67)
        ]
        
        invalid_proofs = [
            AgentProof(
                agent_id=f"traitor-{i}",
                core_type=AgentCore.LATTICE if i < 17 else AgentCore.HEURISTIC,
                valid=False,
                fips_204_compliant=False,
                fips_203_compliant=False
            )
            for i in range(34)
        ]
        
        result = await voter.verify_consensus(valid_proofs + invalid_proofs)
        
        # Should reach consensus but detect Byzantine agents
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert len(result.byzantine_agents) == 34
        assert result.quorum_count == 67
    
    @pytest.mark.asyncio
    async def test_byzantine_agents_tracked(self, voter: ByzantineVoter):
        """VOTE-03.2: Byzantine agent IDs are tracked in result."""
        # 80 valid, 20 invalid
        valid_proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 40 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(80)
        ]
        
        invalid_proofs = [
            AgentProof(
                agent_id=f"traitor-{i}",
                core_type=AgentCore.LATTICE,
                valid=False,
                fips_204_compliant=False,
                fips_203_compliant=False
            )
            for i in range(20)
        ]
        
        result = await voter.verify_consensus(valid_proofs + invalid_proofs)
        
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert len(result.byzantine_agents) == 20
        for i in range(20):
            assert f"traitor-{i}" in result.byzantine_agents


class TestAgentIntegration:
    """
    Test Agent stub integration with ByzantineVoter.
    """
    
    @pytest.mark.asyncio
    async def test_honest_agent_generates_valid_proof(self):
        """Agent.1: Honest agent generates valid proof."""
        agent = Agent(agent_id="honest-001", is_honest=True)
        proof = agent.generate_proof(batch_id="batch-123", core_type="LATTICE")
        
        assert proof.agent_id == "honest-001"
        assert proof.valid is True
        assert proof.core_type == AgentCore.LATTICE
        assert proof.fips_204_compliant is True
        assert proof.fips_203_compliant is True
    
    @pytest.mark.asyncio
    async def test_dishonest_agent_generates_invalid_proof(self):
        """Agent.2: Dishonest agent generates invalid proof."""
        agent = Agent(agent_id="traitor-001", is_honest=False)
        proof = agent.generate_proof(batch_id="batch-123", core_type="HEURISTIC")
        
        assert proof.agent_id == "traitor-001"
        assert proof.valid is False
        assert proof.core_type == AgentCore.HEURISTIC
        assert proof.fips_204_compliant is False
        assert proof.fips_203_compliant is False
    
    @pytest.mark.asyncio
    async def test_swarm_consensus_with_agent_proofs(self, voter: ByzantineVoter):
        """Agent.3: Consensus verification with agent-generated proofs."""
        # Create 80 honest agents, 20 dishonest
        honest_agents = [Agent(f"honest-{i}", is_honest=True) for i in range(80)]
        dishonest_agents = [Agent(f"traitor-{i}", is_honest=False) for i in range(20)]
        
        # Generate proofs
        honest_proofs = [
            agent.generate_proof(
                "batch-123",
                core_type="LATTICE" if i < 40 else "HEURISTIC"
            )
            for i, agent in enumerate(honest_agents)
        ]
        
        dishonest_proofs = [
            agent.generate_proof("batch-123", core_type="LATTICE")
            for agent in dishonest_agents
        ]
        
        result = await voter.verify_consensus(honest_proofs + dishonest_proofs)
        
        assert result.status == ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED
        assert result.quorum_count == 80
        assert len(result.byzantine_agents) == 20


class TestPAC44Compatibility:
    """
    Test PAC-44 diversity parity and NIST compliance (preserved from existing implementation).
    """
    
    @pytest.mark.asyncio
    async def test_diversity_parity_enforcement(self, voter: ByzantineVoter):
        """PAC-44.1: Diversity collapse detected when core imbalance exceeds threshold."""
        # All 100 proofs from LATTICE core (0 HEURISTIC) = 100% imbalance
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE,
                valid=True,
                fips_204_compliant=True,
                fips_203_compliant=True
            )
            for i in range(100)
        ]
        
        result = await voter.verify_consensus(proofs)
        
        # Should fail diversity parity check
        assert result.status == ConsensusStatus.DIVERSITY_COLLAPSE
        assert "Diversity collapse" in result.reason
    
    @pytest.mark.asyncio
    async def test_nist_compliance_enforcement(self, voter: ByzantineVoter):
        """PAC-44.2: NIST compliance violation when FIPS 204/203 not met."""
        # 80 valid proofs but NOT NIST compliant
        proofs = [
            AgentProof(
                agent_id=f"agent-{i}",
                core_type=AgentCore.LATTICE if i < 40 else AgentCore.HEURISTIC,
                valid=True,
                fips_204_compliant=False,  # NOT compliant
                fips_203_compliant=False
            )
            for i in range(80)
        ]
        
        result = await voter.verify_consensus(proofs, enforce_nist=True)
        
        assert result.status == ConsensusStatus.NIST_VIOLATION
        assert "NIST FIPS 204/203" in result.reason
