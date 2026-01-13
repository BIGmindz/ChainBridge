"""
Lifecycle Bindings - WRAP/BER Event Integration
===============================================

PAC Reference: PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM
Classification: LAW_TIER
Author: ALEX (GID-08) - Lifecycle Logic
Orchestrator: BENSON (GID-00)

Binds heartbeat events to WRAP/BER generation lifecycle.
Ensures proof events are visible in OCC timeline.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass

from .heartbeat_emitter import HeartbeatEmitter, HeartbeatEvent, HeartbeatEventType, get_emitter


@dataclass
class LifecycleHook:
    """Hook for lifecycle event callbacks."""
    name: str
    event_type: HeartbeatEventType
    callback: Callable[[HeartbeatEvent], None]
    enabled: bool = True


class LifecycleBindings:
    """
    Binds PAC execution lifecycle to heartbeat events.
    
    Automatically emits heartbeats when:
    - PAC files are created/updated
    - WRAP proofs are generated
    - BER evaluations complete
    - Ledger commits occur
    
    Usage:
        bindings = LifecycleBindings()
        
        # Before generating WRAP
        bindings.on_wrap_start(pac_id, wrap_id)
        
        # After WRAP complete
        bindings.on_wrap_complete(pac_id, wrap_id, agent_attestations)
        
        # After BER complete
        bindings.on_ber_complete(pac_id, ber_id, score)
    """
    
    def __init__(self, emitter: Optional[HeartbeatEmitter] = None):
        self.emitter = emitter or get_emitter()
        self._hooks: List[LifecycleHook] = []
        self._wrap_start_times: Dict[str, str] = {}
        self._ber_start_times: Dict[str, str] = {}
    
    def register_hook(
        self,
        name: str,
        event_type: HeartbeatEventType,
        callback: Callable[[HeartbeatEvent], None]
    ) -> None:
        """Register a callback hook for specific event type."""
        self._hooks.append(LifecycleHook(
            name=name,
            event_type=event_type,
            callback=callback
        ))
    
    def _trigger_hooks(self, event: HeartbeatEvent) -> None:
        """Trigger all matching hooks for an event."""
        for hook in self._hooks:
            if hook.enabled and hook.event_type == event.event_type:
                try:
                    hook.callback(event)
                except Exception as e:
                    # Log but don't fail on hook errors
                    print(f"Hook {hook.name} failed: {e}")
    
    # ==================== PAC Lifecycle ====================
    
    def on_pac_admitted(
        self,
        pac_id: str,
        title: str,
        classification: str,
        lane: str,
        authority: str = "JEFFREY"
    ) -> HeartbeatEvent:
        """Called when PAC is admitted and execution begins."""
        event = self.emitter.emit_pac_start(
            pac_id=pac_id,
            title=title,
            classification=classification,
            lane=lane,
            authority=authority
        )
        self._trigger_hooks(event)
        return event
    
    def on_pac_completed(
        self,
        pac_id: str,
        wrap_id: str,
        ber_id: str,
        ber_score: int,
        tasks_completed: int
    ) -> HeartbeatEvent:
        """Called when PAC execution completes successfully."""
        event = self.emitter.emit_pac_complete(
            pac_id=pac_id,
            wrap_id=wrap_id,
            ber_id=ber_id,
            ber_score=ber_score,
            tasks_completed=tasks_completed
        )
        self._trigger_hooks(event)
        return event
    
    def on_pac_failed(
        self,
        pac_id: str,
        reason: str,
        tasks_completed: int,
        tasks_failed: int
    ) -> HeartbeatEvent:
        """Called when PAC execution fails."""
        event = self.emitter.emit_pac_failed(
            pac_id=pac_id,
            reason=reason,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed
        )
        self._trigger_hooks(event)
        return event
    
    # ==================== WRAP Lifecycle ====================
    
    def on_wrap_start(self, pac_id: str, wrap_id: str) -> HeartbeatEvent:
        """Called when WRAP generation begins."""
        self._wrap_start_times[wrap_id] = datetime.now(timezone.utc).isoformat()
        return self.emitter.emit_task_start(
            task_id=f"WRAP-GEN-{wrap_id}",
            title=f"Generating {wrap_id}",
            agent_gid="GID-00",
            agent_name="BENSON"
        )
    
    def on_wrap_complete(
        self,
        pac_id: str,
        wrap_id: str,
        agent_count: int = 13,
        consensus: str = "UNANIMOUS"
    ) -> HeartbeatEvent:
        """Called when WRAP generation completes."""
        start_time = self._wrap_start_times.pop(wrap_id, None)
        
        # Emit task complete
        self.emitter.emit_task_complete(
            task_id=f"WRAP-GEN-{wrap_id}",
            title=f"Generated {wrap_id}",
            artifact=f"proofs/{wrap_id}.json"
        )
        
        # Emit WRAP generated event
        event = self.emitter.emit_wrap_generated(
            wrap_id=wrap_id,
            pac_id=pac_id,
            agent_count=agent_count,
            consensus=consensus,
            start_time=start_time
        )
        self._trigger_hooks(event)
        return event
    
    # ==================== BER Lifecycle ====================
    
    def on_ber_start(self, pac_id: str, ber_id: str) -> HeartbeatEvent:
        """Called when BER evaluation begins."""
        self._ber_start_times[ber_id] = datetime.now(timezone.utc).isoformat()
        return self.emitter.emit_task_start(
            task_id=f"BER-EVAL-{ber_id}",
            title=f"Evaluating {ber_id}",
            agent_gid="GID-00",
            agent_name="BENSON"
        )
    
    def on_ber_complete(
        self,
        pac_id: str,
        ber_id: str,
        score: int,
        max_score: int = 100,
        recommendation: str = "ACCEPT"
    ) -> HeartbeatEvent:
        """Called when BER evaluation completes."""
        start_time = self._ber_start_times.pop(ber_id, None)
        
        # Emit task complete
        self.emitter.emit_task_complete(
            task_id=f"BER-EVAL-{ber_id}",
            title=f"Evaluated {ber_id}",
            artifact=f"proofs/{ber_id}.json"
        )
        
        # Emit BER generated event
        event = self.emitter.emit_ber_generated(
            ber_id=ber_id,
            pac_id=pac_id,
            score=score,
            max_score=max_score,
            recommendation=recommendation,
            start_time=start_time
        )
        self._trigger_hooks(event)
        return event
    
    # ==================== Ledger Lifecycle ====================
    
    def on_ledger_commit(
        self,
        record_name: str,
        pac_id: Optional[str] = None,
        ledger_path: str = "core/governance/SOVEREIGNTY_LEDGER.json"
    ) -> HeartbeatEvent:
        """Called when ledger is updated."""
        event = self.emitter.emit_ledger_commit(
            record_name=record_name,
            ledger_path=ledger_path,
            pac_id=pac_id
        )
        self._trigger_hooks(event)
        return event
    
    # ==================== Agent Lifecycle ====================
    
    def on_agent_activated(
        self,
        agent_gid: str,
        agent_name: str,
        role: str,
        pac_id: Optional[str] = None
    ) -> HeartbeatEvent:
        """Called when agent is activated for PAC execution."""
        event = self.emitter.emit_agent_active(
            agent_gid=agent_gid,
            agent_name=agent_name,
            role=role,
            pac_id=pac_id
        )
        self._trigger_hooks(event)
        return event
    
    def on_agent_attested(
        self,
        agent_gid: str,
        agent_name: str,
        attestation: str,
        wrap_id: Optional[str] = None
    ) -> HeartbeatEvent:
        """Called when agent provides attestation."""
        event = self.emitter.emit_agent_attested(
            agent_gid=agent_gid,
            agent_name=agent_name,
            attestation=attestation,
            wrap_id=wrap_id
        )
        self._trigger_hooks(event)
        return event
    
    # ==================== Full Swarm Activation ====================
    
    def activate_full_swarm(self, pac_id: str) -> List[HeartbeatEvent]:
        """Emit activation events for all 13 agents."""
        agents = [
            ("GID-00", "BENSON", "Orchestrator"),
            ("GID-01", "CODY", "Backend"),
            ("GID-02", "SONNY", "API"),
            ("GID-03", "MIRA-R", "Documentation"),
            ("GID-04", "CINDY", "Testing"),
            ("GID-05", "PAX", "Workflow"),
            ("GID-06", "SAM", "Security"),
            ("GID-07", "DAN", "CI/CD"),
            ("GID-08", "ALEX", "Logic"),
            ("GID-09", "LIRA", "UX"),
            ("GID-10", "MAGGIE", "AI Policy"),
            ("GID-11", "ATLAS", "Architecture"),
            ("GID-12", "DIGGI", "Audit"),
        ]
        
        events = []
        for gid, name, role in agents:
            event = self.on_agent_activated(gid, name, role, pac_id)
            events.append(event)
        
        return events


# ==================== Convenience Factory ====================

def create_lifecycle_bindings(emitter: Optional[HeartbeatEmitter] = None) -> LifecycleBindings:
    """Factory function to create lifecycle bindings."""
    return LifecycleBindings(emitter)


# ==================== Self-Test ====================

if __name__ == "__main__":
    print("LifecycleBindings Self-Test")
    print("=" * 50)
    
    from .heartbeat_emitter import reset_emitter
    
    emitter = reset_emitter()
    bindings = LifecycleBindings(emitter)
    
    pac_id = "PAC-P744-TEST"
    wrap_id = "WRAP-P744-TEST"
    ber_id = "BER-P744-TEST"
    
    # Test full lifecycle
    bindings.on_pac_admitted(pac_id, "Test PAC", "LAW_TIER", "TEST")
    bindings.activate_full_swarm(pac_id)
    bindings.on_wrap_start(pac_id, wrap_id)
    bindings.on_wrap_complete(pac_id, wrap_id, agent_count=13)
    bindings.on_ber_start(pac_id, ber_id)
    bindings.on_ber_complete(pac_id, ber_id, score=100)
    bindings.on_ledger_commit("test_record", pac_id)
    bindings.on_pac_completed(pac_id, wrap_id, ber_id, 100, 4)
    
    print(f"\nEvents emitted: {emitter._sequence}")
    print("✅ Self-test PASSED")
