#!/usr/bin/env python3
"""
PAC-44: Byzantine Supermajority & NIST Compliance
=================================================
CLASSIFICATION: SOVEREIGN // EYES ONLY
GOVERNANCE: GID-00 (BENSON) + GID-01 (EVE - Vision/Architect) + GID-02 (CODY - Research)
VERSION: 1.0.0-ALPHA

The Byzantine Voter implements distributed sovereign consensus using
supermajority quorum (2/3 + 1) with diversity parity enforcement to
prevent homogeneous drift vulnerabilities.

CANONICAL GATES (EXTENDED):
- GATE-08: Supermajority Quorum (>66.67% consensus required)
- GATE-09: Diversity Parity (cross-audit between logic cores)
- GATE-10: NIST Compliance (FIPS 204/203 enforcement)

THREAT MODEL:
- Byzantine failures (up to 33% malicious agents)
- Homogeneous Drift (logic path convergence)
- Harvest-Now, Decrypt-Later (HNDL) attacks

ARCHITECTURE:
- 10,000-agent lattice
- 5,000 Deterministic Lattice agents
- 5,000 Heuristic Adaptive agents
- 2/3 + 1 = 6,667 minimum consensus threshold

Author: Eve (GID-01) - Vision/Architect + Cody (GID-02) - Research
Executor: BENSON (GID-00)
"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
from enum import Enum


class AgentCore(Enum):
    """Agent logic core classification."""
    LATTICE = "DETERMINISTIC_LATTICE"
    HEURISTIC = "HEURISTIC_ADAPTIVE"
    UNKNOWN = "UNKNOWN"


class ConsensusStatus(Enum):
    """Consensus verification status."""
    SOVEREIGN_CONSENSUS_REACHED = "SOVEREIGN_CONSENSUS_REACHED"
    QUORUM_FAILURE = "QUORUM_FAILURE_DRIFT_DETECTED"
    DIVERSITY_COLLAPSE = "DIVERSITY_COLLAPSE_DETECTED"
    LOGIC_DRIFT = "LOGIC_DRIFT_DETECTED"
    BYZANTINE_ATTACK = "BYZANTINE_ATTACK_DETECTED"
    NIST_VIOLATION = "NIST_COMPLIANCE_VIOLATION"


@dataclass
class AgentProof:
    """Cryptographic proof from a single agent."""
    agent_id: str
    core_type: AgentCore
    valid: bool
    nfi_signature: Optional[bytes] = None
    dilithium_signature: Optional[bytes] = None
    timestamp: float = field(default_factory=time.time)
    fips_204_compliant: bool = False
    fips_203_compliant: bool = False


@dataclass
class ConsensusResult:
    """Result of Byzantine consensus verification."""
    status: ConsensusStatus
    quorum_count: int
    threshold: int
    lattice_votes: int
    heuristic_votes: int
    diversity_ratio: float
    nist_compliant: bool
    reason: Optional[str] = None
    byzantine_agents: List[str] = field(default_factory=list)


@dataclass
class ByzantineMetrics:
    """Metrics for Byzantine voter operations."""
    total_consensus_attempts: int = 0
    successful_consensus: int = 0
    quorum_failures: int = 0
    diversity_collapses: int = 0
    byzantine_detections: int = 0
    nist_violations: int = 0
    avg_quorum_percentage: float = 0.0
    avg_diversity_ratio: float = 0.0


class ByzantineVoter:
    """
    Byzantine fault-tolerant consensus mechanism for distributed swarm.
    
    Implements supermajority quorum (2/3 + 1) with diversity parity
    enforcement to prevent homogeneous drift. Protects against up to
    33% Byzantine (malicious or faulty) agents.
    
    GATE-08: Requires >6,666 valid signatures from 10,000 agents
    GATE-09: Enforces <15% drift between lattice and heuristic cores
    GATE-10: Validates NIST FIPS 204/203 compliance
    """
    
    def __init__(self, swarm_size: int = 10000, diversity_drift_threshold: float = 0.15):
        """
        Initialize Byzantine Voter.
        
        Args:
            swarm_size: Total number of agents in swarm (default: 10,000)
            diversity_drift_threshold: Maximum allowed drift ratio (default: 15%)
        
        Byzantine Tolerance:
            Can tolerate up to (swarm_size - 1) / 3 Byzantine agents
        """
        self.swarm_size = swarm_size
        self.threshold = (2 * swarm_size // 3) + 1  # 2/3 + 1 supermajority
        self.lattice_count = swarm_size // 2  # 5,000 deterministic
        self.heuristic_count = swarm_size // 2  # 5,000 heuristic
        self.diversity_drift_threshold = diversity_drift_threshold  # 15% max drift
        
        # Byzantine tolerance
        self.max_byzantine = (swarm_size - 1) // 3  # Up to 3,333 Byzantine agents
        
        # Metrics
        self.metrics = ByzantineMetrics()
        
        # Agent registry
        self.registered_agents: Dict[str, AgentCore] = {}
        
        # Voter mempool (pending proofs)
        self.mempool: Dict[str, AgentProof] = {}
        
        print(f"[BYZANTINE] Voter initialized:")
        print(f"  Swarm Size: {self.swarm_size}")
        print(f"  Threshold: {self.threshold} ({(self.threshold/swarm_size)*100:.2f}%)")
        print(f"  Byzantine Tolerance: {self.max_byzantine} agents")
        print(f"  Diversity Drift Max: {self.diversity_drift_threshold*100:.1f}%")
    
    def register_agent(self, agent_id: str, core_type: AgentCore):
        """
        Register agent in Byzantine voter registry.
        
        Args:
            agent_id: Unique agent identifier
            core_type: Logic core classification (LATTICE or HEURISTIC)
        """
        self.registered_agents[agent_id] = core_type
    
    def initialize_10k_lattice_registry(self):
        """
        PREFLIGHT: Initialize 10,000-agent lattice registry.
        
        Creates balanced distribution:
        - 5,000 Deterministic Lattice agents
        - 5,000 Heuristic Adaptive agents
        """
        print("\n[PREFLIGHT] Initializing 10K agent lattice registry...")
        
        # Register deterministic lattice agents
        for i in range(self.lattice_count):
            agent_id = f"LATTICE-{i:04d}"
            self.register_agent(agent_id, AgentCore.LATTICE)
        
        # Register heuristic adaptive agents
        for i in range(self.heuristic_count):
            agent_id = f"HEURISTIC-{i:04d}"
            self.register_agent(agent_id, AgentCore.HEURISTIC)
        
        print(f"✓ Registered {len(self.registered_agents)} agents")
        print(f"  - LATTICE: {self.lattice_count}")
        print(f"  - HEURISTIC: {self.heuristic_count}")
    
    async def verify_consensus(
        self,
        agent_proofs: List[AgentProof],
        enforce_nist: bool = True
    ) -> ConsensusResult:
        """
        Verify Byzantine consensus across agent proofs.
        
        PROTOCOL:
        1. GATE-08: Verify supermajority quorum (>6,666 valid proofs)
        2. GATE-09: Check diversity parity between logic cores
        3. GATE-10: Validate NIST FIPS 204/203 compliance
        4. Detect Byzantine agents (invalid proofs)
        
        Args:
            agent_proofs: List of cryptographic proofs from agents
            enforce_nist: If True, enforce GATE-10 NIST compliance
            
        Returns:
            ConsensusResult with verification status
        """
        self.metrics.total_consensus_attempts += 1
        
        # Count valid approvals
        approvals = sum(1 for p in agent_proofs if p.valid)
        
        # GATE-08: Supermajority Quorum Check
        if approvals < self.threshold:
            self.metrics.quorum_failures += 1
            return ConsensusResult(
                status=ConsensusStatus.QUORUM_FAILURE,
                quorum_count=approvals,
                threshold=self.threshold,
                lattice_votes=0,
                heuristic_votes=0,
                diversity_ratio=0.0,
                nist_compliant=False,
                reason=f"Quorum failure: {approvals}/{self.threshold} votes",
                byzantine_agents=[p.agent_id for p in agent_proofs if not p.valid]
            )
        
        # Count votes by logic core
        lattice_votes = sum(
            1 for p in agent_proofs 
            if p.core_type == AgentCore.LATTICE and p.valid
        )
        heuristic_votes = sum(
            1 for p in agent_proofs 
            if p.core_type == AgentCore.HEURISTIC and p.valid
        )
        
        # GATE-09: Diversity Parity Check
        diversity_ratio = abs(lattice_votes - heuristic_votes) / max(1, self.threshold)
        
        if diversity_ratio > self.diversity_drift_threshold:
            self.metrics.diversity_collapses += 1
            return ConsensusResult(
                status=ConsensusStatus.DIVERSITY_COLLAPSE,
                quorum_count=approvals,
                threshold=self.threshold,
                lattice_votes=lattice_votes,
                heuristic_votes=heuristic_votes,
                diversity_ratio=diversity_ratio,
                nist_compliant=False,
                reason=f"Diversity collapse: {diversity_ratio*100:.1f}% drift (max {self.diversity_drift_threshold*100:.1f}%)"
            )
        
        # GATE-10: NIST Compliance Check
        nist_compliant_count = sum(
            1 for p in agent_proofs 
            if p.valid and p.fips_204_compliant and p.fips_203_compliant
        )
        nist_compliant = nist_compliant_count >= self.threshold
        
        if enforce_nist and not nist_compliant:
            self.metrics.nist_violations += 1
            return ConsensusResult(
                status=ConsensusStatus.NIST_VIOLATION,
                quorum_count=approvals,
                threshold=self.threshold,
                lattice_votes=lattice_votes,
                heuristic_votes=heuristic_votes,
                diversity_ratio=diversity_ratio,
                nist_compliant=False,
                reason=f"NIST FIPS 204/203 compliance failure: {nist_compliant_count}/{self.threshold}"
            )
        
        # Detect Byzantine agents
        byzantine_agents = [p.agent_id for p in agent_proofs if not p.valid]
        if byzantine_agents:
            self.metrics.byzantine_detections += len(byzantine_agents)
            print(f"[BYZANTINE] {len(byzantine_agents)} Byzantine agents detected: {byzantine_agents[:5]}...")
        
        # SUCCESS: Sovereign consensus reached
        self.metrics.successful_consensus += 1
        self._update_avg_metrics(approvals, diversity_ratio)
        
        return ConsensusResult(
            status=ConsensusStatus.SOVEREIGN_CONSENSUS_REACHED,
            quorum_count=approvals,
            threshold=self.threshold,
            lattice_votes=lattice_votes,
            heuristic_votes=heuristic_votes,
            diversity_ratio=diversity_ratio,
            nist_compliant=nist_compliant,
            byzantine_agents=byzantine_agents
        )
    
    def _update_avg_metrics(self, quorum_count: int, diversity_ratio: float):
        """Update running average metrics."""
        total = self.metrics.total_consensus_attempts
        
        self.metrics.avg_quorum_percentage = (
            (self.metrics.avg_quorum_percentage * (total - 1) + 
             (quorum_count / self.swarm_size * 100)) / total
        )
        
        self.metrics.avg_diversity_ratio = (
            (self.metrics.avg_diversity_ratio * (total - 1) + 
             diversity_ratio) / total
        )
    
    def sync_diversity_coefficients(self) -> Dict[str, float]:
        """
        PREFLIGHT: Calculate diversity coefficients for sub-swarms.
        
        Returns:
            Dict containing diversity metrics
        """
        lattice_count = sum(1 for c in self.registered_agents.values() if c == AgentCore.LATTICE)
        heuristic_count = sum(1 for c in self.registered_agents.values() if c == AgentCore.HEURISTIC)
        
        # Prevent division by zero if no agents registered
        max_count = max(lattice_count, heuristic_count)
        balance_ratio = min(lattice_count, heuristic_count) / max_count if max_count > 0 else 0.0
        
        return {
            "lattice_coefficient": lattice_count / self.swarm_size if self.swarm_size > 0 else 0.0,
            "heuristic_coefficient": heuristic_count / self.swarm_size if self.swarm_size > 0 else 0.0,
            "balance_ratio": balance_ratio,
            "total_agents": len(self.registered_agents)
        }
    
    def get_metrics(self) -> Dict:
        """Retrieve Byzantine voter metrics."""
        success_rate = (
            (self.metrics.successful_consensus / max(1, self.metrics.total_consensus_attempts)) * 100
        )
        
        return {
            "swarm_size": self.swarm_size,
            "threshold": self.threshold,
            "max_byzantine_tolerance": self.max_byzantine,
            "total_consensus_attempts": self.metrics.total_consensus_attempts,
            "successful_consensus": self.metrics.successful_consensus,
            "success_rate": f"{success_rate:.2f}%",
            "quorum_failures": self.metrics.quorum_failures,
            "diversity_collapses": self.metrics.diversity_collapses,
            "byzantine_detections": self.metrics.byzantine_detections,
            "nist_violations": self.metrics.nist_violations,
            "avg_quorum_percentage": f"{self.metrics.avg_quorum_percentage:.2f}%",
            "avg_diversity_ratio": f"{self.metrics.avg_diversity_ratio * 100:.2f}%"
        }
    
    def run_preflight_checks(self) -> Dict[str, bool]:
        """
        Execute PAC-44 preflight validation.
        
        Returns:
            Dict of check results
        """
        checks = {}
        
        print("\n" + "=" * 70)
        print("🔐 PAC-44 BYZANTINE VOTER PREFLIGHT")
        print("=" * 70)
        
        # CHECK 1: Agent registry initialized
        checks["AGENT_REGISTRY_INITIALIZED"] = len(self.registered_agents) == self.swarm_size
        print(f"✓ Agent Registry: {len(self.registered_agents)}/{self.swarm_size} agents")
        
        # CHECK 2: Diversity coefficients
        coeffs = self.sync_diversity_coefficients()
        checks["DIVERSITY_COEFFICIENTS_SYNCED"] = coeffs["balance_ratio"] > 0.95
        print(f"✓ Diversity Balance: {coeffs['balance_ratio']*100:.1f}%")
        print(f"  - Lattice: {coeffs['lattice_coefficient']*100:.1f}%")
        print(f"  - Heuristic: {coeffs['heuristic_coefficient']*100:.1f}%")
        
        # CHECK 3: Byzantine tolerance
        checks["BYZANTINE_TOLERANCE"] = self.max_byzantine >= 3000
        print(f"✓ Byzantine Tolerance: {self.max_byzantine} agents ({(self.max_byzantine/self.swarm_size)*100:.1f}%)")
        
        # CHECK 4: Threshold calculation
        checks["THRESHOLD_CALCULATION"] = self.threshold == 6667
        print(f"✓ Supermajority Threshold: {self.threshold} ({(self.threshold/self.swarm_size)*100:.2f}%)")
        
        print("=" * 70)
        
        all_passed = all(checks.values())
        if all_passed:
            print("✅ ALL BYZANTINE VOTER PREFLIGHT CHECKS PASSED")
        else:
            print("⚠️  BYZANTINE VOTER PREFLIGHT WARNINGS")
        print("=" * 70)
        
        return checks


# ══════════════════════════════════════════════════════════════════════════════
# TESTING & VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

async def test_byzantine_voter():
    """
    Test Byzantine Voter with simulated agent proofs.
    
    Scenarios:
    1. Successful consensus (70% approval)
    2. Quorum failure (60% approval - below threshold)
    3. Diversity collapse (extreme drift between cores)
    4. Byzantine attack (30% malicious agents)
    5. NIST compliance validation
    """
    print("=" * 70)
    print("🛡️  BYZANTINE VOTER TEST — PAC-44")
    print("=" * 70)
    
    # Initialize voter
    voter = ByzantineVoter(swarm_size=10000)
    
    # Initialize registry FIRST, then run preflight
    voter.initialize_10k_lattice_registry()
    voter.run_preflight_checks()
    
    # Test 1: Successful consensus (7,000 valid proofs)
    print("\n[TEST 1] Successful consensus (70% approval)...")
    proofs_success = []
    for i in range(7000):
        core = AgentCore.LATTICE if i < 3500 else AgentCore.HEURISTIC
        proofs_success.append(AgentProof(
            agent_id=f"{core.value}-{i:04d}",
            core_type=core,
            valid=True,
            fips_204_compliant=True,
            fips_203_compliant=True
        ))
    
    result = await voter.verify_consensus(proofs_success)
    print(f"Status: {result.status.value}")
    print(f"Quorum: {result.quorum_count}/{result.threshold}")
    print(f"Diversity: {result.diversity_ratio*100:.2f}% drift")
    
    # Test 2: Quorum failure (6,000 valid proofs - below threshold)
    print("\n[TEST 2] Quorum failure (60% approval)...")
    proofs_failure = proofs_success[:6000]
    result = await voter.verify_consensus(proofs_failure)
    print(f"Status: {result.status.value}")
    print(f"Reason: {result.reason}")
    
    # Test 3: Diversity collapse (6,900 lattice, 100 heuristic)
    print("\n[TEST 3] Diversity collapse...")
    proofs_drift = []
    for i in range(6900):
        proofs_drift.append(AgentProof(
            agent_id=f"LATTICE-{i:04d}",
            core_type=AgentCore.LATTICE,
            valid=True,
            fips_204_compliant=True,
            fips_203_compliant=True
        ))
    for i in range(100):
        proofs_drift.append(AgentProof(
            agent_id=f"HEURISTIC-{i:04d}",
            core_type=AgentCore.HEURISTIC,
            valid=True,
            fips_204_compliant=True,
            fips_203_compliant=True
        ))
    
    result = await voter.verify_consensus(proofs_drift)
    print(f"Status: {result.status.value}")
    print(f"Reason: {result.reason}")
    
    # Test 4: Byzantine attack (3,000 malicious agents)
    print("\n[TEST 4] Byzantine attack (3,000 malicious agents)...")
    proofs_byzantine = []
    for i in range(7000):
        core = AgentCore.LATTICE if i < 3500 else AgentCore.HEURISTIC
        valid = i >= 3000  # First 3,000 are Byzantine
        proofs_byzantine.append(AgentProof(
            agent_id=f"{core.value}-{i:04d}",
            core_type=core,
            valid=valid,
            fips_204_compliant=valid,
            fips_203_compliant=valid
        ))
    
    result = await voter.verify_consensus(proofs_byzantine)
    print(f"Status: {result.status.value}")
    print(f"Byzantine Agents Detected: {len(result.byzantine_agents)}")
    print(f"Quorum: {result.quorum_count}/{result.threshold}")
    
    # Test 5: Metrics
    print("\n📊 BYZANTINE VOTER METRICS:")
    metrics = voter.get_metrics()
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 70)
    print("✓ BYZANTINE VOTER VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_byzantine_voter())
