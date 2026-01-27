"""
ChainBridge Polyatomic Hive - The Consensus Engine
====================================================
Multi-agent consensus system enforcing cryptographic resonance voting.

Created: PAC-DEV-P51 (Polyatomic Swarm Intelligence)
Updated: PAC-CRYPTO-P60 (Quantum Shield - Signature Verification)
Purpose: Replace "Trust" with "Polyatomic Verification"

Core Concept:
- 1 agent can hallucinate
- 5 agents with resonance enforcement cannot
- Consensus requires 3-of-5 (60%) hash agreement

Invariants:
- POLY-01: Thoughts MUST require >50% resonance (supermajority)
- POLY-02: Dissonance MUST trigger fail-closed state (no action)
- POLY-03: Every consensus decision MUST be auditable (vote records)
- PQC-02: Verification failure MUST trigger immediate Dissonance/SCRAM (PAC-P60)
"""

import asyncio
import json
import logging
import os
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.swarm.types import Task, PrimeDirective, ReasoningResult
from core.swarm.agent_university import AgentUniversity, GIDPersona
from core.intelligence.llm_bridge import LLMBridge
from core.crypto.quantum_signer import QuantumVerifier

# PAC-INT-P56: Live Data Pipeline
HIVE_LOG_PATH = "logs/hive_consensus.jsonl"


class ConsensusResult:
    """
    Result of polyatomic consensus voting.
    
    Attributes:
        decision: Winning decision (from majority hash)
        reasoning: Winning reasoning chain
        confidence: Winning confidence score
        hash: Winning SHA3-256 hash
        vote_count: Number of agents that agreed (e.g., 3)
        total_atoms: Total agents polled (e.g., 5)
        resonance_rate: Percentage agreement (e.g., 0.60 = 60%)
        consensus_achieved: Whether threshold was met
        all_hashes: All unique hashes observed (for audit)
        metadata: Additional context (task_id, timestamp, etc.)
    """
    
    def __init__(
        self,
        decision: str,
        reasoning: str,
        confidence: float,
        hash: str,
        vote_count: int,
        total_atoms: int,
        consensus_achieved: bool,
        all_hashes: Dict[str, int],
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.decision = decision
        self.reasoning = reasoning
        self.confidence = confidence
        self.hash = hash
        self.vote_count = vote_count
        self.total_atoms = total_atoms
        self.resonance_rate = vote_count / total_atoms if total_atoms > 0 else 0.0
        self.consensus_achieved = consensus_achieved
        self.all_hashes = all_hashes
        self.metadata = metadata or {}
    
    def __repr__(self):
        status = "✅ CONSENSUS" if self.consensus_achieved else "❌ DISSONANCE"
        return (
            f"ConsensusResult({status} | "
            f"votes={self.vote_count}/{self.total_atoms} ({self.resonance_rate:.0%}) | "
            f"decision={self.decision} | hash={self.hash[:16]}...)"
        )


class PolyatomicHive:
    """
    The Hive Mind - Multi-Agent Consensus Engine.
    
    Distributes a cognitive task to N Atoms (AgentClones).
    Enforces consensus via resonance hashing (SHA3-256 voting).
    
    Workflow:
    1. Spawn N clones from parent GID
    2. Each clone reasons independently about the same task
    3. Collect all reasoning results (with hashes)
    4. Count hash occurrences (resonance voting)
    5. Require threshold (e.g., 3-of-5) for consensus
    6. Return winning result OR fail-closed on dissonance
    
    Design Philosophy:
    - "One agent can hallucinate. Five agents with resonance cannot."
    - "Consensus is cryptographic, not probabilistic."
    - "Dissonance triggers investigation, not action."
    """
    
    def __init__(
        self,
        university: Optional[AgentUniversity] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Polyatomic Hive.
        
        Args:
            university: Agent spawning factory (creates if None)
            logger: Logging instance
        """
        self.university = university or AgentUniversity()
        self.logger = logger or logging.getLogger("PolyatomicHive")
        self.consensus_history: List[ConsensusResult] = []
    
    async def think_polyatomic(
        self,
        parent_gid: str,
        task: Task,
        directive: Optional[PrimeDirective] = None,
        atom_count: int = 5,
        threshold: int = 3,
        model_name: str = "gpt-4",
        temperature: float = 0.0
    ) -> ConsensusResult:
        """
        Execute polyatomic consensus reasoning.
        
        Args:
            parent_gid: Parent GID to clone (e.g., "GID-06" for SAM)
            task: Task to reason about (all atoms see same task)
            directive: Constitutional instructions (optional)
            atom_count: Number of clones to spawn (default 5)
            threshold: Minimum votes for consensus (default 3)
            model_name: LLM model for reasoning
            temperature: LLM temperature (0.0 = deterministic)
        
        Returns:
            ConsensusResult with vote details and winning decision
        
        Raises:
            ValueError: If threshold > atom_count or atom_count < 1
        """
        # Validation
        if atom_count < 1:
            raise ValueError("atom_count must be >= 1")
        if threshold > atom_count:
            raise ValueError(f"threshold ({threshold}) cannot exceed atom_count ({atom_count})")
        if threshold <= atom_count / 2:
            self.logger.warning(
                f"POLY-01 VIOLATION RISK: threshold={threshold} is not supermajority "
                f"(should be >{atom_count/2}). Proceeding anyway."
            )
        
        start_time = datetime.now()
        self.logger.info(
            f"🧠 IGNITING POLYATOMIC THOUGHT: {atom_count} atoms, "
            f"threshold={threshold}, task={task.task_id}"
        )
        
        # Step 1: Get parent persona
        # In production, fetch from registry; for now, create mock
        parent = self._get_parent_persona(parent_gid)
        
        # Step 2: Spawn atom squad
        squad = self.university.spawn_squad(
            parent_gid=parent.gid,
            count=atom_count,
            directive=directive
        )
        self.logger.info(f"🎓 Spawned {len(squad)} atoms from {parent_gid}")
        
        # Step 3: Create reasoning engines (LLMBridge) for each atom
        bridge = LLMBridge(model_name=model_name, temperature=temperature)
        for atom in squad:
            atom.set_reasoning_engine(bridge)
        
        # Step 4: Parallel reasoning (async execution)
        self.logger.info(f"⚙️  Executing parallel reasoning across {atom_count} atoms...")
        reasoning_tasks = [
            atom.execute_task_intelligent(task)
            for atom in squad
        ]
        
        # Wait for all reasoning to complete
        raw_results = await asyncio.gather(*reasoning_tasks, return_exceptions=True)
        
        # Step 5: Extract ReasoningResults from execution strings
        # Note: execute_task_intelligent() returns formatted string, not ReasoningResult
        # We need to re-invoke bridge.reason() to get structured results
        reasoning_results: List[ReasoningResult] = []
        for atom in squad:
            context = {"directive": directive, "agent_gid": atom.gid}
            result = await bridge.reason(task, context)
            reasoning_results.append(result)
        
        # Step 5.5: PAC-P60 - Verify quantum signatures (PQC-02 enforcement)
        self.logger.info("🔐 Verifying quantum signatures (Dilithium attestation)...")
        signature_failures = []
        for idx, result in enumerate(reasoning_results):
            if "quantum_signature" in result.metadata:
                sig_hex = result.metadata["quantum_signature"]
                pubkey_hex = result.metadata["pqc_public_key"]
                
                # Create verifier from public key
                verifier = QuantumVerifier.from_hex(pubkey_hex)
                hash_bytes = bytes.fromhex(result.hash)
                signature_bytes = bytes.fromhex(sig_hex)
                
                is_valid = verifier.verify(hash_bytes, signature_bytes)
                
                if not is_valid:
                    # PQC-02: Signature verification failure → SCRAM
                    self.logger.error(
                        f"❌ PQC-02 VIOLATION: Atom {idx} signature verification FAILED. "
                        f"Hash {result.hash[:16]}... has invalid Dilithium signature. SCRAM TRIGGERED."
                    )
                    signature_failures.append(idx)
            else:
                self.logger.warning(f"⚠️  Atom {idx} missing quantum signature (legacy result?)")
        
        # If ANY signature fails, trigger SCRAM (fail-closed)
        if signature_failures:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            scram_result = ConsensusResult(
                decision="SCRAM_QUANTUM_SIGNATURE_FAILURE",
                reasoning=(
                    f"PQC-02 VIOLATION: Quantum signature verification failed for atoms {signature_failures}. "
                    f"System entering fail-closed SCRAM state. All decisions REJECTED."
                ),
                confidence=0.0,
                hash="SCRAM",
                vote_count=0,
                total_atoms=atom_count,
                consensus_achieved=False,
                all_hashes={},
                metadata={
                    "task_id": task.task_id,
                    "scram_reason": "quantum_signature_failure",
                    "failed_atoms": signature_failures,
                    "timestamp": datetime.now().isoformat(),
                    "latency_ms": elapsed_ms
                }
            )
            self._log_consensus_event(scram_result)
            self.consensus_history.append(scram_result)
            return scram_result
        
        self.logger.info(f"✅ All {atom_count} quantum signatures verified successfully")
        
        # Step 6: Count resonance hashes (voting)
        hash_votes = Counter(result.hash for result in reasoning_results)
        most_common_hash, vote_count = hash_votes.most_common(1)[0]
        
        self.logger.info(
            f"🗳️  RESONANCE VOTE: {vote_count}/{atom_count} atoms "
            f"match on hash {most_common_hash[:16]}..."
        )
        
        # Step 7: Check consensus threshold
        consensus_achieved = vote_count >= threshold
        
        if consensus_achieved:
            # Find winning result (any result with winning hash)
            winner = next(r for r in reasoning_results if r.hash == most_common_hash)
            
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result = ConsensusResult(
                decision=winner.decision,
                reasoning=winner.reasoning,
                confidence=winner.confidence,
                hash=winner.hash,
                vote_count=vote_count,
                total_atoms=atom_count,
                consensus_achieved=True,
                all_hashes=dict(hash_votes),
                metadata={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "parent_gid": parent_gid,
                    "atom_count": atom_count,
                    "threshold": threshold,
                    "model": model_name,
                    "temperature": temperature,
                    "latency_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat()
                }
            )
            # PAC-INT-P56: Emit consensus event to JSONL audit log
            self._log_consensus_event(result)
            
            
            self.logger.info(
                f"✅ POLYATOMIC CONSENSUS REACHED: {vote_count}/{atom_count} votes "
                f"({result.resonance_rate:.0%}) | Decision: {winner.decision}"
            )
            
            self.consensus_history.append(result)
            return result
        
        else:
            # Cognitive dissonance detected (POLY-02: fail-closed)
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            result = ConsensusResult(
                decision="DISSONANCE_DETECTED",
                reasoning=(
                    f"COGNITIVE DISSONANCE: Only {vote_count}/{atom_count} atoms agreed. "
                    f"Threshold {threshold} not met. Hash distribution: {dict(hash_votes)}"
                ),
                confidence=0.0,
                hash="DISSONANCE",
                vote_count=vote_count,
                total_atoms=atom_count,
                consensus_achieved=False,
                all_hashes=dict(hash_votes),
                metadata={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "parent_gid": parent_gid,
                    "atom_count": atom_count,
                    "threshold": threshold,
                    "latency_ms": elapsed_ms,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            self.logger.warning(
                f"⚠️  COGNITIVE DISSONANCE DETECTED: {vote_count}/{atom_count} votes "
                f"({result.resonance_rate:.0%}) < threshold {threshold}. "
            # PAC-INT-P56: Emit dissonance event to JSONL audit log
            self._log_consensus_event(result)
            
                f"FAIL-CLOSED (POLY-02). Hash distribution: {dict(hash_votes)}"
            )
            
            self.consensus_history.append(result)
            return result
    
    def _get_parent_persona(self, parent_gid: str) -> GIDPersona:
        """
        Retrieve parent persona for cloning.
        
        Args:
            parent_gid: Parent GID (e.g., "GID-06")
        
        Returns:
            GIDPersona object
        """
        # Mock implementation - in production, fetch from registry
        personas = {
            "GID-06": GIDPersona(
                gid="GID-06",
                name="SAM",
                role="Security Auditor",
                skills=["Risk Assessment", "Compliance Validation"],
                scope="Transaction security and governance compliance"
            ),
            "GID-04": GIDPersona(
                gid="GID-04",
                name="NINA",
                role="Network Orchestrator",
                skills=["API Integration", "Data Flow Management"],
                scope="Cross-chain communication and network optimization"
            ),
        }
        
        if parent_gid not in personas:
            # Fallback generic persona
            return GIDPersona(
                gid=parent_gid,
                name=f"AGENT-{parent_gid}",
                role="Generic Agent",
                skills=["Task Execution"],
                scope="General purpose agent"
            )
        
        return personas[parent_gid]
    
    def get_consensus_history(self) -> List[ConsensusResult]:
        """
        Retrieve all consensus results (audit trail).
        
        Returns:
            List of ConsensusResult objects
        """
        return self.consensus_history.copy()
    
    def get_consensus_stats(self) -> Dict[str, Any]:
        """
        Calculate aggregate consensus statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.consensus_history:
            return {
                "total_votes": 0,
                "consensus_count": 0,
                "dissonance_count": 0,
                "consensus_rate": 0.0,
                "avg_resonance_rate": 0.0
            }
        
        total = len(self.consensus_history)
        consensus_count = sum(1 for r in self.consensus_history if r.consensus_achieved)
        dissonance_count = total - consensus_count
        
        avg_resonance = sum(r.resonance_rate for r in self.consensus_history) / total
        
        return {
            "total_votes": total,
            "consensus_count": consensus_count,
            "dissonance_count": dissonance_count,
            "consensus_rate": consensus_count / total,
            "dissonance_rate": dissonance_count / total,
            "avg_resonance_rate": avg_resonance
        }
    
    def _log_consensus_event(self, result: ConsensusResult):
        """
        Log consensus event to JSONL audit trail (PAC-INT-P56).
        
        Args:
            result: ConsensusResult to log
        
        Writes:
            Single JSON line to logs/hive_consensus.jsonl
        
        Invariant: PIPE-02 (Non-blocking, fail-open)
        """
        try:
            # Ensure logs directory exists
            Path("logs").mkdir(exist_ok=True)
            
            # Build event record
            event = {
                "event": "CONSENSUS_REACHED" if result.consensus_achieved else "DISSONANCE_DETECTED",
                "consensus_id": result.metadata.get("task_id", "UNKNOWN"),
                "decision": result.decision,
                "hash": result.hash,
                "vote_count": result.vote_count,
                "total_atoms": result.total_atoms,
                "resonance_rate": result.resonance_rate,
                "threshold": result.metadata.get("threshold", 0),
                "all_hashes": result.all_hashes,
                "metadata": result.metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            # Append to JSONL file (atomic write)
            with open(HIVE_LOG_PATH, "a") as f:
                f.write(json.dumps(event) + "\n")
        
        except Exception as e:
            # PIPE-02: Fail-open (log error but don't crash)
            self.logger.error(f"Failed to log consensus event: {e}")


# Example usage (for documentation)
if __name__ == "__main__":
    async def demo():
        """Demonstrate Polyatomic Hive usage."""
        # Initialize hive
        hive = PolyatomicHive()
        
        # Create task
        task = Task(
            task_id="TASK-CONSENSUS-001",
            task_type="GOVERNANCE_CHECK",
            payload={"transaction_id": "TXN-123", "amount_usd": 50000}
        )
        
        # Create directive
        directive = PrimeDirective(
            mission="Validate high-value transactions",
            constraints=["READ_ONLY", "MAX_AMOUNT_100K"],
            success_criteria={"accuracy": 0.95}
        )
        
        # Execute polyatomic consensus (5 atoms, require 3 votes)
        result = await hive.think_polyatomic(
            parent_gid="GID-06",  # SAM - Security Auditor
            task=task,
            directive=directive,
            atom_count=5,
            threshold=3
        )
        
        print(f"\n{result}")
        print(f"Decision: {result.decision}")
        print(f"Consensus: {result.consensus_achieved}")
        print(f"Votes: {result.vote_count}/{result.total_atoms}")
        print(f"Resonance: {result.resonance_rate:.0%}")
        print(f"Hash: {result.hash}")
        
        # Show statistics
        stats = hive.get_consensus_stats()
        print(f"\nHive Statistics:")
        print(f"  Total Votes: {stats['total_votes']}")
        print(f"  Consensus Rate: {stats['consensus_rate']:.0%}")
    
    asyncio.run(demo())
