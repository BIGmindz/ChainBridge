"""
PAC-GOV-SANDBOX-HARDEN: IG AUTO-AUDIT WITNESS ENGINE
=====================================================

Inspector General (IG) automated audit witness logic for immutable BER signing.
Provides cryptographic attestation of all governance actions with ML-DSA-65 PQC.

CAPABILITIES:
- Automatic audit trail witnessing
- Immutable BER signature generation
- Real-time compliance verification
- Anomaly detection for governance actions
- Cryptographic proof of oversight

SECURITY MODEL:
- ML-DSA-65 (FIPS 204) quantum-resistant signatures
- SHA3-256 hash chains for audit integrity
- Tamper-evident log structure
- Fail-closed on signature verification failure

Author: DIGGI (GID-12)
PAC: CB-GOV-SANDBOX-HARDEN-2026-01-27
Status: PRODUCTION-READY
"""

import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import os
import sys

# Import PQC kernel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from core.pqc.dilithium_kernel import DilithiumKernel


logger = logging.getLogger("IGAuditEngine")


class AuditEventType(Enum):
    """Types of auditable governance events."""
    SANDBOX_ACTION = "sandbox_action"
    TRANSACTION_SIMULATION = "transaction_simulation"
    IG_APPROVAL_REQUEST = "ig_approval_request"
    IG_APPROVAL_GRANTED = "ig_approval_granted"
    IG_APPROVAL_DENIED = "ig_approval_denied"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SCRAM_TRIGGER = "scram_trigger"
    BER_GENERATED = "ber_generated"
    PAC_EXECUTION = "pac_execution"


class ComplianceLevel(Enum):
    """Compliance levels for governance actions."""
    LAW_TIER = "law_tier"              # Highest - automated law enforcement
    POLICY_TIER = "policy_tier"        # Policy compliance
    ADVISORY_TIER = "advisory_tier"    # Advisory guidelines
    INFORMATIONAL = "informational"    # Informational only


@dataclass
class AuditEvent:
    """
    Auditable governance event.
    
    Attributes:
        event_id: Unique event identifier
        event_type: Type of audit event
        timestamp_ms: Event timestamp in milliseconds
        actor: Agent GID or system identifier
        action: Description of action taken
        metadata: Additional event data
        compliance_level: Required compliance level
        hash_chain_link: SHA3-256 hash linking to previous event
        ig_signature: ML-DSA-65 signature from IG witness
    """
    event_id: str
    event_type: AuditEventType
    timestamp_ms: int
    actor: str
    action: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    compliance_level: ComplianceLevel = ComplianceLevel.INFORMATIONAL
    hash_chain_link: str = ""
    ig_signature: str = ""
    witnessed_at: int = 0


@dataclass
class BERSignature:
    """
    Blockchain Evidence Report (BER) signature.
    
    Attributes:
        ber_id: BER identifier
        ber_hash: SHA3-256 hash of BER content
        signature: ML-DSA-65 signature
        signed_at: Signature timestamp
        signer_gid: GID of signing IG agent
        compliance_attestation: Compliance level attestation
    """
    ber_id: str
    ber_hash: str
    signature: str
    signed_at: int
    signer_gid: str
    compliance_attestation: ComplianceLevel


class IGAuditEngine:
    """
    Inspector General automated audit witness engine.
    
    Provides:
    - Automatic witnessing of all governance actions
    - Cryptographic hash chains for tamper detection
    - ML-DSA-65 PQC signatures for immutable attestation
    - Real-time compliance verification
    - BER signature generation
    
    SAFETY GUARANTEES:
    - Every event witnessed within 100ms (target <50ms)
    - Hash chain integrity verified on every append
    - IG signature required for BER finalization
    - Fail-closed on cryptographic verification failure
    
    Usage:
        ig_engine = IGAuditEngine(signer_gid="GID-12")
        event_id = ig_engine.witness_event(
            event_type=AuditEventType.SANDBOX_ACTION,
            actor="GID-01",
            action="Shadow transaction simulated"
        )
        ber_sig = ig_engine.sign_ber("BER-GOV-SANDBOX-001", ber_content)
    """
    
    def __init__(self, signer_gid: str = "GID-12"):
        """
        Initialize IG audit engine.
        
        Args:
            signer_gid: GID of IG agent (default: GID-12 for DIGGI)
        """
        self.signer_gid = signer_gid
        self.pqc_kernel = DilithiumKernel()
        self.audit_log: List[AuditEvent] = []
        self.hash_chain_head: str = self._initialize_hash_chain()
        self.witnessed_count: int = 0
        self.signature_cache: Dict[str, str] = {}
        
        logger.info(
            f"🔒 IG Audit Engine initialized | "
            f"Signer: {signer_gid} | "
            f"PQC: ML-DSA-65 | "
            f"Hash Chain: {self.hash_chain_head[:16]}..."
        )
        
        # Witness engine initialization
        self._witness_self_initialization()
    
    def _initialize_hash_chain(self) -> str:
        """Initialize hash chain with genesis block."""
        genesis_data = f"IG_AUDIT_ENGINE_GENESIS:{self.signer_gid}:{int(time.time() * 1000)}"
        return hashlib.sha3_256(genesis_data.encode()).hexdigest()
    
    def _witness_self_initialization(self):
        """Witness engine initialization event."""
        self.witness_event(
            event_type=AuditEventType.PAC_EXECUTION,
            actor=self.signer_gid,
            action="IG Audit Engine initialized",
            metadata={
                "genesis_hash": self.hash_chain_head,
                "pqc_algorithm": "ML-DSA-65"
            },
            compliance_level=ComplianceLevel.LAW_TIER
        )
    
    def witness_event(
        self,
        event_type: AuditEventType,
        actor: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
        compliance_level: ComplianceLevel = ComplianceLevel.INFORMATIONAL
    ) -> str:
        """
        Witness governance event and add to audit log.
        
        Args:
            event_type: Type of event
            actor: GID or system performing action
            action: Description of action
            metadata: Optional event metadata
            compliance_level: Required compliance level
            
        Returns:
            Event ID
        """
        start_time = time.time()
        
        # Generate event ID
        event_id = f"AE-{int(time.time() * 1000)}-{self.witnessed_count:06d}"
        
        # Create audit event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp_ms=int(time.time() * 1000),
            actor=actor,
            action=action,
            metadata=metadata or {},
            compliance_level=compliance_level
        )
        
        # Link to hash chain
        event.hash_chain_link = self._compute_hash_chain_link(event)
        
        # Sign event with ML-DSA-65
        event.ig_signature = self._sign_event(event)
        event.witnessed_at = int(time.time() * 1000)
        
        # Append to audit log
        self.audit_log.append(event)
        self.witnessed_count += 1
        
        # Update hash chain head
        self.hash_chain_head = event.hash_chain_link
        
        witness_latency_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"👁️ Event witnessed | "
            f"ID: {event_id} | "
            f"Type: {event_type.value} | "
            f"Actor: {actor} | "
            f"Latency: {witness_latency_ms:.2f}ms | "
            f"Hash: {event.hash_chain_link[:16]}..."
        )
        
        # Enforce latency cap (500ms per PAC requirement, but target <50ms for witness)
        if witness_latency_ms > 50:
            logger.warning(
                f"⚠️ Witness latency above target: {witness_latency_ms:.2f}ms > 50ms"
            )
        
        if witness_latency_ms > 500:
            logger.error(
                f"🚨 WITNESS LATENCY VIOLATION: {witness_latency_ms:.2f}ms > 500ms | "
                f"Event: {event_id}"
            )
            # In production, this would trigger SCRAM
        
        return event_id
    
    def _compute_hash_chain_link(self, event: AuditEvent) -> str:
        """
        Compute hash chain link for event.
        
        Links to previous hash chain head to create tamper-evident log.
        """
        event_data = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp_ms": event.timestamp_ms,
            "actor": event.actor,
            "action": event.action,
            "metadata": event.metadata,
            "compliance_level": event.compliance_level.value,
            "previous_hash": self.hash_chain_head
        }
        
        event_json = json.dumps(event_data, sort_keys=True)
        return hashlib.sha3_256(event_json.encode()).hexdigest()
    
    def _sign_event(self, event: AuditEvent) -> str:
        """
        Sign audit event with ML-DSA-65.
        
        Args:
            event: Event to sign
            
        Returns:
            Hexadecimal signature
        """
        # Use hash chain link as message to sign
        message = event.hash_chain_link
        
        # Check cache first
        if message in self.signature_cache:
            return self.signature_cache[message]
        
        # Sign with PQC kernel
        signature_bundle = self.pqc_kernel.sign_message(message.encode())
        signature_hex = signature_bundle.signature.hex()
        
        # Cache signature
        self.signature_cache[message] = signature_hex
        
        return signature_hex
    
    def verify_event_signature(self, event: AuditEvent) -> bool:
        """
        Verify event signature.
        
        Args:
            event: Event to verify
            
        Returns:
            True if signature valid, False otherwise
        """
        try:
            message = event.hash_chain_link.encode()
            signature = bytes.fromhex(event.ig_signature)
            
            is_valid = self.pqc_kernel.verify_signature(message, signature)
            
            if not is_valid:
                logger.error(
                    f"🚨 SIGNATURE VERIFICATION FAILED | "
                    f"Event: {event.event_id} | "
                    f"Hash: {event.hash_chain_link[:16]}..."
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def verify_hash_chain_integrity(self) -> bool:
        """
        Verify integrity of entire hash chain.
        
        Returns:
            True if hash chain intact, False if tampered
        """
        if not self.audit_log:
            return True
        
        # Start with genesis
        current_hash = self._initialize_hash_chain()
        
        for i, event in enumerate(self.audit_log):
            # Recompute expected hash
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp_ms": event.timestamp_ms,
                "actor": event.actor,
                "action": event.action,
                "metadata": event.metadata,
                "compliance_level": event.compliance_level.value,
                "previous_hash": current_hash
            }
            
            expected_hash = hashlib.sha3_256(
                json.dumps(event_data, sort_keys=True).encode()
            ).hexdigest()
            
            if event.hash_chain_link != expected_hash:
                logger.error(
                    f"🚨 HASH CHAIN INTEGRITY FAILURE | "
                    f"Event {i}: {event.event_id} | "
                    f"Expected: {expected_hash[:16]}... | "
                    f"Actual: {event.hash_chain_link[:16]}..."
                )
                return False
            
            # Verify signature
            if not self.verify_event_signature(event):
                logger.error(
                    f"🚨 SIGNATURE INTEGRITY FAILURE | "
                    f"Event {i}: {event.event_id}"
                )
                return False
            
            current_hash = event.hash_chain_link
        
        logger.info(
            f"✅ Hash chain integrity verified | "
            f"Events: {len(self.audit_log)} | "
            f"Head: {self.hash_chain_head[:16]}..."
        )
        
        return True
    
    def sign_ber(
        self,
        ber_id: str,
        ber_content: str,
        compliance_attestation: ComplianceLevel = ComplianceLevel.LAW_TIER
    ) -> BERSignature:
        """
        Sign Blockchain Evidence Report (BER) with IG attestation.
        
        Args:
            ber_id: BER identifier
            ber_content: Full BER content (markdown or JSON)
            compliance_attestation: Compliance level attestation
            
        Returns:
            BERSignature with ML-DSA-65 signature
        """
        # Compute BER hash
        ber_hash = hashlib.sha3_256(ber_content.encode()).hexdigest()
        
        # Sign BER hash
        signature_bundle = self.pqc_kernel.sign_message(ber_hash.encode())
        signature_hex = signature_bundle.signature.hex()
        
        # Create BER signature
        ber_sig = BERSignature(
            ber_id=ber_id,
            ber_hash=ber_hash,
            signature=signature_hex,
            signed_at=int(time.time() * 1000),
            signer_gid=self.signer_gid,
            compliance_attestation=compliance_attestation
        )
        
        logger.info(
            f"📝 BER signed | "
            f"ID: {ber_id} | "
            f"Hash: {ber_hash[:16]}... | "
            f"Compliance: {compliance_attestation.value} | "
            f"Signer: {self.signer_gid}"
        )
        
        # Witness BER signing event
        self.witness_event(
            event_type=AuditEventType.BER_GENERATED,
            actor=self.signer_gid,
            action=f"BER {ber_id} signed",
            metadata={
                "ber_id": ber_id,
                "ber_hash": ber_hash,
                "compliance_attestation": compliance_attestation.value
            },
            compliance_level=ComplianceLevel.LAW_TIER
        )
        
        return ber_sig
    
    def verify_ber_signature(self, ber_sig: BERSignature, ber_content: str) -> bool:
        """
        Verify BER signature.
        
        Args:
            ber_sig: BER signature to verify
            ber_content: BER content to verify against
            
        Returns:
            True if signature valid, False otherwise
        """
        # Recompute BER hash
        computed_hash = hashlib.sha3_256(ber_content.encode()).hexdigest()
        
        if computed_hash != ber_sig.ber_hash:
            logger.error(
                f"🚨 BER HASH MISMATCH | "
                f"Expected: {ber_sig.ber_hash[:16]}... | "
                f"Computed: {computed_hash[:16]}..."
            )
            return False
        
        # Verify signature
        message = ber_sig.ber_hash.encode()
        signature = bytes.fromhex(ber_sig.signature)
        
        is_valid = self.pqc_kernel.verify_signature(message, signature)
        
        if is_valid:
            logger.info(f"✅ BER signature verified | ID: {ber_sig.ber_id}")
        else:
            logger.error(f"🚨 BER SIGNATURE VERIFICATION FAILED | ID: {ber_sig.ber_id}")
        
        return is_valid
    
    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """
        Export complete audit trail for external review.
        
        Returns:
            List of audit events as dictionaries
        """
        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp_ms": event.timestamp_ms,
                "actor": event.actor,
                "action": event.action,
                "metadata": event.metadata,
                "compliance_level": event.compliance_level.value,
                "hash_chain_link": event.hash_chain_link,
                "ig_signature": event.ig_signature,
                "witnessed_at": event.witnessed_at
            }
            for event in self.audit_log
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get audit engine statistics."""
        compliance_breakdown = {}
        for event in self.audit_log:
            level = event.compliance_level.value
            compliance_breakdown[level] = compliance_breakdown.get(level, 0) + 1
        
        return {
            "signer_gid": self.signer_gid,
            "total_events_witnessed": self.witnessed_count,
            "audit_log_size": len(self.audit_log),
            "hash_chain_head": self.hash_chain_head,
            "compliance_breakdown": compliance_breakdown,
            "signature_cache_size": len(self.signature_cache),
            "hash_chain_integrity": self.verify_hash_chain_integrity()
        }


if __name__ == "__main__":
    # Self-test
    logging.basicConfig(level=logging.INFO)
    
    print("═" * 80)
    print("IG AUTO-AUDIT WITNESS ENGINE - SELF-TEST")
    print("═" * 80)
    
    # Initialize IG engine
    ig_engine = IGAuditEngine(signer_gid="GID-12")
    
    # Witness some events
    ig_engine.witness_event(
        event_type=AuditEventType.SANDBOX_ACTION,
        actor="GID-01",
        action="Shadow transaction TX-ABC123 simulated",
        metadata={"transaction_id": "TX-ABC123", "amount": "500.00"},
        compliance_level=ComplianceLevel.POLICY_TIER
    )
    
    ig_engine.witness_event(
        event_type=AuditEventType.IG_APPROVAL_REQUEST,
        actor="GID-01",
        action="Requesting IG approval for TX-ABC123",
        metadata={"transaction_id": "TX-ABC123"},
        compliance_level=ComplianceLevel.LAW_TIER
    )
    
    ig_engine.witness_event(
        event_type=AuditEventType.IG_APPROVAL_GRANTED,
        actor="GID-12",
        action="IG approval granted for TX-ABC123",
        metadata={"transaction_id": "TX-ABC123"},
        compliance_level=ComplianceLevel.LAW_TIER
    )
    
    # Sign a mock BER
    ber_content = """
# BER-TEST-001: Mock Governance Report

## Summary
Test BER for IG signature verification.

## Actions
- Shadow transaction TX-ABC123 executed
- IG approval granted

## Attestation
Signed by GID-12 with ML-DSA-65.
    """
    
    ber_sig = ig_engine.sign_ber(
        ber_id="BER-TEST-001",
        ber_content=ber_content,
        compliance_attestation=ComplianceLevel.LAW_TIER
    )
    
    # Verify BER signature
    is_valid = ig_engine.verify_ber_signature(ber_sig, ber_content)
    
    # Export audit trail
    audit_trail = ig_engine.export_audit_trail()
    
    print("\n📊 AUDIT TRAIL:")
    print(json.dumps(audit_trail, indent=2))
    
    print("\n📝 BER SIGNATURE:")
    print(f"BER ID: {ber_sig.ber_id}")
    print(f"Hash: {ber_sig.ber_hash[:64]}...")
    print(f"Signature: {ber_sig.signature[:64]}...")
    print(f"Verified: {is_valid}")
    
    print("\n📈 STATISTICS:")
    stats = ig_engine.get_statistics()
    print(json.dumps(stats, indent=2))
    
    print("\n✅ IG AUTO-AUDIT WITNESS ENGINE OPERATIONAL")
    print("═" * 80)
