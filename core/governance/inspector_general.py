"""
Inspector General (IG) Node - PAC-P824
=====================================

The Internal Affairs Division for ChainBridge Constitutional Framework.

MISSION:
    Monitor TGL (Test Governance Layer) audit trails in real-time and enforce
    fail-closed security by triggering SCRAM when REJECTED verdicts are detected
    for artifacts that are currently deployed or running.

INVARIANTS:
    IG-01: IG Node MUST trigger SCRAM upon detecting a REJECTED verdict
    IG-02: IG Node MUST NOT modify the audit log (Read-Only operation)

INTEGRATION:
    - Reads from: logs/governance/tgl_audit_trail.jsonl (written by SemanticJudge)
    - Triggers: core.governance.scram.SCRAMController.emergency_halt()
    - Bootstrap: Launched by sovereign_main.py at system startup

CONSTITUTIONAL AUTHORITY:
    - PAC-P824: Inspector General Node Deployment
    - JEFFREY (GID-CONST-01): Constitutional Architect
    - FORGE (GID-04): Implementation Agent

SECURITY POSTURE:
    - Fail-Closed: Any detection of REJECTED verdict triggers immediate SCRAM
    - Read-Only: IG never writes to audit logs (append-only by TGL only)
    - Async Monitoring: Non-blocking continuous surveillance with 1s poll interval
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set
from core.governance.scram import get_scram_controller, SCRAMController
from core.governance.integrity_sentinel import get_integrity_sentinel, IntegritySentinel


class InspectorGeneral:
    """
    The Inspector General (IG) Node - Runtime Oversight for Constitutional Compliance.
    
    The IG continuously monitors the TGL audit trail for REJECTED verdicts and enforces
    fail-closed security by triggering SCRAM when constitutional violations are detected.
    
    Attributes:
        log_path (Path): Path to TGL audit trail JSONL file
        scram (SCRAMController): SCRAM kill switch controller
        logger (Logger): Python logging instance
        _monitoring (bool): Flag indicating if monitoring is active
        _processed_entries (Set[str]): Manifest IDs already processed (avoid duplicates)
        _last_position (int): File byte position from last scan
    
    Example:
        >>> ig = InspectorGeneral()
        >>> await ig.start_monitoring()  # Runs until stopped or SCRAM triggered
    """
    
    def __init__(
        self,
        log_path: str = "logs/governance/tgl_audit_trail.jsonl",
        scram_controller: Optional[SCRAMController] = None,
        integrity_sentinel: Optional[IntegritySentinel] = None
    ):
        """
        Initialize the Inspector General Node.
        
        Args:
            log_path: Path to TGL audit trail JSONL file (default: logs/governance/tgl_audit_trail.jsonl)
            scram_controller: Optional SCRAM controller instance (default: get_scram_controller())
            integrity_sentinel: Optional IntegritySentinel instance (default: get_integrity_sentinel())
        """
        self.log_path = Path(log_path)
        self.scram = scram_controller or get_scram_controller()
        self.sentinel = integrity_sentinel or get_integrity_sentinel()
        self.logger = logging.getLogger("InspectorGeneral")
        self._monitoring = False
        self._processed_entries: Set[str] = set()
        self._last_position = 0
        
        # Ensure log directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"IG Node initialized. Watching: {self.log_path}")
        self.logger.info(f"🔐 Constitutional Integrity Sentinel integrated (PAC-P825)")
    
    async def start_monitoring(self) -> None:
        """
        Start continuous monitoring of TGL audit trail.
        
        This method runs indefinitely until:
        1. stop() is called (sets _monitoring = False)
        2. SCRAM is triggered (status != "OPERATIONAL")
        3. An unhandled exception occurs
        
        The monitoring loop:
        - Scans the audit log for new entries
        - Analyzes each entry for REJECTED verdicts
        - Triggers SCRAM if constitutional violations detected
        - Polls every 1 second (would use inotify in production)
        
        Side Effects:
            - May trigger SCRAM emergency halt
            - Updates _processed_entries and _last_position
        """
        self._monitoring = True
        self.logger.info(f"🔍 IG Node monitoring started: {self.log_path}")
        
        try:
            # Initial scan of existing log
            await self._scan_log()
            
            # Continuous monitoring loop
            while self._monitoring:
                # Check if SCRAM has been triggered
                if self.scram.status != "OPERATIONAL":
                    self.logger.warning("⚠️ SCRAM triggered. IG monitoring halted.")
                    break
                
                # PAC-P825: Verify constitutional integrity on each cycle
                integrity_status = await self.sentinel.verify_integrity()
                if integrity_status == "BREACH_DETECTED":
                    self.logger.critical("🚨 Constitutional breach detected. SCRAM triggered by Sentinel.")
                    break  # SCRAM already triggered by sentinel
                
                # Scan for new log entries
                await self._scan_log()
                
                # Poll interval (production would use inotify/watchdog)
                await asyncio.sleep(1.0)
        
        except Exception as e:
            self.logger.error(f"❌ IG monitoring error: {e}", exc_info=True)
            # Fail-closed: trigger SCRAM on unexpected errors
            await self.scram.emergency_halt(
                reason=f"IG_MONITORING_FAILURE: {str(e)}"
            )
        
        finally:
            self.logger.info("🛑 IG Node monitoring stopped")
    
    async def _scan_log(self) -> None:
        """
        Scan TGL audit trail for new entries since last scan.
        
        Implements incremental reading by tracking file position (_last_position).
        Only processes entries that haven't been seen before (via _processed_entries).
        
        Side Effects:
            - Updates _last_position
            - Updates _processed_entries
            - May trigger SCRAM via _analyze_entry()
        """
        if not self.log_path.exists():
            # Log file doesn't exist yet (no TGL judgments made)
            return
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                # Seek to last known position (incremental read)
                f.seek(self._last_position)
                
                # Read new lines since last scan
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        await self._analyze_entry(entry)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"⚠️ Malformed JSON in audit log: {e}")
                        continue
                
                # Update file position for next scan
                self._last_position = f.tell()
        
        except Exception as e:
            self.logger.error(f"❌ Log scan error: {e}", exc_info=True)
    
    async def _analyze_entry(self, entry: Dict[str, Any]) -> None:
        """
        Analyze a single audit log entry for constitutional violations.
        
        ENFORCEMENT LOGIC (IG-01):
            IF judgment == "Rejected" AND manifest_id not previously processed THEN
                Trigger SCRAM with detailed violation report
            END IF
        
        READ-ONLY GUARANTEE (IG-02):
            This method only reads audit log entries. No write operations are performed.
        
        Args:
            entry: Parsed JSONL entry from TGL audit trail
                   Expected fields: manifest_id, judgment, reason, agent_gid, git_commit_hash
        
        Side Effects:
            - May trigger SCRAM emergency halt
            - Logs violations to IG logger
            - Updates _processed_entries
        """
        # Extract key fields
        manifest_id = entry.get("manifest_id", "UNKNOWN")
        judgment = entry.get("judgment", "UNKNOWN")
        agent_gid = entry.get("agent_gid", "UNKNOWN")
        git_commit = entry.get("git_commit_hash", "UNKNOWN")
        reason = entry.get("reason", "No reason provided")
        timestamp = entry.get("timestamp", datetime.utcnow().isoformat())
        
        # Skip if already processed (avoid duplicate SCRAM triggers)
        if manifest_id in self._processed_entries:
            return
        
        # Mark as processed
        self._processed_entries.add(manifest_id)
        
        # IG-01 ENFORCEMENT: Detect REJECTED verdicts
        if judgment == "Rejected":
            violation_report = (
                f"🚨 CONSTITUTIONAL VIOLATION DETECTED 🚨\n"
                f"Manifest: {manifest_id}\n"
                f"Agent: {agent_gid}\n"
                f"Git Commit: {git_commit}\n"
                f"Judgment: REJECTED\n"
                f"Reason: {reason}\n"
                f"Timestamp: {timestamp}\n"
                f"\n"
                f"⚠️ IG-01 ENFORCEMENT: A REJECTED manifest indicates code that failed\n"
                f"constitutional requirements (zero test failures, 100% MCDC coverage,\n"
                f"valid Ed25519 signature). If this code is currently deployed or running,\n"
                f"it represents a critical security risk.\n"
                f"\n"
                f"🛑 TRIGGERING SCRAM EMERGENCY HALT"
            )
            
            self.logger.critical(violation_report)
            
            # Trigger SCRAM with detailed reason
            scram_reason = (
                f"IG_VIOLATION_DETECTED: Manifest {manifest_id} (Agent: {agent_gid}, "
                f"Commit: {git_commit}) was REJECTED by TGL. Reason: {reason}"
            )
            
            await self.scram.emergency_halt(reason=scram_reason)
        
        else:
            # Log approved judgments for audit purposes (non-critical)
            self.logger.debug(
                f"✅ Manifest {manifest_id} APPROVED (Agent: {agent_gid})"
            )
    
    async def stop(self) -> None:
        """
        Stop IG monitoring gracefully.
        
        Sets the _monitoring flag to False, which will cause the monitoring loop
        in start_monitoring() to exit after the next poll interval.
        
        Side Effects:
            - Sets _monitoring = False
            - Logs shutdown message
        """
        self.logger.info("🛑 IG Node shutdown requested")
        self._monitoring = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current IG status for health checks and monitoring.
        
        Returns:
            Dictionary with status information:
                - monitoring: bool - Is IG currently monitoring?
                - log_path: str - Path to audit trail
                - processed_count: int - Number of entries processed
                - scram_status: str - Current SCRAM status
                - last_scan_position: int - File byte position
        """
        return {
            "monitoring": self._monitoring,
            "log_path": str(self.log_path),
            "processed_count": len(self._processed_entries),
            "scram_status": self.scram.status,
            "last_scan_position": self._last_position,
        }


# Singleton instance for application-wide access
_inspector_general_instance: Optional[InspectorGeneral] = None


def get_inspector_general(
    log_path: str = "logs/governance/tgl_audit_trail.jsonl",
    scram_controller: Optional[SCRAMController] = None
) -> InspectorGeneral:
    """
    Get or create the singleton InspectorGeneral instance.
    
    This ensures only one IG node is running per process, preventing
    duplicate monitoring and SCRAM triggers.
    
    Args:
        log_path: Path to TGL audit trail (used only on first call)
        scram_controller: Optional SCRAM controller (used only on first call)
    
    Returns:
        Singleton InspectorGeneral instance
    
    Example:
        >>> ig = get_inspector_general()
        >>> await ig.start_monitoring()
    """
    global _inspector_general_instance
    
    if _inspector_general_instance is None:
        _inspector_general_instance = InspectorGeneral(
            log_path=log_path,
            scram_controller=scram_controller
        )
    
    return _inspector_general_instance


# Convenience function for async startup in bootstrap code
async def start_inspector_general_monitoring() -> InspectorGeneral:
    """
    Convenience function to start IG monitoring in system bootstrap.
    
    This is the recommended way to start IG monitoring during application startup.
    
    Returns:
        InspectorGeneral instance with monitoring started
    
    Example (in sovereign_main.py):
        >>> ig = await start_inspector_general_monitoring()
        >>> # IG now running in background, monitoring TGL audit trail
    """
    ig = get_inspector_general()
    
    # Start monitoring in background task
    asyncio.create_task(ig.start_monitoring())
    
    return ig
