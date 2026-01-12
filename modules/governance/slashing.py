#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     SLASHING ENGINE - THE COURT                              ║
║                   PAC-GOV-P320-FEDERATION-POLICY                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Automated Justice for the Mesh                                              ║
║                                                                              ║
║  "Slashing is code, not decision. If proof exists, punishment is immediate." ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Slashing Engine provides:
  - Double-signing detection with cryptographic proof
  - Automated punishment (no committee decision)
  - Slashing event audit trail
  - Stake confiscation

INVARIANTS:
  INV-GOV-002 (Automated Justice): Slashing is code. If proof exists, 
                                   punishment is immediate. No appeals.

Usage:
    from modules.governance.slashing import SlashingEngine, SlashingEvidence
    
    # Create engine with policy
    engine = SlashingEngine(policy)
    
    # Submit evidence of double-signing
    evidence = SlashingEvidence(
        violation_type=ViolationType.DOUBLE_SIGN,
        accused_node_id="NODE-MALICIOUS",
        header_a={"height": 100, "hash": "abc...", "signature": "sig1..."},
        header_b={"height": 100, "hash": "def...", "signature": "sig2..."},
    )
    
    # Process (automatic punishment if valid)
    result = engine.process_evidence(evidence)
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .policy import FederationPolicy

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# VIOLATION TYPES
# ══════════════════════════════════════════════════════════════════════════════

class ViolationType(Enum):
    """Types of slashable offenses."""
    
    # Critical (immediate ban + full stake slash)
    DOUBLE_SIGN = "DOUBLE_SIGN"           # Signed two different blocks at same height
    DOUBLE_VOTE = "DOUBLE_VOTE"           # Voted for two proposals at same round
    
    # Severe (partial slash + probation)
    DOWNTIME = "DOWNTIME"                 # Extended unavailability
    CENSORSHIP = "CENSORSHIP"             # Refusing to include valid transactions
    
    # Minor (warning)
    LATE_BLOCK = "LATE_BLOCK"             # Block produced outside window
    INVALID_SIGNATURE = "INVALID_SIGNATURE"  # Bad signature (could be bug)


class SlashingAction(Enum):
    """Actions taken in response to violations."""
    
    WARN = "WARN"                         # Issue warning
    PROBATION = "PROBATION"               # Place on probation
    SLASH_PARTIAL = "SLASH_PARTIAL"       # Confiscate portion of stake
    SLASH_FULL = "SLASH_FULL"             # Confiscate all stake
    BAN = "BAN"                           # Permanent expulsion


# Violation severity mapping
VIOLATION_SEVERITY = {
    ViolationType.DOUBLE_SIGN: {
        "action": SlashingAction.BAN,
        "slash_percent": 100,
        "description": "Signed conflicting blocks - cardinal sin"
    },
    ViolationType.DOUBLE_VOTE: {
        "action": SlashingAction.BAN,
        "slash_percent": 100,
        "description": "Voted for conflicting proposals"
    },
    ViolationType.DOWNTIME: {
        "action": SlashingAction.SLASH_PARTIAL,
        "slash_percent": 10,
        "description": "Extended downtime affecting consensus"
    },
    ViolationType.CENSORSHIP: {
        "action": SlashingAction.SLASH_PARTIAL,
        "slash_percent": 25,
        "description": "Transaction censorship detected"
    },
    ViolationType.LATE_BLOCK: {
        "action": SlashingAction.WARN,
        "slash_percent": 0,
        "description": "Block produced late"
    },
    ViolationType.INVALID_SIGNATURE: {
        "action": SlashingAction.WARN,
        "slash_percent": 0,
        "description": "Invalid signature (possible software bug)"
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# SLASHING EVIDENCE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BlockHeader:
    """Block header for double-sign evidence."""
    
    height: int
    block_hash: str
    parent_hash: str
    timestamp: str
    validator_id: str
    signature: str
    
    def compute_signing_hash(self) -> str:
        """Compute the hash that was signed."""
        data = {
            "height": self.height,
            "block_hash": self.block_hash,
            "parent_hash": self.parent_hash,
            "timestamp": self.timestamp,
            "validator_id": self.validator_id,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "height": self.height,
            "block_hash": self.block_hash,
            "parent_hash": self.parent_hash,
            "timestamp": self.timestamp,
            "validator_id": self.validator_id,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlockHeader":
        return cls(
            height=data["height"],
            block_hash=data["block_hash"],
            parent_hash=data["parent_hash"],
            timestamp=data["timestamp"],
            validator_id=data["validator_id"],
            signature=data["signature"],
        )


@dataclass
class SlashingEvidence:
    """
    Evidence submitted to prove a slashable offense.
    
    For DOUBLE_SIGN: Must include two different block headers at same height
                     signed by the same validator.
    """
    
    # Violation details
    violation_type: ViolationType
    accused_node_id: str
    
    # Evidence payload (type-specific)
    header_a: Optional[BlockHeader] = None
    header_b: Optional[BlockHeader] = None
    
    # Additional context
    downtime_duration_seconds: int = 0
    censored_tx_hashes: List[str] = field(default_factory=list)
    
    # Metadata
    reporter_id: str = ""
    submitted_at: str = ""
    evidence_hash: str = ""
    
    def __post_init__(self):
        if not self.submitted_at:
            self.submitted_at = datetime.now(timezone.utc).isoformat()
        if not self.evidence_hash:
            self.evidence_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute unique hash of evidence."""
        data = {
            "violation_type": self.violation_type.value,
            "accused": self.accused_node_id,
            "header_a": self.header_a.to_dict() if self.header_a else None,
            "header_b": self.header_b.to_dict() if self.header_b else None,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# SLASHING RESULT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SlashingResult:
    """Result of processing slashing evidence."""
    
    # Verdict
    is_valid: bool
    action_taken: SlashingAction
    
    # Details
    accused_node_id: str
    violation_type: ViolationType
    stake_slashed: int
    
    # Audit
    evidence_hash: str
    verdict_hash: str
    processed_at: str
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "action_taken": self.action_taken.value,
            "accused_node_id": self.accused_node_id,
            "violation_type": self.violation_type.value,
            "stake_slashed": self.stake_slashed,
            "evidence_hash": self.evidence_hash,
            "verdict_hash": self.verdict_hash,
            "processed_at": self.processed_at,
            "reason": self.reason,
        }


# ══════════════════════════════════════════════════════════════════════════════
# SLASHING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class SlashingEngine:
    """
    The Court - Automated Justice for the Federation.
    
    INV-GOV-002: Slashing is code, not decision. If valid proof exists,
                 punishment is immediate and automatic. No appeals.
    
    The engine:
      - Validates cryptographic evidence
      - Applies punishment based on violation type
      - Maintains immutable audit trail
    """
    
    def __init__(self, policy: "FederationPolicy"):
        """
        Initialize slashing engine.
        
        Args:
            policy: Federation policy (for node access and status updates)
        """
        self._policy = policy
        
        # Evidence log (immutable audit trail)
        self._evidence_log: List[SlashingEvidence] = []
        
        # Verdict log
        self._verdict_log: List[SlashingResult] = []
        
        # Slashed stake pool (could be redistributed or burned)
        self._slashed_stake: int = 0
        
        # Processed evidence hashes (prevent replay)
        self._processed_hashes: set = set()
        
        logger.info("SlashingEngine initialized - Automated Justice Active")
    
    # ──────────────────────────────────────────────────────────────────────────
    # EVIDENCE VALIDATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def validate_double_sign_evidence(
        self, 
        evidence: SlashingEvidence
    ) -> Tuple[bool, str]:
        """
        Validate double-signing evidence.
        
        Requirements:
          1. Both headers must exist
          2. Same height
          3. Different block hashes
          4. Same validator ID (accused)
          5. Valid signatures (simplified - in production would verify crypto)
          
        Returns:
            Tuple of (is_valid, reason)
        """
        if not evidence.header_a or not evidence.header_b:
            return False, "Missing block headers"
        
        h_a = evidence.header_a
        h_b = evidence.header_b
        
        # Check same height
        if h_a.height != h_b.height:
            return False, f"Different heights: {h_a.height} vs {h_b.height}"
        
        # Check different block hashes (the crime)
        if h_a.block_hash == h_b.block_hash:
            return False, "Same block hash - not double-signing"
        
        # Check same validator
        if h_a.validator_id != h_b.validator_id:
            return False, f"Different validators: {h_a.validator_id} vs {h_b.validator_id}"
        
        # Check matches accused
        if h_a.validator_id != evidence.accused_node_id:
            return False, f"Validator ID doesn't match accused"
        
        # Check signatures exist (in production: verify cryptographic validity)
        if not h_a.signature or not h_b.signature:
            return False, "Missing signatures"
        
        # Signatures must be different (proves two separate signing events)
        if h_a.signature == h_b.signature:
            return False, "Same signature on both - not double-signing"
        
        # Verify accused node exists
        node = self._policy.get_node(evidence.accused_node_id)
        if not node:
            return False, f"Accused node {evidence.accused_node_id} not found"
        
        return True, f"VALID: {evidence.accused_node_id} signed two different blocks at height {h_a.height}"
    
    def validate_downtime_evidence(
        self,
        evidence: SlashingEvidence
    ) -> Tuple[bool, str]:
        """Validate downtime evidence."""
        if evidence.downtime_duration_seconds < 3600:  # Less than 1 hour
            return False, "Downtime less than 1 hour - warning only"
        
        node = self._policy.get_node(evidence.accused_node_id)
        if not node:
            return False, f"Accused node {evidence.accused_node_id} not found"
        
        return True, f"VALID: {evidence.accused_node_id} down for {evidence.downtime_duration_seconds}s"
    
    # ──────────────────────────────────────────────────────────────────────────
    # EVIDENCE PROCESSING
    # ──────────────────────────────────────────────────────────────────────────
    
    def process_evidence(self, evidence: SlashingEvidence) -> SlashingResult:
        """
        Process slashing evidence.
        
        INV-GOV-002: If proof is valid, punishment is automatic and immediate.
        
        Args:
            evidence: The evidence to process
            
        Returns:
            SlashingResult with verdict
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Check for replay
        if evidence.evidence_hash in self._processed_hashes:
            return SlashingResult(
                is_valid=False,
                action_taken=SlashingAction.WARN,
                accused_node_id=evidence.accused_node_id,
                violation_type=evidence.violation_type,
                stake_slashed=0,
                evidence_hash=evidence.evidence_hash,
                verdict_hash="",
                processed_at=now,
                reason="REPLAY: Evidence already processed",
            )
        
        # Validate based on type
        is_valid = False
        reason = ""
        
        if evidence.violation_type == ViolationType.DOUBLE_SIGN:
            is_valid, reason = self.validate_double_sign_evidence(evidence)
        elif evidence.violation_type == ViolationType.DOUBLE_VOTE:
            is_valid, reason = self.validate_double_sign_evidence(evidence)  # Similar logic
        elif evidence.violation_type == ViolationType.DOWNTIME:
            is_valid, reason = self.validate_downtime_evidence(evidence)
        else:
            is_valid = True
            reason = f"Minor violation: {evidence.violation_type.value}"
        
        # Get severity
        severity = VIOLATION_SEVERITY[evidence.violation_type]
        action = severity["action"]
        slash_percent = severity["slash_percent"]
        
        # Calculate stake to slash
        stake_slashed = 0
        if is_valid and slash_percent > 0:
            node = self._policy.get_node(evidence.accused_node_id)
            if node:
                stake_slashed = int(node.stake_amount * slash_percent / 100)
        
        # Create verdict
        verdict_data = {
            "is_valid": is_valid,
            "evidence_hash": evidence.evidence_hash,
            "stake_slashed": stake_slashed,
            "timestamp": now,
        }
        verdict_hash = hashlib.sha256(
            json.dumps(verdict_data, sort_keys=True).encode()
        ).hexdigest()
        
        result = SlashingResult(
            is_valid=is_valid,
            action_taken=action if is_valid else SlashingAction.WARN,
            accused_node_id=evidence.accused_node_id,
            violation_type=evidence.violation_type,
            stake_slashed=stake_slashed if is_valid else 0,
            evidence_hash=evidence.evidence_hash,
            verdict_hash=verdict_hash,
            processed_at=now,
            reason=reason,
        )
        
        # Apply punishment if valid (INV-GOV-002: Automated Justice)
        if is_valid:
            self._apply_punishment(evidence, result)
        
        # Record
        self._evidence_log.append(evidence)
        self._verdict_log.append(result)
        self._processed_hashes.add(evidence.evidence_hash)
        
        return result
    
    def _apply_punishment(self, evidence: SlashingEvidence, result: SlashingResult):
        """
        Apply punishment for validated offense.
        
        INV-GOV-002: Punishment is automatic. No committee. No appeal.
        """
        node_id = evidence.accused_node_id
        action = result.action_taken
        
        logger.warning(f"⚖️  SLASHING: {node_id} for {evidence.violation_type.value}")
        logger.warning(f"    Action: {action.value}, Stake Slashed: {result.stake_slashed}")
        
        # Update node in policy
        node = self._policy.get_node(node_id)
        if not node:
            return
        
        # Confiscate stake
        if result.stake_slashed > 0:
            self._slashed_stake += result.stake_slashed
            node.stake_amount -= result.stake_slashed
            node.slashing_events.append(result.verdict_hash)
        
        # Apply status change
        if action == SlashingAction.BAN:
            self._policy.ban_node(node_id, f"Slashed: {evidence.violation_type.value}")
        elif action == SlashingAction.PROBATION:
            from .policy import NodeStatus
            self._policy.update_node_status(node_id, NodeStatus.PROBATION, 
                                           f"Slashed: {evidence.violation_type.value}")
        elif action == SlashingAction.WARN:
            self._policy.warn_node(node_id, f"Violation: {evidence.violation_type.value}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # CONVENIENCE METHODS
    # ──────────────────────────────────────────────────────────────────────────
    
    def check_double_signing(
        self,
        header_a: Dict[str, Any],
        header_b: Dict[str, Any],
        reporter_id: str = "SYSTEM"
    ) -> SlashingResult:
        """
        Convenience method to check for double-signing.
        
        Args:
            header_a: First block header as dict
            header_b: Second block header as dict
            reporter_id: Who reported this
            
        Returns:
            SlashingResult
        """
        h_a = BlockHeader.from_dict(header_a)
        h_b = BlockHeader.from_dict(header_b)
        
        evidence = SlashingEvidence(
            violation_type=ViolationType.DOUBLE_SIGN,
            accused_node_id=h_a.validator_id,
            header_a=h_a,
            header_b=h_b,
            reporter_id=reporter_id,
        )
        
        return self.process_evidence(evidence)
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get slashing engine status."""
        return {
            "total_evidence_processed": len(self._evidence_log),
            "total_verdicts": len(self._verdict_log),
            "valid_slashings": len([v for v in self._verdict_log if v.is_valid]),
            "total_stake_slashed": self._slashed_stake,
            "violations_by_type": {
                vt.value: len([v for v in self._verdict_log 
                              if v.violation_type == vt and v.is_valid])
                for vt in ViolationType
            },
        }
    
    def get_verdicts(self, node_id: Optional[str] = None) -> List[SlashingResult]:
        """Get verdict history, optionally filtered by node."""
        if node_id:
            return [v for v in self._verdict_log if v.accused_node_id == node_id]
        return self._verdict_log.copy()


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate slashing module."""
    print("=" * 70)
    print("SLASHING ENGINE v3.0.0 - Self Test")
    print("=" * 70)
    
    from .policy import FederationPolicy, PeeringContract
    
    # Setup policy with nodes
    policy = FederationPolicy()
    
    for i in range(1, 4):
        contract = PeeringContract(
            node_id=f"NODE-{i}",
            public_key=f"pk_node{i}_xyz",
            stake_amount=50000,
            endpoint=f"node{i}.mesh.io:8080",
        )
        policy.admit_node(contract)
    
    print(f"\n[SETUP] Created policy with {policy.node_count} nodes")
    
    # Create slashing engine
    engine = SlashingEngine(policy)
    
    # Test 1: Detect double-signing
    print("\n[1/4] Testing double-sign detection (INV-GOV-002)...")
    
    # Create conflicting headers
    header_a = {
        "height": 100,
        "block_hash": "hash_block_a_abc123",
        "parent_hash": "hash_parent_99",
        "timestamp": "2026-01-11T00:00:00Z",
        "validator_id": "NODE-1",
        "signature": "sig_node1_on_block_a",
    }
    
    header_b = {
        "height": 100,  # Same height!
        "block_hash": "hash_block_b_def456",  # Different hash = CRIME
        "parent_hash": "hash_parent_99",
        "timestamp": "2026-01-11T00:00:01Z",
        "validator_id": "NODE-1",  # Same validator
        "signature": "sig_node1_on_block_b",  # Different sig = two signings
    }
    
    result = engine.check_double_signing(header_a, header_b, reporter_id="NODE-2")
    
    assert result.is_valid, f"Should detect double-signing: {result.reason}"
    assert result.action_taken == SlashingAction.BAN
    assert result.stake_slashed == 50000  # 100% slash
    
    print(f"      ✓ Double-signing detected!")
    print(f"      ✓ Verdict: {result.reason}")
    print(f"      ✓ Action: {result.action_taken.value}")
    print(f"      ✓ Stake slashed: {result.stake_slashed}")
    
    # Verify node is banned
    node = policy.get_node("NODE-1")
    from .policy import NodeStatus
    assert node.status == NodeStatus.BANNED
    print(f"      ✓ Node status: {node.status.value}")
    print(f"      ✓ INV-GOV-002 VERIFIED: Automatic punishment applied")
    
    # Test 2: Reject invalid evidence
    print("\n[2/4] Testing invalid evidence rejection...")
    
    # Same block hash = not double-signing
    header_same = header_a.copy()
    header_same["validator_id"] = "NODE-2"
    header_same["signature"] = "sig_node2_v1"
    
    header_same_copy = header_same.copy()
    header_same_copy["signature"] = "sig_node2_v2"
    
    result = engine.check_double_signing(header_same, header_same_copy)
    assert not result.is_valid
    print(f"      ✓ Rejected: {result.reason}")
    
    # Test 3: Replay protection
    print("\n[3/4] Testing replay protection...")
    
    # Try to submit same evidence again
    result = engine.check_double_signing(header_a, header_b)
    assert not result.is_valid
    assert "REPLAY" in result.reason
    print(f"      ✓ Replay rejected: {result.reason}")
    
    # Test 4: Minor violation (warning only)
    print("\n[4/4] Testing minor violations...")
    
    evidence = SlashingEvidence(
        violation_type=ViolationType.LATE_BLOCK,
        accused_node_id="NODE-3",
    )
    
    result = engine.process_evidence(evidence)
    assert result.action_taken == SlashingAction.WARN
    assert result.stake_slashed == 0
    
    node3 = policy.get_node("NODE-3")
    assert node3.status == NodeStatus.ACTIVE  # Still active
    assert node3.warnings == 1
    
    print(f"      ✓ Warning issued for minor violation")
    print(f"      ✓ Node still ACTIVE with {node3.warnings} warning(s)")
    
    # Summary
    status = engine.get_status()
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print(f"Evidence processed: {status['total_evidence_processed']}")
    print(f"Valid slashings: {status['valid_slashings']}")
    print(f"Total stake slashed: {status['total_stake_slashed']}")
    print("INV-GOV-002 (Automated Justice): ENFORCED")
    print("=" * 70)
    print("\n⚖️  The Court is in session. Justice is automatic.")


if __name__ == "__main__":
    _self_test()
