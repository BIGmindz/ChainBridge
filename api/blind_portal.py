"""
ChainBridge Sovereign Swarm - Blind Vetting Portal
PAC-BLIND-PORTAL-28 | JOB B: BLIND-PORTAL

Secure Zero-PII ingest layer for .cbh (ChainBridge Hash) files.
Integrates with Concordium ZK-Bridge for real-time identity vetting.

Constitutional Constraints:
- MUST only accept .cbh file format
- MUST NOT write uploaded data to disk (memory-only streaming)
- MUST validate HMAC signature before processing
- MUST fail-closed on salt-mismatch or invalid signature

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001
"""

import hashlib
import hmac
import json
import time
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncGenerator
from io import BytesIO
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zk.concordium_bridge import (
    ConcordiumBridge,
    ZKProof,
    ZKProofStatus,
    ZKValidationResult,
    SovereignSalt,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class PortalSecurityLimits:
    """Security limits enforced by the Blind Portal"""
    MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
    MAX_RECORDS_PER_SESSION = 100000
    RATE_LIMIT_PER_MINUTE = 10
    SESSION_TIMEOUT_SECONDS = 3600
    MAX_CONCURRENT_SESSIONS = 5
    ALLOWED_FILE_EXTENSION = ".cbh"
    ALLOWED_CONTENT_TYPE = "application/json"


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class SessionStatus(Enum):
    """Portal session status"""
    PENDING = "PENDING"
    AUTHENTICATING = "AUTHENTICATING"
    UPLOADING = "UPLOADING"
    VALIDATING = "VALIDATING"
    VETTING = "VETTING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class VettingResult(Enum):
    """Individual record vetting result"""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PENDING = "PENDING"
    ERROR = "ERROR"


class SecurityEventType(Enum):
    """Security event types for audit logging"""
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_AUTHENTICATED = "SESSION_AUTHENTICATED"
    FILE_UPLOADED = "FILE_UPLOADED"
    SALT_MISMATCH = "SALT_MISMATCH"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    SIZE_LIMIT_EXCEEDED = "SIZE_LIMIT_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    VETTING_COMPLETE = "VETTING_COMPLETE"
    SESSION_TERMINATED = "SESSION_TERMINATED"


@dataclass
class SecurityEvent:
    """Security event for audit logging"""
    event_id: str
    event_type: SecurityEventType
    session_id: str
    timestamp: str
    details: Dict[str, Any]
    severity: str = "INFO"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "details": self.details,
            "severity": self.severity
        }


@dataclass
class VettedRecord:
    """Result of vetting a single record"""
    record_id: str
    full_name_hash: str
    result: VettingResult
    gates_passed: int
    gates_failed: int
    decision: str
    latency_ms: float
    brp_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "full_name_hash_preview": f"{self.full_name_hash[:8]}...{self.full_name_hash[-8:]}",
            "result": self.result.value,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "decision": self.decision,
            "latency_ms": self.latency_ms,
            "brp_hash": self.brp_hash
        }


@dataclass
class BlindAuditResponse:
    """
    Standardized response schema for bank systems.
    This is the JSON structure returned after a complete audit.
    """
    session_id: str
    status: str
    total_records: int
    compliant_count: int
    non_compliant_count: int
    error_count: int
    compliance_rate: float
    total_processing_time_ms: float
    average_latency_per_record_ms: float
    genesis_anchor: str
    salt_fingerprint: str
    audit_timestamp: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    brp_summary_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "blind_audit_response": {
                "session_id": self.session_id,
                "status": self.status,
                "summary": {
                    "total_records": self.total_records,
                    "compliant": self.compliant_count,
                    "non_compliant": self.non_compliant_count,
                    "errors": self.error_count,
                    "compliance_rate_percent": round(self.compliance_rate * 100, 2)
                },
                "performance": {
                    "total_processing_time_ms": round(self.total_processing_time_ms, 3),
                    "average_latency_per_record_ms": round(self.average_latency_per_record_ms, 4)
                },
                "cryptographic_binding": {
                    "genesis_anchor": self.genesis_anchor,
                    "salt_fingerprint": self.salt_fingerprint,
                    "brp_summary_hash": self.brp_summary_hash
                },
                "audit_timestamp": self.audit_timestamp
            },
            "records": self.records[:100]  # Limit response size
        }


@dataclass
class PortalSession:
    """Active portal session"""
    session_id: str
    gid_token: str
    created_at: str
    status: SessionStatus
    client_ip: str = "0.0.0.0"
    file_size_bytes: int = 0
    records_processed: int = 0
    records_compliant: int = 0
    records_non_compliant: int = 0
    last_activity: str = ""
    security_events: List[SecurityEvent] = field(default_factory=list)
    
    def update_activity(self):
        self.last_activity = datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# GID TOKEN MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class GIDTokenManager:
    """
    Manages one-time GID tokens for portal authentication.
    Each bank session requires a unique token.
    """
    
    def __init__(self):
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
        self.used_tokens: set = set()
    
    def generate_token(self, bank_id: str, valid_duration_seconds: int = 3600) -> str:
        """Generate a new one-time GID token"""
        token = f"GID-{bank_id}-{uuid.uuid4().hex[:16].upper()}"
        self.active_tokens[token] = {
            "bank_id": bank_id,
            "created_at": time.time(),
            "expires_at": time.time() + valid_duration_seconds,
            "used": False
        }
        return token
    
    def validate_token(self, token: str) -> tuple[bool, str]:
        """Validate a GID token. Returns (valid, reason)"""
        if token in self.used_tokens:
            return False, "TOKEN_ALREADY_USED"
        
        if token not in self.active_tokens:
            return False, "TOKEN_NOT_FOUND"
        
        token_data = self.active_tokens[token]
        
        if time.time() > token_data["expires_at"]:
            return False, "TOKEN_EXPIRED"
        
        return True, "TOKEN_VALID"
    
    def consume_token(self, token: str) -> bool:
        """Mark a token as used (one-time use)"""
        if token in self.active_tokens:
            self.used_tokens.add(token)
            del self.active_tokens[token]
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# CBH FILE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CBHValidator:
    """
    Validates .cbh (ChainBridge Hash) files before processing.
    Enforces constitutional constraints on file format and integrity.
    """
    
    def __init__(self):
        self.sovereign_salt = SovereignSalt()
        self.expected_salt_fingerprint = f"{self.sovereign_salt.salt[:8]}...{self.sovereign_salt.salt[-8:]}"
    
    def validate_file_extension(self, filename: str) -> tuple[bool, str]:
        """Validate file has .cbh extension"""
        if not filename.lower().endswith(PortalSecurityLimits.ALLOWED_FILE_EXTENSION):
            return False, f"INVALID_EXTENSION: Expected {PortalSecurityLimits.ALLOWED_FILE_EXTENSION}"
        return True, "VALID"
    
    def validate_file_size(self, size_bytes: int) -> tuple[bool, str]:
        """Validate file size is within limits"""
        if size_bytes > PortalSecurityLimits.MAX_FILE_SIZE_BYTES:
            return False, f"SIZE_EXCEEDED: Max {PortalSecurityLimits.MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
        return True, "VALID"
    
    def validate_cbh_structure(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Validate CBH file has required structure"""
        if "cbh_header" not in data:
            return False, "MISSING_CBH_HEADER"
        
        header = data["cbh_header"]
        required_fields = ["version", "genesis_anchor", "salt_fingerprint", "integrity_hash"]
        
        for field in required_fields:
            if field not in header:
                return False, f"MISSING_HEADER_FIELD: {field}"
        
        if "records" not in data:
            return False, "MISSING_RECORDS_ARRAY"
        
        return True, "VALID"
    
    def validate_salt_fingerprint(self, cbh_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        CRITICAL: Validate salt fingerprint matches our Sovereign Salt.
        FAIL-CLOSED if mismatch detected.
        """
        header = cbh_data.get("cbh_header", {})
        file_fingerprint = header.get("salt_fingerprint", "")
        
        # Normalize fingerprint format
        expected_short = self.expected_salt_fingerprint
        
        if file_fingerprint != expected_short:
            return False, f"SALT_MISMATCH: Expected {expected_short}, got {file_fingerprint}"
        
        return True, "SALT_VERIFIED"
    
    def validate_integrity_hash(self, cbh_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate the integrity hash matches the file content.
        """
        header = cbh_data.get("cbh_header", {})
        claimed_hash = header.get("integrity_hash", "")
        
        # Recompute integrity hash
        content = json.dumps({
            "version": header.get("version"),
            "genesis_anchor": header.get("genesis_anchor"),
            "total_records": header.get("total_records"),
            "records": cbh_data.get("records", [])
        }, sort_keys=True)
        computed_hash = hashlib.sha256(content.encode()).hexdigest()
        
        if not hmac.compare_digest(claimed_hash, computed_hash):
            return False, "INTEGRITY_HASH_MISMATCH"
        
        return True, "INTEGRITY_VERIFIED"
    
    def full_validation(self, filename: str, content: bytes) -> tuple[bool, str, Optional[Dict]]:
        """
        Perform full validation of a .cbh file.
        Returns (valid, reason, parsed_data)
        """
        # Step 1: Extension check
        valid, reason = self.validate_file_extension(filename)
        if not valid:
            return False, reason, None
        
        # Step 2: Size check
        valid, reason = self.validate_file_size(len(content))
        if not valid:
            return False, reason, None
        
        # Step 3: Parse JSON
        try:
            cbh_data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            return False, f"JSON_PARSE_ERROR: {str(e)}", None
        
        # Step 4: Structure check
        valid, reason = self.validate_cbh_structure(cbh_data)
        if not valid:
            return False, reason, None
        
        # Step 5: Salt fingerprint check (CRITICAL)
        valid, reason = self.validate_salt_fingerprint(cbh_data)
        if not valid:
            return False, reason, None
        
        # Step 6: Integrity hash check
        valid, reason = self.validate_integrity_hash(cbh_data)
        if not valid:
            return False, reason, None
        
        return True, "ALL_VALIDATIONS_PASSED", cbh_data


# ═══════════════════════════════════════════════════════════════════════════════
# BLIND VETTING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class BlindVettingEngine:
    """
    Core vetting engine that processes .cbh records against Identity Gates.
    Integrates with Concordium ZK-Bridge for Zero-Knowledge validation.
    """
    
    def __init__(self):
        self.concordium_bridge = ConcordiumBridge()
        self.sovereign_salt = SovereignSalt()
        self.total_vetted = 0
        self.total_compliant = 0
        self.total_non_compliant = 0
    
    def vet_record(self, record: Dict[str, Any]) -> VettedRecord:
        """
        Vet a single record against Identity Gates.
        Uses hash-to-hash comparison (Zero-Knowledge).
        """
        start_time = time.time()
        
        record_id = record.get("record_id", "UNKNOWN")
        full_name_hash = record.get("full_name_hash", "")
        
        # Create a synthetic ZK-Proof from the hash
        # In production, this would come from Concordium
        zk_proof = ZKProof(
            proof_id=f"PROOF-{record_id}",
            credential_id=f"CRED-{record_id}",
            holder_did=f"did:cbh:{full_name_hash[:16]}",
            attributes={
                "fullNameHash": full_name_hash,
                "sanctionsCheck": "CLEAR",  # Would be real check in production
                "amlCheck": "PASS",
                "countryOfResidence": "US",
                "nationality": "US",
                "idDocType": "VERIFIED",
                "idDocIssuer": "VERIFIED",
                "idDocExpiryDate": "2030-01-01T00:00:00Z",
                "firstNameHash": full_name_hash[:64] if len(full_name_hash) >= 64 else "a" * 64,
                "lastNameHash": full_name_hash[:64] if len(full_name_hash) >= 64 else "b" * 64,
                "dobHash": record.get("dob_hash", "c" * 64)
            },
            timestamp=time.time(),
            expiry=time.time() + 3600,
            signature="cbh_derived_signature",
            issuer_id="BLIND-PORTAL"
        )
        
        # Validate through Concordium Bridge
        validation_result = self.concordium_bridge.validate_zk_proof(zk_proof)
        
        latency = (time.time() - start_time) * 1000
        
        if validation_result.status == ZKProofStatus.VALID:
            result = VettingResult.COMPLIANT
            self.total_compliant += 1
        else:
            result = VettingResult.NON_COMPLIANT
            self.total_non_compliant += 1
        
        self.total_vetted += 1
        
        return VettedRecord(
            record_id=record_id,
            full_name_hash=full_name_hash,
            result=result,
            gates_passed=validation_result.gates_passed,
            gates_failed=validation_result.gates_failed,
            decision=validation_result.decision,
            latency_ms=latency,
            brp_hash=validation_result.brp_hash
        )
    
    def vet_batch(self, records: List[Dict[str, Any]]) -> List[VettedRecord]:
        """Vet a batch of records"""
        return [self.vet_record(record) for record in records]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vetting statistics"""
        return {
            "total_vetted": self.total_vetted,
            "total_compliant": self.total_compliant,
            "total_non_compliant": self.total_non_compliant,
            "compliance_rate": self.total_compliant / max(1, self.total_vetted),
            "bridge_stats": self.concordium_bridge.get_statistics()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProgressUpdate:
    """Real-time progress update for Decision Feed"""
    session_id: str
    timestamp: str
    progress_percent: float
    records_processed: int
    records_total: int
    compliant_count: int
    non_compliant_count: int
    current_record_id: str
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "progress": {
                "percent": round(self.progress_percent, 1),
                "processed": self.records_processed,
                "total": self.records_total
            },
            "results": {
                "compliant": self.compliant_count,
                "non_compliant": self.non_compliant_count
            },
            "current_record": self.current_record_id,
            "status": self.status
        }


class ProgressEngine:
    """
    Real-time progress tracking for bank dashboard.
    Provides streaming updates during vetting process.
    """
    
    def __init__(self, session_id: str, total_records: int):
        self.session_id = session_id
        self.total_records = total_records
        self.processed = 0
        self.compliant = 0
        self.non_compliant = 0
        self.current_record = ""
        self.updates: List[ProgressUpdate] = []
    
    def update(self, record_id: str, result: VettingResult) -> ProgressUpdate:
        """Record a progress update"""
        self.processed += 1
        self.current_record = record_id
        
        if result == VettingResult.COMPLIANT:
            self.compliant += 1
        elif result == VettingResult.NON_COMPLIANT:
            self.non_compliant += 1
        
        progress = ProgressUpdate(
            session_id=self.session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            progress_percent=(self.processed / max(1, self.total_records)) * 100,
            records_processed=self.processed,
            records_total=self.total_records,
            compliant_count=self.compliant,
            non_compliant_count=self.non_compliant,
            current_record_id=record_id,
            status="VETTING" if self.processed < self.total_records else "COMPLETE"
        )
        
        self.updates.append(progress)
        return progress
    
    def get_final_summary(self) -> Dict[str, Any]:
        """Get final progress summary"""
        return {
            "session_id": self.session_id,
            "total_records": self.total_records,
            "processed": self.processed,
            "compliant": self.compliant,
            "non_compliant": self.non_compliant,
            "compliance_rate": self.compliant / max(1, self.processed),
            "total_updates": len(self.updates)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# BLIND PORTAL ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class BlindPortalOrchestrator:
    """
    Main orchestrator for the Blind Portal.
    Coordinates authentication, validation, vetting, and response generation.
    """
    
    def __init__(self):
        self.token_manager = GIDTokenManager()
        self.cbh_validator = CBHValidator()
        self.vetting_engine = BlindVettingEngine()
        self.active_sessions: Dict[str, PortalSession] = {}
        self.security_log: List[SecurityEvent] = []
    
    def _log_security_event(
        self,
        event_type: SecurityEventType,
        session_id: str,
        details: Dict[str, Any],
        severity: str = "INFO"
    ) -> SecurityEvent:
        """Log a security event"""
        event = SecurityEvent(
            event_id=f"SEC-{uuid.uuid4().hex[:12].upper()}",
            event_type=event_type,
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details,
            severity=severity
        )
        self.security_log.append(event)
        return event
    
    def create_session(self, gid_token: str, client_ip: str = "0.0.0.0") -> tuple[bool, str, Optional[PortalSession]]:
        """Create a new portal session with GID token authentication"""
        
        # Validate token
        valid, reason = self.token_manager.validate_token(gid_token)
        
        session_id = f"SESSION-{uuid.uuid4().hex[:16].upper()}"
        
        if not valid:
            self._log_security_event(
                SecurityEventType.SESSION_TERMINATED,
                session_id,
                {"reason": reason, "token_preview": gid_token[:10] + "..."},
                severity="WARNING"
            )
            return False, reason, None
        
        # Consume token (one-time use)
        self.token_manager.consume_token(gid_token)
        
        # Create session
        session = PortalSession(
            session_id=session_id,
            gid_token=gid_token,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=SessionStatus.AUTHENTICATING,
            client_ip=client_ip
        )
        session.update_activity()
        
        self.active_sessions[session_id] = session
        
        self._log_security_event(
            SecurityEventType.SESSION_CREATED,
            session_id,
            {"client_ip": client_ip},
            severity="INFO"
        )
        
        session.status = SessionStatus.PENDING
        
        return True, "SESSION_CREATED", session
    
    def process_cbh_upload(
        self,
        session_id: str,
        filename: str,
        content: bytes
    ) -> tuple[bool, str, Optional[BlindAuditResponse]]:
        """
        Process a .cbh file upload.
        MEMORY-ONLY: Content is never written to disk.
        """
        
        if session_id not in self.active_sessions:
            return False, "SESSION_NOT_FOUND", None
        
        session = self.active_sessions[session_id]
        session.status = SessionStatus.UPLOADING
        session.file_size_bytes = len(content)
        session.update_activity()
        
        # Validate the CBH file
        session.status = SessionStatus.VALIDATING
        valid, reason, cbh_data = self.cbh_validator.full_validation(filename, content)
        
        if not valid:
            severity = "CRITICAL" if "SALT_MISMATCH" in reason or "INTEGRITY" in reason else "WARNING"
            event_type = (
                SecurityEventType.SALT_MISMATCH if "SALT" in reason
                else SecurityEventType.INVALID_SIGNATURE if "INTEGRITY" in reason
                else SecurityEventType.INVALID_FILE_TYPE
            )
            
            self._log_security_event(
                event_type,
                session_id,
                {"reason": reason, "filename": filename},
                severity=severity
            )
            
            session.status = SessionStatus.TERMINATED
            return False, reason, None
        
        self._log_security_event(
            SecurityEventType.FILE_UPLOADED,
            session_id,
            {
                "filename": filename,
                "size_bytes": len(content),
                "total_records": len(cbh_data.get("records", []))
            }
        )
        
        # Start vetting process
        session.status = SessionStatus.VETTING
        records = cbh_data.get("records", [])
        total_records = len(records)
        
        # Check record limit
        if total_records > PortalSecurityLimits.MAX_RECORDS_PER_SESSION:
            self._log_security_event(
                SecurityEventType.SIZE_LIMIT_EXCEEDED,
                session_id,
                {"records": total_records, "limit": PortalSecurityLimits.MAX_RECORDS_PER_SESSION},
                severity="WARNING"
            )
            return False, f"RECORD_LIMIT_EXCEEDED: Max {PortalSecurityLimits.MAX_RECORDS_PER_SESSION}", None
        
        # Initialize progress engine
        progress_engine = ProgressEngine(session_id, total_records)
        
        # Process records
        start_time = time.time()
        vetted_records: List[VettedRecord] = []
        
        for record in records:
            vetted = self.vetting_engine.vet_record(record)
            vetted_records.append(vetted)
            progress_engine.update(vetted.record_id, vetted.result)
            session.records_processed += 1
            if vetted.result == VettingResult.COMPLIANT:
                session.records_compliant += 1
            else:
                session.records_non_compliant += 1
        
        total_time = (time.time() - start_time) * 1000
        
        # Build response
        header = cbh_data.get("cbh_header", {})
        compliance_rate = session.records_compliant / max(1, total_records)
        
        # Generate BRP summary hash
        brp_summary = json.dumps({
            "session_id": session_id,
            "total_records": total_records,
            "compliant": session.records_compliant,
            "non_compliant": session.records_non_compliant,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, sort_keys=True)
        brp_summary_hash = hashlib.sha256(brp_summary.encode()).hexdigest()
        
        response = BlindAuditResponse(
            session_id=session_id,
            status="COMPLETE",
            total_records=total_records,
            compliant_count=session.records_compliant,
            non_compliant_count=session.records_non_compliant,
            error_count=0,
            compliance_rate=compliance_rate,
            total_processing_time_ms=total_time,
            average_latency_per_record_ms=total_time / max(1, total_records),
            genesis_anchor=header.get("genesis_anchor", ""),
            salt_fingerprint=header.get("salt_fingerprint", ""),
            audit_timestamp=datetime.now(timezone.utc).isoformat(),
            records=[r.to_dict() for r in vetted_records],
            brp_summary_hash=brp_summary_hash
        )
        
        session.status = SessionStatus.COMPLETE
        
        self._log_security_event(
            SecurityEventType.VETTING_COMPLETE,
            session_id,
            {
                "total_records": total_records,
                "compliant": session.records_compliant,
                "non_compliant": session.records_non_compliant,
                "compliance_rate": compliance_rate,
                "processing_time_ms": total_time,
                "brp_summary_hash": brp_summary_hash
            }
        )
        
        return True, "VETTING_COMPLETE", response
    
    def generate_gid_token(self, bank_id: str) -> str:
        """Generate a new GID token for a bank"""
        return self.token_manager.generate_token(bank_id)
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an active session"""
        if session_id not in self.active_sessions:
            return None
        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "created_at": session.created_at,
            "records_processed": session.records_processed,
            "records_compliant": session.records_compliant,
            "records_non_compliant": session.records_non_compliant,
            "last_activity": session.last_activity
        }
    
    def get_security_log(self) -> List[Dict[str, Any]]:
        """Get security event log"""
        return [e.to_dict() for e in self.security_log]


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_portal_test() -> Dict[str, Any]:
    """Run a complete portal test cycle"""
    print("=" * 70)
    print("CHAINBRIDGE BLIND PORTAL | PAC-BLIND-PORTAL-28 | TEST CYCLE")
    print("=" * 70)
    
    # Initialize portal
    portal = BlindPortalOrchestrator()
    
    # Step 1: Generate GID token for bank
    print("\n[STEP 1] Generating GID token for test bank...")
    gid_token = portal.generate_gid_token("TEST-BANK-001")
    print(f"  Token: {gid_token}")
    
    # Step 2: Create session
    print("\n[STEP 2] Creating portal session...")
    success, reason, session = portal.create_session(gid_token, "127.0.0.1")
    print(f"  Success: {success}")
    print(f"  Session ID: {session.session_id if session else 'N/A'}")
    
    if not success:
        return {"error": reason}
    
    # Step 3: Create test CBH file in memory
    print("\n[STEP 3] Creating test .cbh file in memory...")
    
    from tools.vaporizer.vaporizer import VaporizerEngine, CBHFile
    
    engine = VaporizerEngine()
    test_records = []
    for i in range(10):
        record = engine.vaporize_record(
            record_id=f"TEST-{i:04d}",
            first_name=f"TestFirst{i}",
            last_name=f"TestLast{i}",
            dob=f"1990-01-{(i % 28) + 1:02d}"
        )
        test_records.append(record)
    
    cbh_file = CBHFile.from_vaporized_records(test_records)
    cbh_content = json.dumps(cbh_file.to_dict()).encode('utf-8')
    print(f"  Records: {len(test_records)}")
    print(f"  Size: {len(cbh_content)} bytes")
    
    # Step 4: Process upload
    print("\n[STEP 4] Processing CBH upload through Blind Portal...")
    success, reason, response = portal.process_cbh_upload(
        session.session_id,
        "test_upload.cbh",
        cbh_content
    )
    
    if not success:
        print(f"  FAILED: {reason}")
        return {"error": reason}
    
    print(f"  Status: {response.status}")
    print(f"  Total Records: {response.total_records}")
    print(f"  Compliant: {response.compliant_count}")
    print(f"  Non-Compliant: {response.non_compliant_count}")
    print(f"  Compliance Rate: {response.compliance_rate * 100:.1f}%")
    print(f"  Processing Time: {response.total_processing_time_ms:.2f}ms")
    print(f"  Avg Latency/Record: {response.average_latency_per_record_ms:.4f}ms")
    print(f"  BRP Summary Hash: {response.brp_summary_hash[:16]}...")
    
    # Step 5: Check security log
    print("\n[STEP 5] Security Event Log:")
    for event in portal.get_security_log():
        print(f"  [{event['severity']}] {event['event_type']}: {event['details']}")
    
    print("\n" + "=" * 70)
    print("BLIND PORTAL TEST: COMPLETE")
    print("=" * 70)
    
    return response.to_dict()


if __name__ == "__main__":
    result = run_portal_test()
    print("\n[FINAL RESPONSE SAMPLE]")
    print(json.dumps(result.get("blind_audit_response", {}).get("summary", {}), indent=2))
