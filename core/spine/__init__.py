"""
Minimum Execution Spine (MES) - PAC-BENSON-EXEC-SPINE-01

The irreducible core of ChainBridge:
Event → Decision → Action → Proof

BENSON (GID-00): Wartime CTO / Orchestrator
Doctrine: Proof > Features > Narrative

Constraints:
- Deterministic logic only
- No silent failures
- No async without traceability
- Proof generation is mandatory
"""

__version__ = "1.0.0"

from core.spine.decision import DecisionEngine, DecisionResult
from core.spine.event import SpineEvent, SpineEventType
from core.spine.executor import SpineExecutor, ExecutionProof

__all__ = [
    "SpineEvent",
    "SpineEventType", 
    "DecisionEngine",
    "DecisionResult",
    "SpineExecutor",
    "ExecutionProof",
]
