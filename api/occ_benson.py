"""
BENSON ORCHESTRATOR API ROUTER
PAC-OCC-P14: API Mounting
Identity: Benson Execution (GID-00-EXEC)

Exposes the BensonOrchestrator as a networked service via FastAPI.
Endpoint: POST /occ/execute
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Fix import path for orchestrator
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.core.orchestrator import BensonOrchestrator

# ═══════════════════════════════════════════════════════════════════
# ROUTER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

router = APIRouter(
    prefix="/occ",
    tags=["OCC Benson Orchestrator"],
    responses={
        500: {"description": "Orchestrator execution failure"},
        503: {"description": "Orchestrator not available"},
    },
)

# ═══════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════

class PACExecutionRequest(BaseModel):
    """Request schema for PAC execution."""
    pac_content: str = Field(
        ...,
        description="The Project Authorization Card content to process",
        min_length=1,
        example="Objective: Verify system status.\nScope: Report health metrics."
    )
    execution_mode: str = Field(
        default="standard",
        description="Execution mode: 'standard' or 'tool_enabled'",
        pattern="^(standard|tool_enabled)$"
    )


class BERResponse(BaseModel):
    """Response schema containing the Bridge Execution Record."""
    status: str = Field(..., description="Execution status: SUCCESS or FAILURE")
    timestamp: str = Field(..., description="ISO timestamp of execution")
    pac_id: Optional[str] = Field(None, description="PAC identifier if provided")
    ber_content: str = Field(..., description="The Bridge Execution Record output")
    tool_calls: int = Field(default=0, description="Number of tool calls made")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")


class HealthResponse(BaseModel):
    """Health check response for orchestrator status."""
    status: str
    orchestrator_ready: bool
    api_key_configured: bool
    tools_available: list[str]
    timestamp: str


# ═══════════════════════════════════════════════════════════════════
# SINGLETON ORCHESTRATOR INSTANCE
# ═══════════════════════════════════════════════════════════════════

_orchestrator_instance: Optional[BensonOrchestrator] = None


def get_orchestrator() -> BensonOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        try:
            _orchestrator_instance = BensonOrchestrator()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize orchestrator: {str(e)}"
            )
    return _orchestrator_instance


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/benson/health", response_model=HealthResponse)
async def orchestrator_health():
    """
    Check Benson Orchestrator health status.
    
    Returns the current state of the orchestrator including
    API key configuration and available tools.
    """
    api_key_configured = bool(os.getenv("GOOGLE_API_KEY"))
    
    tools_available = []
    if api_key_configured:
        try:
            orchestrator = get_orchestrator()
            tools_available = list(orchestrator.tool_functions.keys())
            orchestrator_ready = True
        except Exception:
            orchestrator_ready = False
    else:
        orchestrator_ready = False
    
    # Check kill switch status (PAC-OCC-P16 / EU AI Act Art. 14)
    from api.occ_emergency import is_kill_switch_active
    kill_switch_active = is_kill_switch_active()
    
    return HealthResponse(
        status="killed" if kill_switch_active else ("healthy" if orchestrator_ready else "degraded"),
        orchestrator_ready=orchestrator_ready and not kill_switch_active,
        api_key_configured=api_key_configured,
        tools_available=tools_available if not kill_switch_active else [],
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.post("/execute", response_model=BERResponse)
async def execute_pac(request: PACExecutionRequest):
    """
    Execute a Project Authorization Card (PAC) and return a Bridge Execution Record (BER).
    
    This is the primary endpoint for submitting work to the Benson Orchestrator.
    The orchestrator will process the PAC content, potentially using tools
    (read_file, write_file, run_terminal), and return a structured BER.
    
    **Authorization:** GID-00 (Benson) execution authority required.
    
    **Modes:**
    - `standard`: Basic PAC processing without tool calls
    - `tool_enabled`: Full agentic mode with tool execution capability
    
    **Kill Switch (PAC-OCC-P16):** If KILL_SWITCH.lock exists, returns 503.
    **Authority:** EU AI Act Art. 14 (Human Override)
    """
    import time
    from api.occ_emergency import is_kill_switch_active
    
    # KILL SWITCH GATE — Check BEFORE any processing (EU AI Act Art. 14)
    if is_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail="🔴 EXECUTION BLOCKED — Kill switch active. POST /occ/emergency/resume to restore.",
        )
    
    start_time = time.time()
    
    try:
        orchestrator = get_orchestrator()
        
        # Process the PAC
        ber_content = orchestrator.process_pac(request.pac_content)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Determine status from BER content
        status = "SUCCESS" if "🔴 EXECUTION FAILURE" not in ber_content else "FAILURE"
        
        return BERResponse(
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            pac_id=None,  # Could extract from PAC content if formatted
            ber_content=ber_content,
            tool_calls=0,  # TODO: Track tool calls in orchestrator
            execution_time_ms=round(execution_time_ms, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        return BERResponse(
            status="FAILURE",
            timestamp=datetime.now(timezone.utc).isoformat(),
            pac_id=None,
            ber_content=f"🔴 EXECUTION FAILURE: {str(e)}",
            tool_calls=0,
            execution_time_ms=round(execution_time_ms, 2)
        )


@router.get("/benson/identity")
async def get_orchestrator_identity():
    """
    Return Benson's constitutional identity as read from AGENT_REGISTRY.json.
    
    This endpoint proves the orchestrator can read its own identity
    from the governance files (P13 verification).
    """
    try:
        orchestrator = get_orchestrator()
        
        # Use the read_file tool to get identity
        from src.core.tools import read_file
        result = read_file("docs/governance/AGENT_REGISTRY.json")
        
        if result.status.value == "SUCCESS":
            import json
            registry = json.loads(result.output)
            benson_entry = registry.get("agents", {}).get("BENSON", {})
            
            return {
                "status": "verified",
                "gid": benson_entry.get("gid", "UNKNOWN"),
                "lane": benson_entry.get("lane", "UNKNOWN"),
                "color": benson_entry.get("color", "UNKNOWN"),
                "role": benson_entry.get("role", "UNKNOWN"),
                "emoji": benson_entry.get("emoji_primary", "UNKNOWN"),
                "level": benson_entry.get("agent_level", "UNKNOWN"),
                "source": "docs/governance/AGENT_REGISTRY.json",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read identity: {result.error}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Identity verification failed: {str(e)}"
        )
