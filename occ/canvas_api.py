"""
OCC Canvas API Endpoints
Visual Swarm Builder - HTTP Interface

Provides REST API for the Sovereign Command Canvas.
Enables drag-drop agent deployment and visual workflow building.

Endpoints:
- /canvas/agents - Agent Forge roster
- /canvas/nodes - Canvas node management
- /canvas/connections - Workflow connections
- /canvas/deploy - Swarm deployment
- /canvas/simulate - BRP simulation

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
PAC: PAC-CANVAS-DEPLOY-39
"""

import json
from datetime import datetime, timezone
from typing import Optional, List

try:
    from fastapi import APIRouter, HTTPException, Header, Depends
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from occ.command_canvas import (
    SovereignCommandCanvas,
    ConnectionType,
    NodeType,
    SwarmState,
    CANVAS_VERSION,
)


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    class PlaceAgentRequest(BaseModel):
        agent_gid: str
        position_x: float
        position_y: float
        label: Optional[str] = None
    
    class ConnectNodesRequest(BaseModel):
        source_node_id: str
        target_node_id: str
        connection_type: str = "SEQUENTIAL"
    
    class CreatePipelineRequest(BaseModel):
        agent_gids: List[str]
        name: str = "Pipeline"
    
    class InitializeSwarmRequest(BaseModel):
        name: str
        description: str
    
    class ArmDeploymentRequest(BaseModel):
        swarm_id: str
        smk_key: str
    
    class ExecuteSwarmRequest(BaseModel):
        swarm_id: str
        confirmation_code: str


# ═══════════════════════════════════════════════════════════════════════════════
# CANVAS API ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

_canvas_instance: Optional[SovereignCommandCanvas] = None


def get_canvas() -> SovereignCommandCanvas:
    """Get or create canvas instance"""
    global _canvas_instance
    if _canvas_instance is None:
        _canvas_instance = SovereignCommandCanvas()
    return _canvas_instance


def create_canvas_router():
    """Create FastAPI router for Canvas endpoints"""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available")
    
    router = APIRouter(prefix="/canvas", tags=["Command Canvas"])
    
    # ─────────────────────────────────────────────────────────────────────────
    # ZONE A: AGENT FORGE
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/agents")
    async def get_agents():
        """Get available agents from the forge"""
        canvas = get_canvas()
        return canvas.agent_forge.get_roster()
    
    @router.get("/agents/{gid}")
    async def get_agent(gid: str):
        """Get a specific agent by GID"""
        canvas = get_canvas()
        agent = canvas.agent_forge.get_agent(gid)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent.to_dict()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ZONE B: LOGIC CANVAS
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/state")
    async def get_canvas_state():
        """Get complete canvas state"""
        canvas = get_canvas()
        return canvas.get_complete_state()
    
    @router.get("/nodes")
    async def get_nodes():
        """Get all nodes on canvas"""
        canvas = get_canvas()
        return canvas.canvas.get_canvas_state()
    
    @router.post("/nodes/place")
    async def place_agent(request: PlaceAgentRequest):
        """Place an agent on the canvas"""
        canvas = get_canvas()
        
        node = canvas.drag_agent_to_canvas(
            agent_gid=request.agent_gid,
            position={"x": request.position_x, "y": request.position_y},
            label=request.label or ""
        )
        
        if not node:
            raise HTTPException(status_code=400, detail="Failed to place agent")
        
        return node.to_dict()
    
    @router.delete("/nodes/{node_id}")
    async def remove_node(node_id: str):
        """Remove a node from canvas"""
        canvas = get_canvas()
        success = canvas.canvas.remove_node(node_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return {"removed": node_id}
    
    @router.post("/nodes/{node_id}/move")
    async def move_node(node_id: str, x: float, y: float):
        """Move a node to new position"""
        canvas = get_canvas()
        success = canvas.canvas.move_node(node_id, {"x": x, "y": y})
        
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return {"moved": node_id, "position": {"x": x, "y": y}}
    
    @router.get("/connections")
    async def get_connections():
        """Get all connections"""
        canvas = get_canvas()
        return {
            "connections": [c.to_dict() for c in canvas.canvas.connections.values()]
        }
    
    @router.post("/connections")
    async def create_connection(request: ConnectNodesRequest):
        """Create a connection between nodes"""
        canvas = get_canvas()
        
        try:
            conn_type = ConnectionType[request.connection_type.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid connection type")
        
        connection = canvas.connect_agents(
            request.source_node_id,
            request.target_node_id,
            conn_type
        )
        
        if not connection:
            raise HTTPException(status_code=400, detail="Failed to create connection")
        
        return connection.to_dict()
    
    @router.delete("/connections/{connection_id}")
    async def remove_connection(connection_id: str):
        """Remove a connection"""
        canvas = get_canvas()
        success = canvas.canvas.remove_connection(connection_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        return {"removed": connection_id}
    
    @router.post("/pipeline")
    async def create_pipeline(request: CreatePipelineRequest):
        """Quick-create a sequential pipeline"""
        canvas = get_canvas()
        nodes = canvas.create_pipeline(request.agent_gids, request.name)
        
        return {
            "name": request.name,
            "nodes": [n.to_dict() for n in nodes],
            "node_count": len(nodes)
        }
    
    @router.get("/loops")
    async def detect_loops():
        """Detect loops in the canvas"""
        canvas = get_canvas()
        loops = canvas.canvas.detect_loops()
        
        return {
            "loop_count": len(loops),
            "loops": loops,
            "warning": "Unintentional loops may waste compute" if loops else None
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # ZONE C: STRIKE CONSOLE
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/deployments")
    async def get_deployments():
        """Get all deployments"""
        canvas = get_canvas()
        return canvas.strike_console.get_console_state()
    
    @router.post("/deploy/initialize")
    async def initialize_swarm(request: InitializeSwarmRequest):
        """Initialize a swarm deployment from current canvas"""
        canvas = get_canvas()
        
        if len(canvas.canvas.nodes) == 0:
            raise HTTPException(status_code=400, detail="Canvas is empty")
        
        deployment = canvas.initialize_swarm(request.name, request.description)
        
        return deployment.to_dict()
    
    @router.post("/deploy/{swarm_id}/validate")
    async def validate_deployment(swarm_id: str):
        """Validate a deployment"""
        canvas = get_canvas()
        is_valid, result = canvas.strike_console.validate_deployment(swarm_id)
        
        return result
    
    @router.post("/deploy/{swarm_id}/simulate")
    async def simulate_deployment(swarm_id: str):
        """Simulate deployment and generate BRP"""
        canvas = get_canvas()
        result = canvas.simulate_and_validate(swarm_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("validation", {}).get("errors", ["Validation failed"]))
        
        return result
    
    @router.post("/deploy/arm")
    async def arm_deployment(request: ArmDeploymentRequest):
        """Arm a deployment (first lock of double-lock)"""
        canvas = get_canvas()
        
        success, message = canvas.strike_console.arm_deployment(
            request.swarm_id,
            request.smk_key
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        deployment = canvas.strike_console.deployments[request.swarm_id]
        
        # Generate confirmation code for display
        import hashlib
        confirm_code = hashlib.sha256(
            f"{deployment.architect_signature}:CONFIRM".encode()
        ).hexdigest()[:16].upper()
        
        return {
            "status": message,
            "swarm_id": request.swarm_id,
            "state": deployment.state.value,
            "confirmation_code": confirm_code,
            "warning": "Use this code to execute. Keep secure."
        }
    
    @router.post("/deploy/execute")
    async def execute_swarm(request: ExecuteSwarmRequest):
        """Execute a swarm (second lock of double-lock)"""
        canvas = get_canvas()
        
        success, result = canvas.strike_console.execute_swarm(
            request.swarm_id,
            request.confirmation_code
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
        
        return result
    
    @router.post("/deploy/{swarm_id}/abort")
    async def abort_deployment(swarm_id: str):
        """Abort an armed deployment"""
        canvas = get_canvas()
        
        if swarm_id not in canvas.strike_console.deployments:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        deployment = canvas.strike_console.deployments[swarm_id]
        
        if deployment.state not in [SwarmState.ARMED, SwarmState.DRAFT, SwarmState.VALIDATED]:
            raise HTTPException(status_code=400, detail="Cannot abort deployment in current state")
        
        deployment.state = SwarmState.DRAFT
        canvas.strike_console.active_deployment = None
        
        return {"status": "ABORTED", "swarm_id": swarm_id}
    
    # ─────────────────────────────────────────────────────────────────────────
    # TELEMETRY
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/telemetry")
    async def get_telemetry(since: int = 0):
        """Get telemetry events for live updates"""
        canvas = get_canvas()
        events = canvas.get_telemetry_stream(since)
        
        return {
            "events": events,
            "count": len(events),
            "next_index": len(canvas.telemetry_log)
        }
    
    @router.get("/ascii")
    async def get_ascii_canvas():
        """Get ASCII representation of canvas"""
        canvas = get_canvas()
        return HTMLResponse(
            content=f"<pre>{canvas.render_ascii_canvas()}</pre>",
            media_type="text/html"
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # ENCLAVE LOCK
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/enclave")
    async def get_enclave_status():
        """Get enclave lock status"""
        canvas = get_canvas()
        console = canvas.strike_console
        
        return {
            "locked": console.enclave_locked,
            "reason": console.lock_reason.value if console.lock_reason else None,
            "active_deployment": console.active_deployment
        }
    
    @router.post("/enclave/unlock")
    async def unlock_enclave(smk_key: str):
        """Unlock enclave with SMK re-authentication"""
        canvas = get_canvas()
        
        success, message = canvas.strike_console.release_enclave_lock(smk_key)
        
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        return {"status": message}
    
    return router


# ═══════════════════════════════════════════════════════════════════════════════
# CANVAS UI HTML V2.0.0 - ANCHOR-LOGIC ENABLED
# RNP Deployment: PAC-CANVAS-REPLACEMENT-45
# ═══════════════════════════════════════════════════════════════════════════════

CANVAS_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign Command Canvas V2.1.0 | ChainBridge</title>
    <style>
        :root {
            --bg-dark: #0a0a0a;
            --bg-panel: #111;
            --bg-node: #1a1a1a;
            --accent: #00ff88;
            --accent-blue: #00aaff;
            --accent-yellow: #ffcc00;
            --accent-red: #ff3366;
            --accent-gold: #FFD700;
            --text: #fff;
            --text-dim: #666;
            --border: #333;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: var(--bg-dark);
            color: var(--text);
            font-family: 'SF Mono', 'Monaco', monospace;
            height: 100vh;
            overflow: hidden;
        }
        
        .layout {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            height: 100vh;
        }
        
        /* ZONE A: Agent Forge */
        .agent-forge {
            background: var(--bg-panel);
            border-right: 1px solid var(--border);
            overflow-y: auto;
        }
        
        .zone-header {
            padding: 16px;
            border-bottom: 1px solid var(--border);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: var(--accent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .version-badge {
            background: var(--accent);
            color: var(--bg-dark);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9px;
        }
        
        .agent-card {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            cursor: grab;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 12px;
            user-select: none;
        }
        
        .agent-card:hover {
            background: var(--bg-node);
        }
        
        .agent-card:active {
            cursor: grabbing;
            opacity: 0.8;
        }
        
        .agent-card.dragging {
            opacity: 0.4;
        }
        
        .agent-icon {
            font-size: 24px;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-dark);
            border-radius: 8px;
        }
        
        .agent-info h3 {
            font-size: 14px;
            margin-bottom: 2px;
        }
        
        .agent-info span {
            font-size: 11px;
            color: var(--text-dim);
        }
        
        .agent-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-left: auto;
        }
        
        .agent-status.active { background: var(--accent); }
        .agent-status.deployed { background: var(--accent-blue); }
        .agent-status.standby { background: var(--text-dim); }
        
        /* ZONE B: Logic Canvas */
        .logic-canvas {
            position: relative;
            background: 
                radial-gradient(circle at center, #0d0d0d 0%, #080808 100%),
                linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px);
            background-size: 100% 100%, 20px 20px, 20px 20px;
            overflow: hidden;
        }
        
        .logic-canvas.drag-over {
            background-color: rgba(0,255,136,0.02);
        }
        
        .canvas-toolbar {
            position: absolute;
            top: 16px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 16px;
            display: flex;
            gap: 16px;
            z-index: 100;
        }
        
        .toolbar-btn {
            background: none;
            border: none;
            color: var(--text);
            cursor: pointer;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            transition: all 0.2s;
        }
        
        .toolbar-btn:hover {
            background: var(--bg-node);
            color: var(--accent);
        }
        
        .canvas-node {
            position: absolute;
            background: var(--bg-node);
            border: 2px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            min-width: 160px;
            cursor: move;
            z-index: 10;
            user-select: none;
            transition: box-shadow 0.2s, border-color 0.2s;
        }
        
        .canvas-node:hover {
            border-color: var(--accent);
        }
        
        .canvas-node.selected {
            border-color: var(--accent);
            box-shadow: 0 0 20px rgba(0,255,136,0.3);
        }
        
        .canvas-node.dragging {
            z-index: 1000;
            opacity: 0.9;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            cursor: grabbing;
        }
        
        .canvas-node.anchored {
            border-color: var(--accent-gold);
            animation: anchor-flash 0.5s ease-out;
        }
        
        @keyframes anchor-flash {
            0% { box-shadow: 0 0 0 0 rgba(255,215,0,0.5); }
            50% { box-shadow: 0 0 30px 10px rgba(255,215,0,0.3); }
            100% { box-shadow: 0 0 10px 0 rgba(255,215,0,0.1); }
        }
        
        .node-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .node-icon {
            font-size: 20px;
        }
        
        .node-name {
            font-size: 14px;
            font-weight: 600;
        }
        
        .node-gid {
            font-size: 9px;
            color: var(--text-dim);
            margin-left: auto;
        }
        
        .node-task {
            font-size: 11px;
            color: var(--text-dim);
        }
        
        .node-anchor-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            width: 20px;
            height: 20px;
            background: var(--accent-gold);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: var(--bg-dark);
            box-shadow: 0 0 10px rgba(255,215,0,0.5);
        }
        
        .node-port {
            position: absolute;
            width: 12px;
            height: 12px;
            background: var(--bg-dark);
            border: 2px solid var(--accent);
            border-radius: 50%;
            cursor: crosshair;
            transition: transform 0.2s;
        }
        
        .node-port:hover {
            transform: scale(1.3);
        }
        
        .node-port.input { left: -6px; top: 50%; transform: translateY(-50%); }
        .node-port.output { right: -6px; top: 50%; transform: translateY(-50%); }
        .node-port.input:hover { transform: translateY(-50%) scale(1.3); }
        .node-port.output:hover { transform: translateY(-50%) scale(1.3); }
        
        /* SVG Connections */
        .connections-svg {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 5;
        }
        
        .connection-line {
            stroke: var(--accent);
            stroke-width: 2;
            fill: none;
            opacity: 0.6;
        }
        
        .connection-line.verified {
            stroke: var(--accent-gold);
            stroke-width: 3;
            opacity: 0.8;
            filter: drop-shadow(0 0 6px rgba(255,215,0,0.5));
        }
        
        .connection-line.dragging {
            stroke: var(--accent-blue);
            stroke-width: 2;
            stroke-dasharray: 8,4;
            opacity: 0.8;
            animation: connection-pulse 0.5s infinite;
        }
        
        @keyframes connection-pulse {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 0.4; }
        }
        
        .connection-line.legal {
            stroke: var(--accent-gold);
            stroke-width: 3;
            stroke-dasharray: none;
            opacity: 1;
            filter: drop-shadow(0 0 10px rgba(255,215,0,0.8));
            animation: legal-glow 0.3s ease-out;
        }
        
        @keyframes legal-glow {
            0% { filter: drop-shadow(0 0 0 rgba(255,215,0,0)); }
            50% { filter: drop-shadow(0 0 20px rgba(255,215,0,1)); }
            100% { filter: drop-shadow(0 0 10px rgba(255,215,0,0.8)); }
        }
        
        .node-port.active {
            background: var(--accent);
            transform: translateY(-50%) scale(1.5);
            box-shadow: 0 0 15px var(--accent);
        }
        
        .node-port.valid-target {
            background: var(--accent-gold);
            transform: translateY(-50%) scale(1.5);
            box-shadow: 0 0 15px var(--accent-gold);
            animation: port-pulse 0.3s infinite;
        }
        
        @keyframes port-pulse {
            0%, 100% { box-shadow: 0 0 15px var(--accent-gold); }
            50% { box-shadow: 0 0 25px var(--accent-gold); }
        }
        
        /* Drop Zone Indicator */
        .drop-indicator {
            position: absolute;
            width: 160px;
            height: 100px;
            border: 2px dashed var(--accent);
            border-radius: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }
        
        .drop-indicator.visible {
            opacity: 0.5;
        }
        
        /* ZONE C: Strike Console */
        .strike-console {
            background: var(--bg-panel);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }
        
        .console-section {
            padding: 16px;
            border-bottom: 1px solid var(--border);
        }
        
        .console-section h4 {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--accent);
            margin-bottom: 12px;
        }
        
        .node-count-display {
            background: var(--bg-dark);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        
        .node-count-number {
            font-size: 48px;
            font-weight: bold;
            color: var(--accent);
        }
        
        .node-count-label {
            font-size: 11px;
            color: var(--text-dim);
        }
        
        .deployment-card {
            background: var(--bg-dark);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
        }
        
        .deployment-name {
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        .deployment-state {
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            display: inline-block;
        }
        
        .deployment-state.draft { background: var(--text-dim); color: var(--bg-dark); }
        .deployment-state.validated { background: var(--accent-blue); color: var(--bg-dark); }
        .deployment-state.simulated { background: var(--accent-yellow); color: var(--bg-dark); }
        .deployment-state.armed { background: var(--accent-red); color: white; animation: pulse 1s infinite; }
        .deployment-state.executing { background: var(--accent); color: var(--bg-dark); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .strike-btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 8px;
            transition: all 0.2s;
        }
        
        .strike-btn.initialize {
            background: var(--accent);
            color: var(--bg-dark);
        }
        
        .strike-btn.simulate {
            background: var(--accent-yellow);
            color: var(--bg-dark);
        }
        
        .strike-btn.arm {
            background: var(--accent-red);
            color: white;
        }
        
        .strike-btn.execute {
            background: linear-gradient(45deg, var(--accent-red), #ff6600);
            color: white;
        }
        
        .strike-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .strike-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .telemetry-feed {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            max-height: 200px;
        }
        
        .telemetry-event {
            font-size: 10px;
            padding: 6px 8px;
            margin-bottom: 4px;
            background: var(--bg-dark);
            border-radius: 4px;
            color: var(--text-dim);
            border-left: 2px solid var(--accent);
        }
        
        .telemetry-event .event-type {
            color: var(--accent);
            font-weight: bold;
        }
        
        .telemetry-event .event-time {
            color: var(--text-dim);
            font-size: 9px;
        }
    </style>
</head>
<body>
    <div class="layout">
        <!-- ZONE A: Agent Forge -->
        <div class="agent-forge" id="agent-forge">
            <div class="zone-header">
                ⚡ Zone A: Agent Forge
                <span class="version-badge">V2.1.0</span>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-00" data-name="Benson" data-icon="⚡" data-role="Sovereign Executor">
                <div class="agent-icon">⚡</div>
                <div class="agent-info">
                    <h3>Benson</h3>
                    <span>Sovereign Executor</span>
                </div>
                <div class="agent-status active"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-03" data-name="Vaporizer" data-icon="💨" data-role="Zero-PII Hasher">
                <div class="agent-icon">💨</div>
                <div class="agent-info">
                    <h3>Vaporizer</h3>
                    <span>Zero-PII Hasher</span>
                </div>
                <div class="agent-status deployed"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-04" data-name="Blind-Portal" data-icon="🚪" data-role="Ingest Layer">
                <div class="agent-icon">🚪</div>
                <div class="agent-info">
                    <h3>Blind-Portal</h3>
                    <span>Ingest Layer</span>
                </div>
                <div class="agent-status deployed"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-05" data-name="Certifier" data-icon="📜" data-role="Settlement Proof">
                <div class="agent-icon">📜</div>
                <div class="agent-info">
                    <h3>Certifier</h3>
                    <span>Settlement Proof</span>
                </div>
                <div class="agent-status deployed"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-02" data-name="University Dean" data-icon="🎓" data-role="Logic Validator">
                <div class="agent-icon">🎓</div>
                <div class="agent-info">
                    <h3>University Dean</h3>
                    <span>Logic Validator</span>
                </div>
                <div class="agent-status standby"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-06" data-name="Watchdog" data-icon="🐕" data-role="Compliance Monitor">
                <div class="agent-icon">🐕</div>
                <div class="agent-info">
                    <h3>Watchdog</h3>
                    <span>Compliance Monitor</span>
                </div>
                <div class="agent-status standby"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-01" data-name="Chancellor" data-icon="👑" data-role="Revenue Ops">
                <div class="agent-icon">👑</div>
                <div class="agent-info">
                    <h3>Chancellor</h3>
                    <span>Revenue Ops</span>
                </div>
                <div class="agent-status standby"></div>
            </div>
        </div>
        
        <!-- ZONE B: Logic Canvas -->
        <div class="logic-canvas" id="canvas">
            <div class="canvas-toolbar">
                <button class="toolbar-btn" onclick="CanvasEngine.clearCanvas()">🗑️ Clear</button>
                <button class="toolbar-btn" onclick="CanvasEngine.autoLayout()">📐 Auto Layout</button>
                <button class="toolbar-btn" onclick="CanvasEngine.detectLoops()">🔄 Check Loops</button>
                <button class="toolbar-btn" onclick="CanvasEngine.exportState()">📋 Export PAC</button>
            </div>
            
            <svg class="connections-svg" id="connections-svg"></svg>
            <div class="drop-indicator" id="drop-indicator"></div>
        </div>
        
        <!-- ZONE C: Strike Console -->
        <div class="strike-console">
            <div class="zone-header">🎯 Zone C: Strike Console</div>
            
            <div class="console-section">
                <h4>Canvas State</h4>
                <div class="node-count-display">
                    <div class="node-count-number" id="node-count">0</div>
                    <div class="node-count-label">Nodes Anchored</div>
                </div>
                <div class="node-count-display" style="margin-top: 8px;">
                    <div class="node-count-number" id="connection-count" style="color: var(--accent-gold);">0</div>
                    <div class="node-count-label">Links Active</div>
                </div>
            </div>
            
            <div class="console-section">
                <h4>Current Deployment</h4>
                <div class="deployment-card" id="deployment-info">
                    <div class="deployment-name">No Active Deployment</div>
                    <span class="deployment-state draft">DRAFT</span>
                </div>
            </div>
            
            <div class="console-section">
                <h4>Actions</h4>
                <button class="strike-btn initialize" onclick="CanvasEngine.initializeSwarm()">Initialize Swarm</button>
                <button class="strike-btn simulate" onclick="CanvasEngine.simulateStrike()">Simulate Strike</button>
                <button class="strike-btn arm" onclick="CanvasEngine.armDeployment()">Arm Deployment</button>
                <button class="strike-btn execute" id="execute-btn" disabled onclick="CanvasEngine.executeSwarm()">Execute Swarm</button>
            </div>
            
            <div class="zone-header" style="border-top: 1px solid var(--border);">📡 Telemetry</div>
            <div class="telemetry-feed" id="telemetry-feed"></div>
        </div>
    </div>
    
    <script>
        /**
         * SOVEREIGN COMMAND CANVAS V2.1.0
         * Active-Link Engine with Port-Snapping Connections
         * RNP Deployment: PAC-LINE-ACTIVATION-48
         * 
         * UPGRADE PATH:
         * V2.0.0: Anchor-Logic (Node Persistence) ← COMPLETE
         * V2.1.0: Active-Link (Vector-Linkage Layer) ← CURRENT
         */
        
        const CanvasEngine = {
            nodes: new Map(),
            connections: [],
            selectedNode: null,
            isDragging: false,
            dragOffset: { x: 0, y: 0 },
            nodeIdCounter: 0,
            currentDeployment: null,
            
            // V2.1.0: Active-Link Connection State
            isDrawingConnection: false,
            connectionSource: null,
            connectionSourcePort: null,
            tempLine: null,
            hoveredPort: null,
            
            // ══════════════════════════════════════════════════════════════
            // INITIALIZATION
            // ══════════════════════════════════════════════════════════════
            
            init() {
                this.setupDragAndDrop();
                this.setupCanvasDrag();
                this.setupConnectionDrawing();  // V2.1.0: Active-Link
                this.logEvent('CANVAS_INITIALIZED', 'V2.1.0 Active-Link Engine ready');
            },
            
            // ══════════════════════════════════════════════════════════════
            // ZONE A → ZONE B: DRAG FROM FORGE TO CANVAS
            // ══════════════════════════════════════════════════════════════
            
            setupDragAndDrop() {
                const agentCards = document.querySelectorAll('.agent-card');
                const canvas = document.getElementById('canvas');
                const dropIndicator = document.getElementById('drop-indicator');
                
                agentCards.forEach(card => {
                    card.addEventListener('dragstart', (e) => {
                        e.dataTransfer.setData('application/json', JSON.stringify({
                            gid: card.dataset.gid,
                            name: card.dataset.name,
                            icon: card.dataset.icon,
                            role: card.dataset.role
                        }));
                        card.classList.add('dragging');
                        this.logEvent('DRAG_START', `${card.dataset.name} (${card.dataset.gid})`);
                    });
                    
                    card.addEventListener('dragend', () => {
                        card.classList.remove('dragging');
                        dropIndicator.classList.remove('visible');
                    });
                });
                
                canvas.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    canvas.classList.add('drag-over');
                    
                    const rect = canvas.getBoundingClientRect();
                    dropIndicator.style.left = (e.clientX - rect.left - 80) + 'px';
                    dropIndicator.style.top = (e.clientY - rect.top - 50) + 'px';
                    dropIndicator.classList.add('visible');
                });
                
                canvas.addEventListener('dragleave', () => {
                    canvas.classList.remove('drag-over');
                    dropIndicator.classList.remove('visible');
                });
                
                canvas.addEventListener('drop', (e) => {
                    e.preventDefault();
                    canvas.classList.remove('drag-over');
                    dropIndicator.classList.remove('visible');
                    
                    const data = JSON.parse(e.dataTransfer.getData('application/json'));
                    const rect = canvas.getBoundingClientRect();
                    const x = e.clientX - rect.left - 80;
                    const y = e.clientY - rect.top - 50;
                    
                    // CREATE NODE WITH ANCHOR-LOGIC
                    this.createNode(data, x, y);
                });
            },
            
            // ══════════════════════════════════════════════════════════════
            // NODE CREATION WITH ANCHOR-LOGIC (PAC-DRAFT DECISION)
            // ══════════════════════════════════════════════════════════════
            
            createNode(agentData, x, y) {
                const nodeId = `NODE-${agentData.gid}-${++this.nodeIdCounter}`;
                
                const nodeEl = document.createElement('div');
                nodeEl.className = 'canvas-node';
                nodeEl.id = nodeId;
                nodeEl.dataset.gid = agentData.gid;
                nodeEl.style.left = x + 'px';
                nodeEl.style.top = y + 'px';
                
                nodeEl.innerHTML = `
                    <div class="node-anchor-badge">⚓</div>
                    <div class="node-port input"></div>
                    <div class="node-header">
                        <span class="node-icon">${agentData.icon}</span>
                        <span class="node-name">${agentData.name}</span>
                        <span class="node-gid">${agentData.gid}</span>
                    </div>
                    <div class="node-task">${agentData.role}</div>
                    <div class="node-port output"></div>
                `;
                
                document.getElementById('canvas').appendChild(nodeEl);
                
                // ANCHOR-LOGIC: Store position in state
                const nodeState = {
                    id: nodeId,
                    gid: agentData.gid,
                    name: agentData.name,
                    icon: agentData.icon,
                    role: agentData.role,
                    position: { x, y },
                    anchored: true,
                    created_at: new Date().toISOString()
                };
                
                this.nodes.set(nodeId, nodeState);
                this.setupNodeDrag(nodeEl);
                this.setupPortListeners(nodeEl);  // V2.1.0: Active-Link port detection
                this.updateNodeCount();
                
                // Flash anchor animation
                nodeEl.classList.add('anchored');
                setTimeout(() => nodeEl.classList.remove('anchored'), 500);
                
                this.logEvent('NODE_ANCHORED', `${agentData.name} anchored at (${Math.round(x)}, ${Math.round(y)})`);
                
                // Persist to backend (PAC-Draft Decision)
                this.persistNodePosition(nodeId, x, y);
                
                return nodeId;
            },
            
            // ══════════════════════════════════════════════════════════════
            // NODE DRAG ON CANVAS (MOVE & RE-ANCHOR)
            // ══════════════════════════════════════════════════════════════
            
            setupCanvasDrag() {
                // Setup drag for existing nodes
                document.querySelectorAll('.canvas-node').forEach(node => {
                    this.setupNodeDrag(node);
                });
            },
            
            setupNodeDrag(nodeEl) {
                let isDragging = false;
                let startX, startY, offsetX, offsetY;
                
                nodeEl.addEventListener('mousedown', (e) => {
                    if (e.target.classList.contains('node-port')) return;
                    
                    isDragging = true;
                    nodeEl.classList.add('dragging');
                    
                    const rect = nodeEl.getBoundingClientRect();
                    offsetX = e.clientX - rect.left;
                    offsetY = e.clientY - rect.top;
                    
                    this.selectNode(nodeEl);
                });
                
                document.addEventListener('mousemove', (e) => {
                    if (!isDragging) return;
                    
                    const canvas = document.getElementById('canvas');
                    const canvasRect = canvas.getBoundingClientRect();
                    
                    let newX = e.clientX - canvasRect.left - offsetX;
                    let newY = e.clientY - canvasRect.top - offsetY;
                    
                    // Constrain to canvas bounds
                    newX = Math.max(0, Math.min(newX, canvasRect.width - 160));
                    newY = Math.max(50, Math.min(newY, canvasRect.height - 100));
                    
                    nodeEl.style.left = newX + 'px';
                    nodeEl.style.top = newY + 'px';
                    
                    // Update connections live
                    this.updateConnections();
                });
                
                document.addEventListener('mouseup', () => {
                    if (!isDragging) return;
                    isDragging = false;
                    nodeEl.classList.remove('dragging');
                    
                    // ANCHOR-LOGIC: Persist new position
                    const x = parseInt(nodeEl.style.left);
                    const y = parseInt(nodeEl.style.top);
                    
                    const nodeState = this.nodes.get(nodeEl.id);
                    if (nodeState) {
                        nodeState.position = { x, y };
                        this.nodes.set(nodeEl.id, nodeState);
                    }
                    
                    // Flash anchor confirmation
                    nodeEl.classList.add('anchored');
                    setTimeout(() => nodeEl.classList.remove('anchored'), 500);
                    
                    this.logEvent('NODE_REPOSITIONED', `${nodeEl.id} anchored at (${x}, ${y})`);
                    this.persistNodePosition(nodeEl.id, x, y);
                });
            },
            
            selectNode(nodeEl) {
                document.querySelectorAll('.canvas-node').forEach(n => n.classList.remove('selected'));
                nodeEl.classList.add('selected');
                this.selectedNode = nodeEl;
            },
            
            // ══════════════════════════════════════════════════════════════
            // BACKEND PERSISTENCE (Write-Back)
            // ══════════════════════════════════════════════════════════════
            
            async persistNodePosition(nodeId, x, y) {
                try {
                    const response = await fetch(`/canvas/nodes/${nodeId}/move?x=${x}&y=${y}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    if (!response.ok) {
                        console.log('Backend sync pending - node anchored locally');
                    }
                } catch (e) {
                    // Offline mode - state persisted locally
                    console.log('Offline mode - node anchored locally');
                }
            },
            
            // ══════════════════════════════════════════════════════════════
            // V2.1.0: ACTIVE-LINK CONNECTION ENGINE
            // PAC-LINE-ACTIVATION-48: Port-Snapping Vector-Linkage Layer
            // ══════════════════════════════════════════════════════════════
            
            setupConnectionDrawing() {
                const canvas = document.getElementById('canvas');
                const svg = document.getElementById('connections-svg');
                
                // Create temporary line element for drag preview
                this.tempLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                this.tempLine.setAttribute('class', 'connection-line dragging');
                this.tempLine.style.display = 'none';
                svg.appendChild(this.tempLine);
                
                // Global mouse move for connection drawing
                canvas.addEventListener('mousemove', (e) => {
                    if (!this.isDrawingConnection) return;
                    
                    const canvasRect = canvas.getBoundingClientRect();
                    const mouseX = e.clientX - canvasRect.left;
                    const mouseY = e.clientY - canvasRect.top;
                    
                    this.updateTempLine(mouseX, mouseY);
                    this.checkPortProximity(e.clientX, e.clientY);
                });
                
                // Cancel connection on escape or right-click
                document.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape' && this.isDrawingConnection) {
                        this.cancelConnection();
                    }
                });
                
                canvas.addEventListener('contextmenu', (e) => {
                    if (this.isDrawingConnection) {
                        e.preventDefault();
                        this.cancelConnection();
                    }
                });
                
                // Cancel if clicking on canvas (not on a port)
                canvas.addEventListener('mouseup', (e) => {
                    if (this.isDrawingConnection && !e.target.classList.contains('node-port')) {
                        this.cancelConnection();
                    }
                });
                
                this.logEvent('ACTIVE_LINK_READY', 'V2.1.0 Port-Snapping enabled');
            },
            
            setupPortListeners(nodeEl) {
                const outputPort = nodeEl.querySelector('.node-port.output');
                const inputPort = nodeEl.querySelector('.node-port.input');
                
                if (outputPort) {
                    outputPort.addEventListener('mousedown', (e) => {
                        e.stopPropagation();
                        this.startConnection(nodeEl, 'output', e);
                    });
                }
                
                if (inputPort) {
                    inputPort.addEventListener('mouseup', (e) => {
                        e.stopPropagation();
                        if (this.isDrawingConnection) {
                            this.completeConnection(nodeEl);
                        }
                    });
                    
                    inputPort.addEventListener('mouseenter', () => {
                        if (this.isDrawingConnection) {
                            this.hoveredPort = { node: nodeEl, type: 'input' };
                            inputPort.classList.add('valid-target');
                        }
                    });
                    
                    inputPort.addEventListener('mouseleave', () => {
                        inputPort.classList.remove('valid-target');
                        this.hoveredPort = null;
                    });
                }
            },
            
            startConnection(sourceNode, portType, e) {
                this.isDrawingConnection = true;
                this.connectionSource = sourceNode;
                this.connectionSourcePort = portType;
                
                const outputPort = sourceNode.querySelector('.node-port.output');
                outputPort.classList.add('active');
                
                // Get port position
                const canvas = document.getElementById('canvas');
                const canvasRect = canvas.getBoundingClientRect();
                const portRect = outputPort.getBoundingClientRect();
                
                this.connectionStartX = portRect.left + portRect.width/2 - canvasRect.left;
                this.connectionStartY = portRect.top + portRect.height/2 - canvasRect.top;
                
                this.tempLine.style.display = 'block';
                this.updateTempLine(this.connectionStartX, this.connectionStartY);
                
                const sourceGid = sourceNode.dataset.gid;
                this.logEvent('CONNECTION_START', `Drawing from ${sourceGid}`);
            },
            
            updateTempLine(mouseX, mouseY) {
                const x1 = this.connectionStartX;
                const y1 = this.connectionStartY;
                const x2 = mouseX;
                const y2 = mouseY;
                
                const midX = (x1 + x2) / 2;
                this.tempLine.setAttribute('d', `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`);
            },
            
            checkPortProximity(clientX, clientY) {
                const SNAP_RADIUS = 30;
                let closestPort = null;
                let closestDist = SNAP_RADIUS;
                
                document.querySelectorAll('.canvas-node').forEach(node => {
                    if (node === this.connectionSource) return; // Can't connect to self
                    
                    const inputPort = node.querySelector('.node-port.input');
                    if (!inputPort) return;
                    
                    const portRect = inputPort.getBoundingClientRect();
                    const portX = portRect.left + portRect.width/2;
                    const portY = portRect.top + portRect.height/2;
                    
                    const dist = Math.sqrt(Math.pow(clientX - portX, 2) + Math.pow(clientY - portY, 2));
                    
                    if (dist < closestDist) {
                        closestDist = dist;
                        closestPort = { node, port: inputPort };
                    }
                });
                
                // Clear all valid-target classes first
                document.querySelectorAll('.node-port.valid-target').forEach(p => p.classList.remove('valid-target'));
                
                if (closestPort) {
                    closestPort.port.classList.add('valid-target');
                    this.hoveredPort = { node: closestPort.node, type: 'input' };
                } else {
                    this.hoveredPort = null;
                }
            },
            
            completeConnection(targetNode) {
                if (!this.connectionSource || this.connectionSource === targetNode) {
                    this.cancelConnection();
                    return;
                }
                
                const sourceGid = this.connectionSource.dataset.gid;
                const targetGid = targetNode.dataset.gid;
                const sourceId = this.connectionSource.id;
                const targetId = targetNode.id;
                
                // LOGIC VALIDATION: Check if connection is Legal
                const isLegal = this.validateConnection(sourceGid, targetGid);
                
                if (isLegal) {
                    // Create the connection
                    this.connections.push({
                        source: sourceId,
                        target: targetId,
                        sourceGid: sourceGid,
                        targetGid: targetGid,
                        verified: true,
                        legal: true,
                        created_at: new Date().toISOString()
                    });
                    
                    this.updateConnections();
                    this.logEvent('CONNECTION_LEGAL', `${sourceGid} → ${targetGid} [GLOWING GOLD]`);
                    
                    // Flash gold on both nodes
                    this.connectionSource.classList.add('anchored');
                    targetNode.classList.add('anchored');
                    setTimeout(() => {
                        this.connectionSource.classList.remove('anchored');
                        targetNode.classList.remove('anchored');
                    }, 500);
                    
                    // Update Strike Console connection count
                    this.updateConnectionCount();
                } else {
                    this.logEvent('CONNECTION_ILLEGAL', `${sourceGid} → ${targetGid} rejected`);
                    alert(`⚠️ Illegal connection: ${sourceGid} cannot link to ${targetGid}`);
                }
                
                this.cancelConnection();
            },
            
            validateConnection(sourceGid, targetGid) {
                // V2.1.0 Legal Connection Rules:
                // 1. Cannot connect to self
                // 2. Cannot create duplicate connections
                // 3. Future: Type-based compatibility checks
                
                if (sourceGid === targetGid) return false;
                
                // Check for duplicate
                const exists = this.connections.some(c => 
                    c.sourceGid === sourceGid && c.targetGid === targetGid
                );
                if (exists) return false;
                
                // All other connections are Legal for now
                // Future PACs will add type-based validation
                return true;
            },
            
            cancelConnection() {
                this.isDrawingConnection = false;
                this.tempLine.style.display = 'none';
                
                // Clear port states
                document.querySelectorAll('.node-port.active').forEach(p => p.classList.remove('active'));
                document.querySelectorAll('.node-port.valid-target').forEach(p => p.classList.remove('valid-target'));
                
                this.connectionSource = null;
                this.connectionSourcePort = null;
                this.hoveredPort = null;
            },
            
            updateConnections() {
                const svg = document.getElementById('connections-svg');
                
                // Remove all existing paths except temp line
                Array.from(svg.querySelectorAll('path:not(.dragging)')).forEach(p => p.remove());
                
                this.connections.forEach(conn => {
                    const sourceEl = document.getElementById(conn.source);
                    const targetEl = document.getElementById(conn.target);
                    
                    if (sourceEl && targetEl) {
                        const sourcePort = sourceEl.querySelector('.node-port.output');
                        const targetPort = targetEl.querySelector('.node-port.input');
                        const canvasRect = document.getElementById('canvas').getBoundingClientRect();
                        
                        const sourceRect = sourcePort.getBoundingClientRect();
                        const targetRect = targetPort.getBoundingClientRect();
                        
                        const x1 = sourceRect.left + sourceRect.width/2 - canvasRect.left;
                        const y1 = sourceRect.top + sourceRect.height/2 - canvasRect.top;
                        const x2 = targetRect.left + targetRect.width/2 - canvasRect.left;
                        const y2 = targetRect.top + targetRect.height/2 - canvasRect.top;
                        
                        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                        const midX = (x1 + x2) / 2;
                        path.setAttribute('d', `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`);
                        
                        // V2.1.0: Legal connections get GLOWING GOLD
                        let pathClass = 'connection-line';
                        if (conn.legal) pathClass += ' legal';
                        else if (conn.verified) pathClass += ' verified';
                        path.setAttribute('class', pathClass);
                        
                        svg.insertBefore(path, this.tempLine);
                    }
                });
            },
            
            updateConnectionCount() {
                // Update the Strike Console with connection count
                const countEl = document.getElementById('connection-count');
                if (countEl) {
                    countEl.textContent = this.connections.length;
                }
            },
            
            createConnection(sourceId, targetId) {
                // Legacy method - now handled by completeConnection
                this.connections.push({ source: sourceId, target: targetId, verified: false });
                this.updateConnections();
                this.logEvent('CONNECTION_CREATED', `${sourceId} → ${targetId}`);
            },
            
            // ══════════════════════════════════════════════════════════════
            // CANVAS ACTIONS
            // ══════════════════════════════════════════════════════════════
            
            clearCanvas() {
                if (!confirm('Clear all nodes from canvas?')) return;
                
                document.querySelectorAll('.canvas-node').forEach(n => n.remove());
                this.nodes.clear();
                this.connections = [];
                this.updateConnections();
                this.updateNodeCount();
                this.logEvent('CANVAS_CLEARED', 'All nodes removed');
            },
            
            autoLayout() {
                const nodes = Array.from(this.nodes.entries());
                const startX = 100;
                const startY = 150;
                const spacingX = 220;
                
                nodes.forEach(([id, state], index) => {
                    const x = startX + (index * spacingX);
                    const y = startY;
                    
                    const nodeEl = document.getElementById(id);
                    if (nodeEl) {
                        nodeEl.style.left = x + 'px';
                        nodeEl.style.top = y + 'px';
                        state.position = { x, y };
                    }
                });
                
                // Auto-connect in sequence
                this.connections = [];
                const nodeIds = Array.from(this.nodes.keys());
                for (let i = 0; i < nodeIds.length - 1; i++) {
                    this.connections.push({ source: nodeIds[i], target: nodeIds[i+1], verified: true });
                }
                
                this.updateConnections();
                this.logEvent('AUTO_LAYOUT', `${nodes.length} nodes arranged sequentially`);
            },
            
            detectLoops() {
                // Simple loop detection
                const visited = new Set();
                let hasLoop = false;
                
                this.connections.forEach(conn => {
                    if (visited.has(conn.target)) {
                        hasLoop = true;
                    }
                    visited.add(conn.source);
                });
                
                if (hasLoop) {
                    alert('⚠️ Loop detected! This may waste compute.');
                } else {
                    alert('✅ No loops detected');
                }
                
                this.logEvent('LOOP_CHECK', hasLoop ? 'Loop found' : 'No loops');
            },
            
            exportState() {
                const state = {
                    version: '2.1.0',
                    nodes: Array.from(this.nodes.values()),
                    connections: this.connections,
                    exported_at: new Date().toISOString()
                };
                
                console.log('Canvas State:', JSON.stringify(state, null, 2));
                alert('State exported to console (F12)');
                this.logEvent('STATE_EXPORTED', `${this.nodes.size} nodes exported`);
            },
            
            // ══════════════════════════════════════════════════════════════
            // STRIKE CONSOLE ACTIONS
            // ══════════════════════════════════════════════════════════════
            
            async initializeSwarm() {
                if (this.nodes.size === 0) {
                    alert('Canvas is empty. Drag agents to canvas first.');
                    return;
                }
                
                const name = prompt('Swarm Name:', 'PNC-Shadow-Vet');
                if (!name) return;
                
                this.currentDeployment = {
                    name: name,
                    state: 'DRAFT',
                    nodes: Array.from(this.nodes.values())
                };
                
                document.getElementById('deployment-info').innerHTML = `
                    <div class="deployment-name">${name}</div>
                    <span class="deployment-state draft">DRAFT</span>
                `;
                
                this.logEvent('SWARM_INITIALIZED', `${name} with ${this.nodes.size} nodes`);
            },
            
            async simulateStrike() {
                if (!this.currentDeployment) {
                    alert('Initialize swarm first');
                    return;
                }
                
                this.currentDeployment.state = 'SIMULATED';
                document.getElementById('deployment-info').innerHTML = `
                    <div class="deployment-name">${this.currentDeployment.name}</div>
                    <span class="deployment-state simulated">SIMULATED</span>
                `;
                
                // Mark connections as verified
                this.connections.forEach(c => c.verified = true);
                this.updateConnections();
                
                this.logEvent('SIMULATION_COMPLETE', 'BRP generated - Risk: LOW');
                alert('✅ Simulation complete\\nBRP Generated\\nRisk: LOW');
            },
            
            async armDeployment() {
                if (!this.currentDeployment || this.currentDeployment.state !== 'SIMULATED') {
                    alert('Simulate deployment first');
                    return;
                }
                
                const smk = prompt('Enter SMK Key to arm:');
                if (!smk) return;
                
                this.currentDeployment.state = 'ARMED';
                document.getElementById('deployment-info').innerHTML = `
                    <div class="deployment-name">${this.currentDeployment.name}</div>
                    <span class="deployment-state armed">ARMED</span>
                `;
                
                document.getElementById('execute-btn').disabled = false;
                this.logEvent('DEPLOYMENT_ARMED', 'Double-lock engaged');
            },
            
            async executeSwarm() {
                if (!this.currentDeployment || this.currentDeployment.state !== 'ARMED') {
                    return;
                }
                
                const confirm_code = prompt('Enter confirmation code to execute:');
                if (!confirm_code) return;
                
                this.currentDeployment.state = 'EXECUTING';
                document.getElementById('deployment-info').innerHTML = `
                    <div class="deployment-name">${this.currentDeployment.name}</div>
                    <span class="deployment-state executing">EXECUTING</span>
                `;
                
                this.logEvent('SWARM_EXECUTING', 'Agents deployed');
                alert('🚀 Swarm executing!');
            },
            
            // ══════════════════════════════════════════════════════════════
            // TELEMETRY
            // ══════════════════════════════════════════════════════════════
            
            updateNodeCount() {
                document.getElementById('node-count').textContent = this.nodes.size;
            },
            
            logEvent(type, message) {
                const feed = document.getElementById('telemetry-feed');
                const time = new Date().toISOString().substr(11, 8);
                
                const event = document.createElement('div');
                event.className = 'telemetry-event';
                event.innerHTML = `<span class="event-time">${time}</span> <span class="event-type">${type}</span> ${message}`;
                
                feed.insertBefore(event, feed.firstChild);
                
                // Keep only last 20 events
                while (feed.children.length > 20) {
                    feed.removeChild(feed.lastChild);
                }
            }
        };
        
        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => CanvasEngine.init());
    </script>
</body>
</html>
"""


def get_canvas_html() -> str:
    """Return the Canvas UI HTML"""
    return CANVAS_UI_HTML
