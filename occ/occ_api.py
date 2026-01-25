"""
OCC FastAPI REST Endpoints
Operators Control in Command - HTTP Interface

Provides secure REST API for the OCC Command Center.
SECURITY: All endpoints require Sovereign Master Key authentication.

Endpoints:
- /occ/admin - Main dashboard
- /occ/command-center - Full command interface
- /occ/lanes - Quad-Lane Monitor
- /occ/gates - Gate Heatmap
- /occ/ticker - PDO Ticker
- /occ/arr - ARR Counter
- /occ/kill-switch - Kill Switch status (restricted)

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
PAC: PAC-OCC-COMMAND-34
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTITUTIONAL GATEWAY - RUNTIME VERSION LOCK
# PAC-CORRECTIVE-ENV-LOCK-59 Addendum-A
# ZERO-DRIFT ENFORCEMENT: Python 3.11.14 REQUIRED
# ═══════════════════════════════════════════════════════════════════════════════
import sys
_REQUIRED_VERSION = (3, 11, 14)
if sys.version_info[:3] != _REQUIRED_VERSION:
    print("═" * 72)
    print("  ██████╗ ██████╗ ███╗   ██╗███████╗████████╗██╗████████╗██╗   ██╗")
    print(" ██╔════╝██╔═══██╗████╗  ██║██╔════╝╚══██╔══╝██║╚══██╔══╝╚██╗ ██╔╝")
    print(" ██║     ██║   ██║██╔██╗ ██║███████╗   ██║   ██║   ██║    ╚████╔╝ ")
    print(" ██║     ██║   ██║██║╚██╗██║╚════██║   ██║   ██║   ██║     ╚██╔╝  ")
    print(" ╚██████╗╚██████╔╝██║ ╚████║███████║   ██║   ██║   ██║      ██║   ")
    print("  ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝   ╚═╝      ╚═╝   ")
    print("              D R I F T   D E T E C T E D")
    print("═" * 72)
    print(f"  CRITICAL: CONSTITUTIONAL RUNTIME VIOLATION")
    print(f"  REQUIRED: Python {'.'.join(map(str, _REQUIRED_VERSION))}")
    print(f"  DETECTED: Python {'.'.join(map(str, sys.version_info[:3]))}")
    print(f"  ACTION:   FAIL-CLOSED - Execution halted")
    print("═" * 72)
    sys.exit(1)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import hmac
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Optional
from functools import wraps

try:
    from fastapi import FastAPI, HTTPException, Header, Depends, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
    WEBSOCKET_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    WEBSOCKET_AVAILABLE = False
    FastAPI = None

from occ.command_center import (
    OCCCommandCenter,
    AlertLevel,
    KillSwitchState,
    LaneStatus,
    GateStatus,
    GENESIS_ANCHOR,
    OCC_VERSION,
)

# V2.0.0 Canvas UI with Anchor-Logic (PAC-CANVAS-REPLACEMENT-45)
from occ.canvas_api import CANVAS_UI_HTML


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    class KillSwitchArmRequest(BaseModel):
        authorization_code: str
    
    class KillSwitchTriggerRequest(BaseModel):
        confirmation_code: str
    
    class AlertRequest(BaseModel):
        level: str
        source: str
        message: str
    
    class GateUpdateRequest(BaseModel):
        gate_id: int
        status: str


# ═══════════════════════════════════════════════════════════════════════════════
# OCC API ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

# Global OCC instance
_occ_instance: Optional[OCCCommandCenter] = None


def get_occ() -> OCCCommandCenter:
    """Get or create OCC instance"""
    global _occ_instance
    if _occ_instance is None:
        _occ_instance = OCCCommandCenter()
    return _occ_instance


def create_occ_router():
    """Create FastAPI router for OCC endpoints"""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available. Install with: pip install fastapi uvicorn")
    
    from fastapi import APIRouter
    router = APIRouter(prefix="/occ", tags=["OCC Command Center"])
    
    # ─────────────────────────────────────────────────────────────────────────
    # AUTHENTICATION
    # ─────────────────────────────────────────────────────────────────────────
    
    async def verify_sovereign_key(x_sovereign_key: str = Header(None)) -> bool:
        """Verify Sovereign Master Key from header"""
        if not x_sovereign_key:
            raise HTTPException(status_code=401, detail="Sovereign Master Key required")
        
        occ = get_occ()
        valid, key_obj, reason = occ.authenticate(x_sovereign_key)
        
        if not valid:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {reason}")
        
        return True
    
    # ─────────────────────────────────────────────────────────────────────────
    # DASHBOARD ENDPOINTS
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/health")
    async def occ_health():
        """Health check - no auth required"""
        return {
            "status": "OPERATIONAL",
            "version": OCC_VERSION,
            "genesis": GENESIS_ANCHOR,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @router.get("/admin")
    async def admin_dashboard(auth: bool = Depends(verify_sovereign_key)):
        """Main admin dashboard data"""
        occ = get_occ()
        return occ.get_dashboard_state()
    
    @router.get("/command-center")
    async def command_center(auth: bool = Depends(verify_sovereign_key)):
        """Full command center state"""
        occ = get_occ()
        state = occ.get_dashboard_state()
        state["session_log"] = occ.session_log[-50:]
        return state
    
    @router.get("/command-center/ascii")
    async def command_center_ascii(auth: bool = Depends(verify_sovereign_key)):
        """ASCII dashboard for terminal display"""
        occ = get_occ()
        return HTMLResponse(
            content=f"<pre>{occ.render_ascii_dashboard()}</pre>",
            media_type="text/html"
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # QUAD-LANE MONITOR
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/lanes")
    async def get_lanes(auth: bool = Depends(verify_sovereign_key)):
        """Get Quad-Lane Monitor snapshot"""
        occ = get_occ()
        return occ.quad_lane.get_snapshot()
    
    @router.post("/lanes/simulate")
    async def simulate_lanes(auth: bool = Depends(verify_sovereign_key)):
        """Simulate lane activity for testing"""
        occ = get_occ()
        occ.quad_lane.simulate_activity()
        return {"status": "SIMULATED", "lanes": occ.quad_lane.get_snapshot()}
    
    # ─────────────────────────────────────────────────────────────────────────
    # GATE HEATMAP
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/gates")
    async def get_gates(auth: bool = Depends(verify_sovereign_key)):
        """Get Gate Heatmap snapshot"""
        occ = get_occ()
        return occ.gate_heatmap.get_snapshot()
    
    @router.get("/gates/ascii")
    async def get_gates_ascii(auth: bool = Depends(verify_sovereign_key)):
        """Get ASCII heatmap"""
        occ = get_occ()
        ascii_map = occ.gate_heatmap.get_ascii_heatmap(40)
        return {"ascii": ascii_map, "stats": occ.gate_heatmap.gate_stats}
    
    @router.post("/gates/{gate_id}/trigger")
    async def trigger_gate(gate_id: int, auth: bool = Depends(verify_sovereign_key)):
        """Trigger a specific gate (mark as blocked)"""
        occ = get_occ()
        if gate_id < 0 or gate_id >= 10000:
            raise HTTPException(status_code=400, detail="Invalid gate_id (0-9999)")
        
        success = occ.gate_heatmap.trigger_gate(gate_id)
        return {"gate_id": gate_id, "triggered": success}
    
    @router.post("/gates/{gate_id}/reset")
    async def reset_gate(gate_id: int, auth: bool = Depends(verify_sovereign_key)):
        """Reset a gate to compliant"""
        occ = get_occ()
        if gate_id < 0 or gate_id >= 10000:
            raise HTTPException(status_code=400, detail="Invalid gate_id (0-9999)")
        
        occ.gate_heatmap.reset_gate(gate_id)
        return {"gate_id": gate_id, "status": "COMPLIANT"}
    
    # ─────────────────────────────────────────────────────────────────────────
    # PDO TICKER
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/ticker")
    async def get_ticker(count: int = 10, auth: bool = Depends(verify_sovereign_key)):
        """Get recent PDO units"""
        occ = get_occ()
        return {
            "recent": occ.pdo_ticker.get_recent(min(count, 100)),
            "stats": occ.pdo_ticker.get_stats()
        }
    
    @router.get("/ticker/stats")
    async def get_ticker_stats(auth: bool = Depends(verify_sovereign_key)):
        """Get PDO ticker statistics"""
        occ = get_occ()
        return occ.pdo_ticker.get_stats()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ARR COUNTER
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/arr")
    async def get_arr(auth: bool = Depends(verify_sovereign_key)):
        """Get ARR Counter display"""
        occ = get_occ()
        return occ.arr_counter.get_display()
    
    @router.get("/arr/history")
    async def get_arr_history(auth: bool = Depends(verify_sovereign_key)):
        """Get ARR update history"""
        occ = get_occ()
        return {
            "current": occ.arr_counter.get_display(),
            "history": occ.arr_counter.history[-50:]
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # KILL SWITCH (RESTRICTED)
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/kill-switch")
    async def get_kill_switch(auth: bool = Depends(verify_sovereign_key)):
        """Get Kill Switch status"""
        occ = get_occ()
        status = occ.kill_switch.get_status()
        status["arm_code_for_architect"] = occ.kill_switch.get_arm_code("ARCHITECT-JEFFREY")
        return status
    
    @router.post("/kill-switch/arm")
    async def arm_kill_switch(
        request: KillSwitchArmRequest,
        auth: bool = Depends(verify_sovereign_key)
    ):
        """Arm the Kill Switch - requires authorization code"""
        occ = get_occ()
        success, message = occ.kill_switch.arm("ARCHITECT-JEFFREY", request.authorization_code)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        occ.add_alert(AlertLevel.CRITICAL, "KILL_SWITCH", "Kill Switch has been ARMED")
        return {"success": True, "message": message, "status": occ.kill_switch.get_status()}
    
    @router.post("/kill-switch/safe")
    async def safe_kill_switch(auth: bool = Depends(verify_sovereign_key)):
        """Return Kill Switch to safe state"""
        occ = get_occ()
        success, message = occ.kill_switch.safe("ARCHITECT-JEFFREY")
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {"success": True, "message": message, "status": occ.kill_switch.get_status()}
    
    @router.post("/kill-switch/trigger")
    async def trigger_kill_switch(
        request: KillSwitchTriggerRequest,
        auth: bool = Depends(verify_sovereign_key)
    ):
        """Trigger Kill Switch - EMERGENCY STOP - requires confirmation code"""
        occ = get_occ()
        success, message = occ.kill_switch.trigger("ARCHITECT-JEFFREY", request.confirmation_code)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        occ.add_alert(AlertLevel.EMERGENCY, "KILL_SWITCH", "Kill Switch TRIGGERED - MESH HALTED")
        return {"success": True, "message": message, "status": occ.kill_switch.get_status()}
    
    # ─────────────────────────────────────────────────────────────────────────
    # ALERTS
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.get("/alerts")
    async def get_alerts(auth: bool = Depends(verify_sovereign_key)):
        """Get all alerts"""
        occ = get_occ()
        return {
            "active": [a.to_dict() for a in occ.alerts if not a.acknowledged],
            "all": [a.to_dict() for a in occ.alerts[-100:]],
            "total": len(occ.alerts)
        }
    
    @router.post("/alerts")
    async def create_alert(request: AlertRequest, auth: bool = Depends(verify_sovereign_key)):
        """Create a new alert"""
        occ = get_occ()
        
        try:
            level = AlertLevel[request.level.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid alert level")
        
        alert = occ.add_alert(level, request.source, request.message)
        return alert.to_dict()
    
    @router.post("/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(alert_id: str, auth: bool = Depends(verify_sovereign_key)):
        """Acknowledge an alert"""
        occ = get_occ()
        
        for alert in occ.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return {"alert_id": alert_id, "acknowledged": True}
        
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # ─────────────────────────────────────────────────────────────────────────
    # KEY MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    @router.post("/keys/bootstrap")
    async def bootstrap_key():
        """
        Bootstrap: Generate first Sovereign Master Key - UNAUTHENTICATED
        Only works when NO active keys exist (first-run protection)
        """
        occ = get_occ()
        
        # Security: Only allow if no active keys exist
        if len(occ.key_manager.active_keys) > 0:
            raise HTTPException(
                status_code=403, 
                detail="Bootstrap denied: Active keys already exist. Use /keys/generate with authentication."
            )
        
        raw_key, key_obj = occ.generate_master_key()
        
        return {
            "warning": "🔐 STORE THIS KEY SECURELY - IT WILL NOT BE SHOWN AGAIN",
            "notice": "This is your ONLY bootstrap key. Use it to authenticate and generate additional keys.",
            "key_id": key_obj.key_id,
            "raw_key": raw_key,
            "expires_at": key_obj.expires_at,
            "permissions": key_obj.permissions,
            "usage_example": f'curl -H "X-Sovereign-Key: {raw_key}" http://localhost:8080/occ/admin'
        }
    
    @router.post("/keys/generate")
    async def generate_key(auth: bool = Depends(verify_sovereign_key)):
        """Generate a new Sovereign Master Key - REQUIRES AUTHENTICATION"""
        occ = get_occ()
        raw_key, key_obj = occ.generate_master_key()
        
        return {
            "warning": "STORE THIS KEY SECURELY - IT WILL NOT BE SHOWN AGAIN",
            "key_id": key_obj.key_id,
            "raw_key": raw_key,
            "expires_at": key_obj.expires_at,
            "permissions": key_obj.permissions
        }
    
    @router.get("/keys/active")
    async def list_active_keys(auth: bool = Depends(verify_sovereign_key)):
        """List active key IDs (not raw keys)"""
        occ = get_occ()
        return {
            "active_keys": [
                k.to_dict() for k in occ.key_manager.active_keys.values()
                if k.key_id not in occ.key_manager.revoked_keys
            ]
        }
    
    return router


# ═══════════════════════════════════════════════════════════════════════════════
# HTML DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

OCC_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCC Command Center | ChainBridge Sovereign</title>
    <style>
        :root {
            --bg-primary: #0a0a0a;
            --bg-secondary: #111111;
            --bg-panel: #1a1a1a;
            --accent-green: #00ff88;
            --accent-red: #ff3366;
            --accent-yellow: #ffcc00;
            --accent-blue: #00aaff;
            --text-primary: #ffffff;
            --text-secondary: #888888;
            --border-color: #333333;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Courier New', monospace;
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(90deg, var(--bg-secondary), var(--bg-panel));
            border-bottom: 2px solid var(--accent-green);
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 24px;
            font-weight: bold;
            color: var(--accent-green);
        }
        
        .logo span { color: var(--text-secondary); }
        
        .status-bar {
            display: flex;
            gap: 20px;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-dot.green { background: var(--accent-green); }
        .status-dot.red { background: var(--accent-red); }
        .status-dot.yellow { background: var(--accent-yellow); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            gap: 20px;
            padding: 20px;
            height: calc(100vh - 80px);
        }
        
        .panel {
            background: var(--bg-panel);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .panel-header {
            background: var(--bg-secondary);
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 12px;
            color: var(--accent-green);
        }
        
        .panel-body {
            padding: 16px;
        }
        
        .arr-display {
            text-align: center;
            padding: 30px;
        }
        
        .arr-value {
            font-size: 36px;
            font-weight: bold;
            color: var(--accent-green);
            text-shadow: 0 0 20px var(--accent-green);
        }
        
        .arr-label {
            font-size: 14px;
            color: var(--text-secondary);
            margin-top: 10px;
        }
        
        .progress-bar {
            background: var(--bg-secondary);
            height: 8px;
            border-radius: 4px;
            margin-top: 20px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-green), var(--accent-blue));
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .lane {
            display: flex;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .lane:last-child { border-bottom: none; }
        
        .lane-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 12px;
        }
        
        .lane-indicator.active { background: var(--accent-green); animation: pulse 1s infinite; }
        .lane-indicator.idle { background: var(--text-secondary); }
        .lane-indicator.blocked { background: var(--accent-red); }
        
        .lane-name {
            flex: 1;
            font-size: 13px;
        }
        
        .lane-latency {
            font-size: 12px;
            color: var(--accent-blue);
        }
        
        .gate-grid {
            display: grid;
            grid-template-columns: repeat(20, 1fr);
            gap: 2px;
            padding: 10px;
        }
        
        .gate-cell {
            aspect-ratio: 1;
            background: var(--accent-green);
            border-radius: 2px;
            opacity: 0.6;
        }
        
        .gate-cell.blocked {
            background: var(--accent-red);
            opacity: 1;
        }
        
        .kill-switch {
            text-align: center;
            padding: 30px;
        }
        
        .kill-switch-btn {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 4px solid var(--accent-red);
            background: transparent;
            color: var(--accent-red);
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .kill-switch-btn:hover {
            background: var(--accent-red);
            color: var(--bg-primary);
        }
        
        .kill-switch-btn.armed {
            border-color: var(--accent-yellow);
            color: var(--accent-yellow);
            animation: pulse 0.5s infinite;
        }
        
        .pdo-item {
            padding: 10px;
            border-bottom: 1px solid var(--border-color);
            font-size: 12px;
        }
        
        .pdo-hash {
            color: var(--accent-blue);
            font-family: monospace;
        }
        
        .pdo-decision {
            color: var(--accent-green);
            margin-left: 10px;
        }
        
        .pdo-outcome {
            color: var(--text-secondary);
            margin-left: 10px;
        }
        
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }
        
        .epoch { color: var(--accent-blue); }
        .genesis { color: var(--text-secondary); }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">OCC <span>| Operators Control in Command</span></div>
        <div class="status-bar">
            <div class="status-item">
                <div class="status-dot green"></div>
                <span>MESH ONLINE</span>
            </div>
            <div class="status-item">
                <div class="status-dot green"></div>
                <span>KILL SWITCH: SAFE</span>
            </div>
            <div class="status-item">
                <div class="status-dot green"></div>
                <span>GATES: 100%</span>
            </div>
        </div>
    </header>
    
    <main class="main-grid">
        <div class="left-column">
            <div class="panel">
                <div class="panel-header">ARR Counter</div>
                <div class="panel-body arr-display">
                    <div class="arr-value">$13,197,500</div>
                    <div class="arr-label">Annual Recurring Revenue</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 13.2%"></div>
                    </div>
                    <div class="arr-label">13.2% to $100M Target</div>
                </div>
            </div>
            
            <div class="panel" style="margin-top: 20px;">
                <div class="panel-header">Kill Switch</div>
                <div class="panel-body kill-switch">
                    <button class="kill-switch-btn">
                        EMERGENCY<br>STOP
                    </button>
                    <div class="arr-label" style="margin-top: 20px;">Status: SAFE</div>
                </div>
            </div>
        </div>
        
        <div class="center-column">
            <div class="panel">
                <div class="panel-header">Gate Heatmap (10,000 Law-Gates)</div>
                <div class="panel-body">
                    <div class="gate-grid" id="gateGrid"></div>
                </div>
            </div>
            
            <div class="panel" style="margin-top: 20px;">
                <div class="panel-header">Quad-Lane Monitor</div>
                <div class="panel-body">
                    <div class="lane">
                        <div class="lane-indicator active"></div>
                        <div class="lane-name">L1: PROOF-INGESTION</div>
                        <div class="lane-latency">0.42ms</div>
                    </div>
                    <div class="lane">
                        <div class="lane-indicator active"></div>
                        <div class="lane-name">L2: GATE-VALIDATION</div>
                        <div class="lane-latency">0.18ms</div>
                    </div>
                    <div class="lane">
                        <div class="lane-indicator idle"></div>
                        <div class="lane-name">L3: DECISION-ENGINE</div>
                        <div class="lane-latency">0.00ms</div>
                    </div>
                    <div class="lane">
                        <div class="lane-indicator active"></div>
                        <div class="lane-name">L4: OUTCOME-SETTLEMENT</div>
                        <div class="lane-latency">1.23ms</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="right-column">
            <div class="panel" style="height: 100%;">
                <div class="panel-header">PDO Ticker</div>
                <div class="panel-body" id="pdoTicker">
                    <div class="pdo-item">
                        <span class="pdo-hash">a7f3b9c2...</span>
                        <span class="pdo-decision">APPROVED</span>
                        <span class="pdo-outcome">SETTLED</span>
                    </div>
                    <div class="pdo-item">
                        <span class="pdo-hash">d8e1f4a5...</span>
                        <span class="pdo-decision">COMPLIANT</span>
                        <span class="pdo-outcome">CAPTURED</span>
                    </div>
                    <div class="pdo-item">
                        <span class="pdo-hash">b2c9d6e7...</span>
                        <span class="pdo-decision">APPROVED</span>
                        <span class="pdo-outcome">SETTLED</span>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <footer class="footer">
        <div class="epoch">EPOCH: EPOCH_001</div>
        <div class="genesis">Genesis: GENESIS-SOVEREIGN-2026-01-14</div>
        <div>OCC v1.0.0 | ChainBridge Sovereign Systems</div>
    </footer>
    
    <script>
        // Initialize gate grid
        const gateGrid = document.getElementById('gateGrid');
        for (let i = 0; i < 400; i++) {
            const cell = document.createElement('div');
            cell.className = 'gate-cell';
            gateGrid.appendChild(cell);
        }
    </script>
</body>
</html>
"""


def create_occ_app() -> "FastAPI":
    """Create complete OCC FastAPI application"""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available")
    
    from pathlib import Path
    
    # Import UI Push Service for WebSocket support
    from occ.ui_push_service import (
        get_session_manager,
        get_push_service,
        handle_websocket_connection,
        AgentStatePayload,
        CanvasStatePayload,
        TelemetryPayload,
        CURRENT_SWARM_ID,
    )
    from occ.command_canvas import AgentForge, SovereignCommandCanvas, SwarmState
    
    app = FastAPI(
        title="OCC Command Center",
        description="Operators Control in Command - ChainBridge Sovereign Systems",
        version=OCC_VERSION
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize singleton services
    session_manager = get_session_manager()
    push_service = get_push_service()
    agent_forge = AgentForge()
    command_canvas = SovereignCommandCanvas()
    occ = get_occ()
    
    # ─────────────────────────────────────────────────────────────────────────
    # STATE PROVIDERS FOR WEBSOCKET BROADCAST
    # ─────────────────────────────────────────────────────────────────────────
    
    def provide_agent_state() -> AgentStatePayload:
        """Provide current agent forge state"""
        roster = agent_forge.get_roster()
        agents = [a.to_dict() for a in agent_forge.agents.values()]
        return AgentStatePayload(
            timestamp=datetime.now(timezone.utc).isoformat(),
            swarm_id=CURRENT_SWARM_ID,
            agents=agents,
            active_count=roster.get("active", 0),
            deployed_count=roster.get("deployed", 0),
            total_count=roster.get("total_agents", 10)
        )
    
    def provide_canvas_state() -> CanvasStatePayload:
        """Provide current canvas state"""
        state = command_canvas.get_canvas_state()
        return CanvasStatePayload(
            timestamp=datetime.now(timezone.utc).isoformat(),
            swarm_id=CURRENT_SWARM_ID,
            nodes=[n.to_dict() for n in state.get("nodes", [])],
            connections=[c.to_dict() for c in state.get("connections", [])],
            execution_state=state.get("execution_state", "IDLE")
        )
    
    def provide_telemetry() -> TelemetryPayload:
        """Provide current telemetry"""
        dashboard = occ.get_dashboard_state()
        gate_stats = dashboard.get("gate_stats", {})
        return TelemetryPayload(
            timestamp=datetime.now(timezone.utc).isoformat(),
            arr_usd=dashboard.get("arr_usd", 13197500.00),
            arr_target_usd=100000000.00,
            arr_progress_pct=dashboard.get("arr_progress", 13.2),
            gates_compliant=gate_stats.get("compliant", 9950),
            gates_blocked=gate_stats.get("blocked", 50),
            gates_total=10000,
            lanes_active=sum(1 for l in dashboard.get("lanes", []) if l.get("status") == "EXECUTING"),
            epoch="EPOCH_001"
        )
    
    # Register state providers
    push_service.register_state_provider("agents", provide_agent_state)
    push_service.register_state_provider("canvas", provide_canvas_state)
    push_service.register_state_provider("telemetry", provide_telemetry)
    
    # ─────────────────────────────────────────────────────────────────────────
    # WEBSOCKET ENDPOINT - PAC-UI-HANDSHAKE-INIT-42
    # ─────────────────────────────────────────────────────────────────────────
    
    @app.websocket("/ws/occ")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for live OCC updates"""
        await handle_websocket_connection(websocket, session_manager, push_service)
    
    @app.on_event("startup")
    async def startup_event():
        """Start push service on app startup"""
        await push_service.start()
        print("[OCC] UI Push Service started - WebSocket bridge active")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Stop push service on app shutdown"""
        await push_service.stop()
    
    # Mount OCC router
    app.include_router(create_occ_router())
    
    # ─────────────────────────────────────────────────────────────────────────
    # SOVEREIGN ENTRY LANDING PAGE - PAC-LANDING-PAGE-41
    # ─────────────────────────────────────────────────────────────────────────
    
    @app.get("/", response_class=HTMLResponse)
    async def sovereign_entry():
        """Sovereign Entry landing page - SMK authentication portal"""
        template_path = Path(__file__).parent / "templates" / "login.html"
        if template_path.exists():
            return HTMLResponse(content=template_path.read_text())
        # Fallback to direct dashboard if template missing
        return HTMLResponse(content=OCC_DASHBOARD_HTML)
    
    @app.get("/occ/canvas", response_class=HTMLResponse)
    async def occ_canvas():
        """Visual OCC Command Canvas V2.0.0 - Anchor-Logic enabled (PAC-CANVAS-REPLACEMENT-45)"""
        # V2.0.0: Direct HTML injection with Anchor-Logic - no template fallback
        return HTMLResponse(content=CANVAS_UI_HTML)
    
    @app.get("/occ/ui", response_class=HTMLResponse)
    async def occ_ui():
        """Legacy UI endpoint - redirects to canvas"""
        return HTMLResponse(content=OCC_DASHBOARD_HTML)
    
    # ─────────────────────────────────────────────────────────────────────────
    # SESSION STATUS ENDPOINT
    # ─────────────────────────────────────────────────────────────────────────
    
    @app.get("/occ/session-status")
    async def session_status():
        """Get current WebSocket session status"""
        return {
            "active_sessions": session_manager.get_session_count(),
            "push_service_running": push_service._running,
            "swarm_id": CURRENT_SWARM_ID,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_occ_app()
    print("=" * 80)
    print("LAUNCHING OCC COMMAND CENTER")
    print("=" * 80)
    print("HTTP:      http://localhost:8080/")
    print("Canvas:    http://localhost:8080/occ/canvas")
    print("WebSocket: ws://localhost:8080/ws/occ")
    print("API:       http://localhost:8080/occ/admin")
    print("=" * 80)
    uvicorn.run(app, host="0.0.0.0", port=8080)
