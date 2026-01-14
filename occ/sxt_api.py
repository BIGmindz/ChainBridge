"""
ChainBridge Sovereign Swarm - SxT Prover API
PAC-SXT-PROVER-UI-40 | Visual Data Finality REST Interface

Provides REST endpoints and HTML UI for SxT Proof-of-SQL verification.
Integrates with Command Canvas to display verification badges.

Endpoints:
- GET  /sxt/health         - Health check
- GET  /sxt/status         - Integration status
- POST /sxt/badge          - Create verification badge
- POST /sxt/tunnel         - Create verifiable tunnel
- GET  /sxt/overlay        - Get canvas overlay data
- GET  /sxt/stream         - SSE stream of proof events
- GET  /sxt/ui             - HTML verification dashboard

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import asyncio
from datetime import datetime, timezone

from .sxt_prover import (
    SxTCanvasIntegration,
    SxTProverClient,
    VerificationBadgeManager,
    ProofStreamManager,
    CanvasMode,
    BadgeState,
    ProofStatus,
    SXT_PROVER_VERSION,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER SETUP
# ═══════════════════════════════════════════════════════════════════════════════

router = APIRouter(prefix="/sxt", tags=["sxt-prover"])

# Global integration instance
_sxt_integration: Optional[SxTCanvasIntegration] = None


def get_integration() -> SxTCanvasIntegration:
    """Get or create the SxT integration instance"""
    global _sxt_integration
    if _sxt_integration is None:
        _sxt_integration = SxTCanvasIntegration()
        _sxt_integration.initialize()
    return _sxt_integration


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateBadgeRequest(BaseModel):
    node_id: str
    agent_gid: str
    agent_name: str


class CreateTunnelRequest(BaseModel):
    source_node_id: str
    target_node_id: str


class VerifyFlowRequest(BaseModel):
    node_ids: List[str]


class SetModeRequest(BaseModel):
    mode: str  # IDLE, ACTIVE_EXECUTION, AUDIT_REPLAY


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sxt-prover",
        "version": SXT_PROVER_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/status")
async def get_status():
    """Get complete integration status"""
    integration = get_integration()
    return integration.get_complete_state()


@router.post("/badge")
async def create_badge(request: CreateBadgeRequest):
    """Create a verification badge for a canvas node"""
    integration = get_integration()
    result = integration.create_node_badge(
        node_id=request.node_id,
        agent_gid=request.agent_gid,
        agent_name=request.agent_name
    )
    return result


@router.post("/tunnel")
async def create_tunnel(request: CreateTunnelRequest):
    """Create a verifiable tunnel between nodes"""
    integration = get_integration()
    result = integration.create_connection_tunnel(
        source_node_id=request.source_node_id,
        target_node_id=request.target_node_id
    )
    return result


@router.post("/verify-flow")
async def verify_flow(request: VerifyFlowRequest):
    """Verify an entire swarm flow"""
    integration = get_integration()
    result = integration.verify_swarm_flow(request.node_ids)
    return result


@router.get("/overlay")
async def get_overlay():
    """Get the visual overlay data for the canvas"""
    integration = get_integration()
    return integration.get_canvas_overlay()


@router.post("/mode")
async def set_mode(request: SetModeRequest):
    """Set the canvas display mode"""
    integration = get_integration()
    
    mode_map = {
        "IDLE": CanvasMode.IDLE,
        "ACTIVE_EXECUTION": CanvasMode.ACTIVE_EXECUTION,
        "AUDIT_REPLAY": CanvasMode.AUDIT_REPLAY
    }
    
    if request.mode not in mode_map:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    
    integration.badge_manager.set_canvas_mode(mode_map[request.mode])
    return {"mode": request.mode, "applied": True}


@router.get("/stream")
async def stream_events():
    """Server-Sent Events stream of proof events"""
    integration = get_integration()
    queue = integration.stream_manager.subscribe()
    
    async def event_generator():
        yield f"data: {json.dumps({'event': 'connected', 'stream_id': integration.stream_manager.stream_id})}\n\n"
        
        while True:
            try:
                # Check for events
                if not queue.empty():
                    event = queue.get_nowait()
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    # Send heartbeat
                    await asyncio.sleep(1)
                    yield f": heartbeat\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/history")
async def get_event_history(limit: int = 100):
    """Get proof event history"""
    integration = get_integration()
    return {
        "events": integration.stream_manager.get_event_history(limit),
        "total_events": len(integration.stream_manager.events)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HTML UI
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ui", response_class=HTMLResponse)
async def sxt_ui():
    """SxT Prover verification dashboard"""
    integration = get_integration()
    stats = integration.get_complete_state()
    overlay = integration.get_canvas_overlay()
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SxT Prover | ChainBridge Sovereign Swarm</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%);
            color: #e0e0e0;
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        .header {{
            background: linear-gradient(90deg, rgba(255, 215, 0, 0.1), transparent);
            border-bottom: 2px solid #FFD700;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header h1 {{
            font-size: 1.5em;
            color: #FFD700;
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }}
        
        .header .subtitle {{
            color: #888;
            font-size: 0.85em;
        }}
        
        .sxt-icon {{
            font-size: 2em;
        }}
        
        .status-bar {{
            background: #111;
            padding: 15px 30px;
            display: flex;
            gap: 40px;
            border-bottom: 1px solid #333;
        }}
        
        .status-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .status-label {{
            color: #666;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .status-value {{
            font-size: 1.4em;
            font-weight: bold;
        }}
        
        .status-value.gold {{ color: #FFD700; }}
        .status-value.green {{ color: #00FF88; }}
        .status-value.blue {{ color: #00D4FF; }}
        
        .container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 20px 30px;
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .panel {{
            background: rgba(20, 20, 30, 0.8);
            border: 1px solid #333;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .panel-header {{
            background: linear-gradient(90deg, #1a1a2e, #0f0f1a);
            padding: 15px 20px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .panel-header h2 {{
            font-size: 1em;
            color: #FFD700;
        }}
        
        .panel-body {{
            padding: 20px;
        }}
        
        .badge-grid {{
            display: grid;
            gap: 15px;
        }}
        
        .badge-card {{
            background: rgba(30, 30, 40, 0.5);
            border: 1px solid #444;
            border-radius: 6px;
            padding: 15px;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: all 0.3s ease;
        }}
        
        .badge-card:hover {{
            border-color: #FFD700;
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.1);
        }}
        
        .badge-icon {{
            font-size: 2em;
            width: 50px;
            text-align: center;
        }}
        
        .badge-icon.verified {{
            color: #FFD700;
            text-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
            animation: pulse 2s infinite;
        }}
        
        .badge-icon.pending {{
            color: #666;
        }}
        
        .badge-icon.error {{
            color: #FF3366;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        .badge-info {{
            flex: 1;
        }}
        
        .badge-node {{
            font-weight: bold;
            color: #fff;
        }}
        
        .badge-tooltip {{
            font-size: 0.85em;
            color: #888;
            margin-top: 4px;
        }}
        
        .badge-status {{
            font-size: 0.75em;
            padding: 4px 10px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        
        .badge-status.verified {{
            background: rgba(255, 215, 0, 0.2);
            color: #FFD700;
            border: 1px solid #FFD700;
        }}
        
        .badge-status.pending {{
            background: rgba(100, 100, 100, 0.2);
            color: #888;
            border: 1px solid #666;
        }}
        
        .tunnel-list {{
            display: grid;
            gap: 10px;
        }}
        
        .tunnel-item {{
            display: flex;
            align-items: center;
            padding: 12px 15px;
            background: rgba(30, 30, 40, 0.5);
            border-radius: 6px;
            border: 1px solid #333;
        }}
        
        .tunnel-node {{
            padding: 6px 12px;
            background: #1a1a2e;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        
        .tunnel-connector {{
            flex: 1;
            height: 3px;
            margin: 0 10px;
            border-radius: 2px;
            position: relative;
        }}
        
        .tunnel-connector.verified {{
            background: linear-gradient(90deg, #FFD700, #FFA500, #FFD700);
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            animation: glow 2s infinite;
        }}
        
        .tunnel-connector.unverified {{
            background: #00D4FF;
        }}
        
        @keyframes glow {{
            0%, 100% {{ box-shadow: 0 0 10px rgba(255, 215, 0, 0.5); }}
            50% {{ box-shadow: 0 0 20px rgba(255, 215, 0, 0.8); }}
        }}
        
        .event-stream {{
            height: 300px;
            overflow-y: auto;
            font-size: 0.85em;
        }}
        
        .event-item {{
            padding: 8px 12px;
            border-bottom: 1px solid #222;
            display: flex;
            gap: 10px;
        }}
        
        .event-time {{
            color: #666;
            white-space: nowrap;
        }}
        
        .event-type {{
            color: #FFD700;
            font-weight: bold;
            width: 150px;
        }}
        
        .event-payload {{
            color: #888;
            flex: 1;
        }}
        
        .legend {{
            background: rgba(30, 30, 40, 0.5);
            padding: 15px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        
        .legend h3 {{
            font-size: 0.9em;
            color: #888;
            margin-bottom: 10px;
        }}
        
        .legend-items {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85em;
        }}
        
        .mode-selector {{
            display: flex;
            gap: 10px;
        }}
        
        .mode-btn {{
            padding: 8px 16px;
            background: #1a1a2e;
            border: 1px solid #444;
            border-radius: 4px;
            color: #888;
            cursor: pointer;
            font-family: inherit;
            font-size: 0.85em;
            transition: all 0.3s ease;
        }}
        
        .mode-btn:hover {{
            border-color: #FFD700;
            color: #FFD700;
        }}
        
        .mode-btn.active {{
            background: rgba(255, 215, 0, 0.1);
            border-color: #FFD700;
            color: #FFD700;
        }}
        
        .full-width {{
            grid-column: 1 / -1;
        }}
        
        .proof-chain {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            padding: 15px;
            background: #0a0a0f;
            border-radius: 6px;
            max-height: 200px;
            overflow-y: auto;
            font-size: 0.8em;
            font-family: monospace;
        }}
        
        .proof-chain-item {{
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px solid #1a1a2e;
        }}
        
        .refresh-btn {{
            padding: 8px 20px;
            background: linear-gradient(135deg, #FFD700, #FFA500);
            border: none;
            border-radius: 4px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
            font-family: inherit;
        }}
        
        .refresh-btn:hover {{
            transform: scale(1.05);
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🔐 SxT PROVER | PROOF OF SQL</h1>
            <div class="subtitle">Space and Time Verification Layer • Decentralized Data Finality</div>
        </div>
        <div class="sxt-icon">⛓️</div>
    </div>
    
    <div class="status-bar">
        <div class="status-item">
            <span class="status-label">Session</span>
            <span class="status-value blue">{stats['sxt_client']['session_id']}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Block Height</span>
            <span class="status-value gold">{stats['sxt_client']['block_height']:,}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Verified Badges</span>
            <span class="status-value green">{stats['badge_manager']['verified_badges']}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Verified Tunnels</span>
            <span class="status-value green">{stats['badge_manager']['verified_tunnels']}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Canvas Mode</span>
            <span class="status-value gold">{overlay['mode']}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Total Gas</span>
            <span class="status-value">{stats['sxt_client']['total_gas_used']:,}</span>
        </div>
    </div>
    
    <div class="container">
        <div class="panel full-width">
            <div class="panel-header">
                <h2>📊 BADGE LEGEND & MODE CONTROL</h2>
                <div class="mode-selector">
                    <button class="mode-btn {'active' if overlay['mode'] == 'IDLE' else ''}" onclick="setMode('IDLE')">IDLE</button>
                    <button class="mode-btn {'active' if overlay['mode'] == 'ACTIVE_EXECUTION' else ''}" onclick="setMode('ACTIVE_EXECUTION')">ACTIVE EXECUTION</button>
                    <button class="mode-btn {'active' if overlay['mode'] == 'AUDIT_REPLAY' else ''}" onclick="setMode('AUDIT_REPLAY')">AUDIT REPLAY</button>
                </div>
            </div>
            <div class="panel-body">
                <div class="legend">
                    <h3>VISUAL ELEMENTS</h3>
                    <div class="legend-items">
                        <div class="legend-item"><span style="color: #FFD700; font-size: 1.5em;">🔐</span> Verified Badge (ZKP Anchored)</div>
                        <div class="legend-item"><span style="color: #666; font-size: 1.5em;">⏳</span> Pending Verification</div>
                        <div class="legend-item"><span style="color: #FF3366; font-size: 1.5em;">❌</span> Verification Failed</div>
                        <div class="legend-item">
                            <div style="width: 60px; height: 4px; background: linear-gradient(90deg, #FFD700, #FFA500, #FFD700); border-radius: 2px; box-shadow: 0 0 8px rgba(255, 215, 0, 0.5);"></div>
                            <span>Glowing Gold (Verified Tunnel)</span>
                        </div>
                        <div class="legend-item">
                            <div style="width: 60px; height: 4px; background: #00D4FF; border-radius: 2px;"></div>
                            <span>Blue Standard (Unverified)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-header">
                <h2>🔐 VERIFICATION BADGES</h2>
                <span style="color: #888;">{len(overlay['badges'])} visible</span>
            </div>
            <div class="panel-body">
                <div class="badge-grid">
                    {''.join(f"""
                    <div class="badge-card">
                        <div class="badge-icon {'verified' if badge['state'] == 'VERIFIED' else 'pending' if badge['state'] == 'PENDING' else 'error'}">{badge['icon']}</div>
                        <div class="badge-info">
                            <div class="badge-node">{badge['node_id']}</div>
                            <div class="badge-tooltip">{badge['tooltip']}</div>
                        </div>
                        <span class="badge-status {'verified' if badge['state'] == 'VERIFIED' else 'pending'}">{badge['state']}</span>
                    </div>
                    """ for badge in overlay['badges']) or '<div style="color: #666; padding: 20px; text-align: center;">No badges visible in current mode</div>'}
                </div>
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-header">
                <h2>🌟 VERIFIABLE TUNNELS</h2>
                <span style="color: #888;">{len(overlay['tunnels'])} tunnels</span>
            </div>
            <div class="panel-body">
                <div class="tunnel-list">
                    {''.join(f"""
                    <div class="tunnel-item">
                        <span class="tunnel-node">{tunnel['source']}</span>
                        <div class="tunnel-connector {'verified' if tunnel['glow'] else 'unverified'}"></div>
                        <span class="tunnel-node">{tunnel['target']}</span>
                    </div>
                    """ for tunnel in overlay['tunnels']) or '<div style="color: #666; padding: 20px; text-align: center;">No tunnels created</div>'}
                </div>
            </div>
        </div>
        
        <div class="panel full-width">
            <div class="panel-header">
                <h2>📜 PROOF STREAM EVENTS</h2>
                <button class="refresh-btn" onclick="location.reload()">↻ REFRESH</button>
            </div>
            <div class="panel-body">
                <div class="event-stream" id="event-stream">
                    <div style="color: #666; padding: 20px; text-align: center;">Connecting to proof stream...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Mode selector
        function setMode(mode) {{
            fetch('/sxt/mode', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{mode: mode}})
            }}).then(() => location.reload());
        }}
        
        // Event stream
        const eventSource = new EventSource('/sxt/stream');
        const eventContainer = document.getElementById('event-stream');
        
        eventSource.onmessage = function(event) {{
            const data = JSON.parse(event.data);
            if (data.event === 'connected') {{
                eventContainer.innerHTML = '';
            }}
            
            const eventItem = document.createElement('div');
            eventItem.className = 'event-item';
            eventItem.innerHTML = `
                <span class="event-time">${{new Date().toISOString().substr(11, 8)}}</span>
                <span class="event-type">${{data.event_type || data.event || 'HEARTBEAT'}}</span>
                <span class="event-payload">${{JSON.stringify(data.payload || {{}}).substr(0, 100)}}</span>
            `;
            eventContainer.insertBefore(eventItem, eventContainer.firstChild);
            
            // Keep only last 50 events
            while (eventContainer.children.length > 50) {{
                eventContainer.removeChild(eventContainer.lastChild);
            }}
        }};
        
        eventSource.onerror = function() {{
            const errorItem = document.createElement('div');
            errorItem.className = 'event-item';
            errorItem.innerHTML = '<span class="event-type" style="color: #FF3366;">CONNECTION LOST</span>';
            eventContainer.insertBefore(errorItem, eventContainer.firstChild);
        }};
    </script>
</body>
</html>
"""
    return html


# ═══════════════════════════════════════════════════════════════════════════════
# CANVAS INTEGRATION OVERLAY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/canvas-overlay-css")
async def get_overlay_css():
    """Get CSS for integrating badges into the canvas"""
    css = """
/* SxT Prover Canvas Overlay Styles */

.sxt-badge {
    position: absolute;
    top: -10px;
    right: -10px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    z-index: 100;
    cursor: pointer;
    transition: all 0.3s ease;
}

.sxt-badge.verified {
    background: linear-gradient(135deg, #FFD700, #FFA500);
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
    animation: sxt-pulse 2s infinite;
}

.sxt-badge.pending {
    background: #444;
    color: #888;
}

.sxt-badge.error {
    background: #FF3366;
    color: #fff;
}

@keyframes sxt-pulse {
    0%, 100% { 
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
        transform: scale(1);
    }
    50% { 
        box-shadow: 0 0 25px rgba(255, 215, 0, 0.9);
        transform: scale(1.1);
    }
}

.sxt-tunnel.verified path {
    stroke: url(#sxt-gold-gradient) !important;
    stroke-width: 3px !important;
    filter: drop-shadow(0 0 6px rgba(255, 215, 0, 0.5));
    animation: sxt-glow 2s infinite;
}

@keyframes sxt-glow {
    0%, 100% { filter: drop-shadow(0 0 6px rgba(255, 215, 0, 0.5)); }
    50% { filter: drop-shadow(0 0 12px rgba(255, 215, 0, 0.8)); }
}

.sxt-tooltip {
    position: absolute;
    background: rgba(10, 10, 15, 0.95);
    border: 1px solid #FFD700;
    border-radius: 6px;
    padding: 10px 15px;
    font-size: 12px;
    color: #e0e0e0;
    z-index: 1000;
    pointer-events: none;
    max-width: 300px;
}

.sxt-tooltip .query-id {
    color: #FFD700;
    font-family: monospace;
}

.sxt-tooltip .proof-hash {
    color: #888;
    font-family: monospace;
    font-size: 10px;
    word-break: break-all;
}
"""
    return {"css": css}


@router.get("/canvas-overlay-js")
async def get_overlay_js():
    """Get JavaScript for integrating badges into the canvas"""
    js = """
// SxT Prover Canvas Overlay Integration

class SxTOverlay {
    constructor() {
        this.badges = new Map();
        this.tunnels = new Map();
        this.mode = 'IDLE';
        this.eventSource = null;
    }
    
    async init() {
        // Fetch initial overlay state
        const response = await fetch('/sxt/overlay');
        const data = await response.json();
        
        this.mode = data.mode;
        this.badges = new Map(data.badges.map(b => [b.node_id, b]));
        this.tunnels = new Map(data.tunnels.map(t => [`${t.source}-${t.target}`, t]));
        
        // Connect to event stream
        this.connectStream();
        
        // Render initial state
        this.render();
    }
    
    connectStream() {
        this.eventSource = new EventSource('/sxt/stream');
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.event_type === 'BADGE_CREATED' || data.event_type === 'BADGE_VERIFIED') {
                this.badges.set(data.payload.node_id, data.payload);
                this.renderBadge(data.payload.node_id);
            }
            
            if (data.event_type === 'TUNNEL_CREATED') {
                const key = `${data.payload.source_node_id}-${data.payload.target_node_id}`;
                this.tunnels.set(key, data.payload);
                this.renderTunnel(key);
            }
        };
    }
    
    render() {
        if (this.mode === 'IDLE') {
            this.hideAll();
            return;
        }
        
        this.badges.forEach((badge, nodeId) => this.renderBadge(nodeId));
        this.tunnels.forEach((tunnel, key) => this.renderTunnel(key));
    }
    
    renderBadge(nodeId) {
        const badge = this.badges.get(nodeId);
        if (!badge) return;
        
        const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
        if (!nodeElement) return;
        
        let badgeEl = nodeElement.querySelector('.sxt-badge');
        if (!badgeEl) {
            badgeEl = document.createElement('div');
            badgeEl.className = 'sxt-badge';
            nodeElement.appendChild(badgeEl);
        }
        
        badgeEl.className = `sxt-badge ${badge.state.toLowerCase()}`;
        badgeEl.innerHTML = badge.icon;
        badgeEl.title = badge.tooltip;
    }
    
    renderTunnel(key) {
        const tunnel = this.tunnels.get(key);
        if (!tunnel) return;
        
        const connectionEl = document.querySelector(`[data-connection="${key}"]`);
        if (!connectionEl) return;
        
        if (tunnel.glow) {
            connectionEl.classList.add('sxt-tunnel', 'verified');
        } else {
            connectionEl.classList.remove('verified');
        }
    }
    
    hideAll() {
        document.querySelectorAll('.sxt-badge').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.sxt-tunnel').forEach(el => el.classList.remove('verified'));
    }
}

// Initialize on load
window.sxtOverlay = new SxTOverlay();
document.addEventListener('DOMContentLoaded', () => window.sxtOverlay.init());
"""
    return {"js": js}
