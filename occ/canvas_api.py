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
# CANVAS UI HTML
# ═══════════════════════════════════════════════════════════════════════════════

CANVAS_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sovereign Command Canvas | ChainBridge</title>
    <style>
        :root {
            --bg-dark: #0a0a0a;
            --bg-panel: #111;
            --bg-node: #1a1a1a;
            --accent: #00ff88;
            --accent-blue: #00aaff;
            --accent-yellow: #ffcc00;
            --accent-red: #ff3366;
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
        }
        
        .agent-card {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            cursor: grab;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .agent-card:hover {
            background: var(--bg-node);
        }
        
        .agent-card:active {
            cursor: grabbing;
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
        }
        
        .toolbar-btn:hover {
            background: var(--bg-node);
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
        }
        
        .canvas-node:hover {
            border-color: var(--accent);
        }
        
        .canvas-node.selected {
            border-color: var(--accent);
            box-shadow: 0 0 20px rgba(0,255,136,0.2);
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
        
        .node-task {
            font-size: 11px;
            color: var(--text-dim);
        }
        
        .node-port {
            position: absolute;
            width: 12px;
            height: 12px;
            background: var(--bg-dark);
            border: 2px solid var(--accent);
            border-radius: 50%;
            cursor: crosshair;
        }
        
        .node-port.input { left: -6px; top: 50%; transform: translateY(-50%); }
        .node-port.output { right: -6px; top: 50%; transform: translateY(-50%); }
        
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
            padding: 16px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-top: 8px;
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
            animation: pulse 0.5s infinite;
        }
        
        .strike-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .brp-display {
            background: var(--bg-dark);
            border-radius: 8px;
            padding: 12px;
            font-size: 11px;
        }
        
        .brp-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        
        .brp-label { color: var(--text-dim); }
        .brp-value { color: var(--accent); }
        
        .telemetry-feed {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
        }
        
        .telemetry-event {
            font-size: 10px;
            padding: 4px 8px;
            margin-bottom: 4px;
            background: var(--bg-dark);
            border-radius: 4px;
            color: var(--text-dim);
        }
        
        .telemetry-event .event-type {
            color: var(--accent);
        }
    </style>
</head>
<body>
    <div class="layout">
        <!-- ZONE A: Agent Forge -->
        <div class="agent-forge">
            <div class="zone-header">⚡ Zone A: Agent Forge</div>
            
            <div class="agent-card" draggable="true" data-gid="GID-00">
                <div class="agent-icon">⚡</div>
                <div class="agent-info">
                    <h3>Benson</h3>
                    <span>Sovereign Executor</span>
                </div>
                <div class="agent-status active"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-03">
                <div class="agent-icon">💨</div>
                <div class="agent-info">
                    <h3>Vaporizer</h3>
                    <span>Zero-PII Hasher</span>
                </div>
                <div class="agent-status deployed"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-04">
                <div class="agent-icon">🚪</div>
                <div class="agent-info">
                    <h3>Blind-Portal</h3>
                    <span>Ingest Layer</span>
                </div>
                <div class="agent-status deployed"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-05">
                <div class="agent-icon">📜</div>
                <div class="agent-info">
                    <h3>Certifier</h3>
                    <span>Settlement Proof</span>
                </div>
                <div class="agent-status deployed"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-02">
                <div class="agent-icon">🎓</div>
                <div class="agent-info">
                    <h3>University Dean</h3>
                    <span>Logic Validator</span>
                </div>
                <div class="agent-status standby"></div>
            </div>
            
            <div class="agent-card" draggable="true" data-gid="GID-06">
                <div class="agent-icon">🐕</div>
                <div class="agent-info">
                    <h3>Watchdog</h3>
                    <span>Compliance Monitor</span>
                </div>
                <div class="agent-status standby"></div>
            </div>
        </div>
        
        <!-- ZONE B: Logic Canvas -->
        <div class="logic-canvas" id="canvas">
            <div class="canvas-toolbar">
                <button class="toolbar-btn" onclick="clearCanvas()">🗑️ Clear</button>
                <button class="toolbar-btn" onclick="autoLayout()">📐 Auto Layout</button>
                <button class="toolbar-btn" onclick="detectLoops()">🔄 Check Loops</button>
                <button class="toolbar-btn" onclick="generatePAC()">📋 Export PAC</button>
            </div>
            
            <!-- Demo nodes -->
            <div class="canvas-node" style="left: 100px; top: 200px;">
                <div class="node-port input"></div>
                <div class="node-header">
                    <span class="node-icon">💨</span>
                    <span class="node-name">Vaporizer</span>
                </div>
                <div class="node-task">Hash PII Data</div>
                <div class="node-port output"></div>
            </div>
            
            <div class="canvas-node" style="left: 320px; top: 200px;">
                <div class="node-port input"></div>
                <div class="node-header">
                    <span class="node-icon">🚪</span>
                    <span class="node-name">Blind-Portal</span>
                </div>
                <div class="node-task">Ingest & Screen</div>
                <div class="node-port output"></div>
            </div>
            
            <div class="canvas-node" style="left: 540px; top: 200px;">
                <div class="node-port input"></div>
                <div class="node-header">
                    <span class="node-icon">📜</span>
                    <span class="node-name">Certifier</span>
                </div>
                <div class="node-task">Generate Proof</div>
                <div class="node-port output"></div>
            </div>
        </div>
        
        <!-- ZONE C: Strike Console -->
        <div class="strike-console">
            <div class="zone-header">🎯 Zone C: Strike Console</div>
            
            <div class="console-section">
                <h4>Current Deployment</h4>
                <div class="deployment-card">
                    <div class="deployment-name">PNC-Shadow-Vet</div>
                    <span class="deployment-state simulated">SIMULATED</span>
                </div>
            </div>
            
            <div class="console-section">
                <h4>Binary Reason Proof</h4>
                <div class="brp-display">
                    <div class="brp-row">
                        <span class="brp-label">BRP ID:</span>
                        <span class="brp-value">BRP-7A3F2D1E</span>
                    </div>
                    <div class="brp-row">
                        <span class="brp-label">Compute:</span>
                        <span class="brp-value">140ms</span>
                    </div>
                    <div class="brp-row">
                        <span class="brp-label">Cost:</span>
                        <span class="brp-value">$0.000014</span>
                    </div>
                    <div class="brp-row">
                        <span class="brp-label">Risk:</span>
                        <span class="brp-value">LOW</span>
                    </div>
                </div>
            </div>
            
            <div class="console-section">
                <h4>Actions</h4>
                <button class="strike-btn initialize">Initialize Swarm</button>
                <button class="strike-btn simulate">Simulate Strike</button>
                <button class="strike-btn arm">Arm Deployment</button>
                <button class="strike-btn execute" disabled>Execute Swarm</button>
            </div>
            
            <div class="zone-header" style="border-top: 1px solid var(--border);">📡 Live Telemetry</div>
            <div class="telemetry-feed">
                <div class="telemetry-event">
                    <span class="event-type">AGENT_PLACED</span> Vaporizer at (100,200)
                </div>
                <div class="telemetry-event">
                    <span class="event-type">AGENT_PLACED</span> Blind-Portal at (320,200)
                </div>
                <div class="telemetry-event">
                    <span class="event-type">CONNECTION_CREATED</span> Sequential link
                </div>
                <div class="telemetry-event">
                    <span class="event-type">PIPELINE_CREATED</span> PNC-Shadow-Vet
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Canvas drag-drop functionality placeholder
        const canvas = document.getElementById('canvas');
        
        function clearCanvas() {
            alert('Canvas cleared');
        }
        
        function autoLayout() {
            alert('Auto layout applied');
        }
        
        function detectLoops() {
            alert('No loops detected ✓');
        }
        
        function generatePAC() {
            alert('PAC schema exported');
        }
    </script>
</body>
</html>
"""


def get_canvas_html() -> str:
    """Return the Canvas UI HTML"""
    return CANVAS_UI_HTML
