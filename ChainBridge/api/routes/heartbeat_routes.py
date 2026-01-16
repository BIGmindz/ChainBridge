"""
Heartbeat API Routes - SSE Stream & REST Endpoints
==================================================

PAC Reference: PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM
Classification: LAW_TIER
Author: SONNY (GID-02) - API Streaming
Orchestrator: BENSON (GID-00)

Exposes heartbeat stream via Server-Sent Events (SSE) for OCC UI consumption.
"""

import json
from datetime import datetime, timezone
from typing import Generator, Optional

from flask import Blueprint, Response, request, jsonify, stream_with_context

# Import heartbeat system
import sys
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from ChainBridge.core.orchestration.heartbeat import (
        HeartbeatEmitter,
        HeartbeatEvent,
        HeartbeatEventType,
        HeartbeatStream,
        get_emitter,
    )
except ImportError:
    # Fallback for standalone testing
    HeartbeatEmitter = None
    get_emitter = lambda: None


# Create Blueprint
heartbeat_bp = Blueprint("heartbeat", __name__, url_prefix="/api/v1/heartbeat")


# ==================== SSE Stream Endpoint ====================

@heartbeat_bp.route("/stream", methods=["GET"])
def heartbeat_stream():
    """
    Server-Sent Events stream for real-time heartbeat updates.
    
    Returns SSE stream with events:
        - PAC_START, PAC_COMPLETE, PAC_FAILED
        - LANE_TRANSITION, LANE_ACTIVE
        - TASK_START, TASK_COMPLETE, TASK_FAILED
        - AGENT_ACTIVE, AGENT_ATTESTED
        - WRAP_GENERATED, BER_GENERATED
        - HEARTBEAT_PING (keepalive every 30s)
    
    Usage:
        const eventSource = new EventSource('/api/v1/heartbeat/stream');
        eventSource.addEventListener('PAC_START', (e) => {
            const data = JSON.parse(e.data);
            console.log('PAC Started:', data.pac_id);
        });
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({"error": "Heartbeat system not initialized"}), 503
    
    def generate() -> Generator[str, None, None]:
        """Generate SSE events from heartbeat stream."""
        try:
            for event in emitter.stream.subscribe():
                yield event.to_sse()
        except GeneratorExit:
            pass
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ==================== History Endpoint ====================

@heartbeat_bp.route("/history", methods=["GET"])
def get_history():
    """
    Get recent heartbeat history.
    
    Query Parameters:
        - limit: Maximum events to return (default 100, max 500)
        - since: Sequence number to get events after (optional)
        - event_type: Filter by event type (optional)
    
    Response:
        {
            "events": [...],
            "count": 50,
            "latest_sequence": 123
        }
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({"error": "Heartbeat system not initialized"}), 503
    
    limit = min(int(request.args.get("limit", 100)), 500)
    since = request.args.get("since", type=int)
    event_type_filter = request.args.get("event_type")
    
    if since is not None:
        events = emitter.stream.get_history_since(since)
    else:
        events = emitter.stream.get_history(limit)
    
    # Filter by event type if specified
    if event_type_filter:
        events = [e for e in events if e.event_type.value == event_type_filter]
    
    # Serialize events
    events_data = [e.to_dict() for e in events[-limit:]]
    latest_seq = events[-1].sequence_number if events else 0
    
    return jsonify({
        "events": events_data,
        "count": len(events_data),
        "latest_sequence": latest_seq
    })


# ==================== Current State Endpoint ====================

@heartbeat_bp.route("/state", methods=["GET"])
def get_current_state():
    """
    Get current execution state snapshot.
    
    Response:
        {
            "session_id": "session_123",
            "current_pac": "PAC-P744-...",
            "current_lane": "OCC/GOVERNANCE_VISIBILITY",
            "active_agents": {...},
            "sequence": 42,
            "timestamp": "2026-01-13T18:30:00Z"
        }
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({"error": "Heartbeat system not initialized"}), 503
    
    return jsonify(emitter.get_current_state())


# ==================== Active PACs Endpoint ====================

@heartbeat_bp.route("/active-pacs", methods=["GET"])
def get_active_pacs():
    """
    Get list of currently executing PACs.
    
    Response:
        {
            "pacs": [
                {
                    "pac_id": "PAC-P744-...",
                    "title": "...",
                    "status": "EXECUTING",
                    "lane": "...",
                    "started_at": "..."
                }
            ]
        }
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({"error": "Heartbeat system not initialized"}), 503
    
    # Extract PAC info from recent events
    history = emitter.stream.get_history(500)
    
    active_pacs = {}
    for event in history:
        if event.pac_id:
            if event.event_type == HeartbeatEventType.PAC_START:
                active_pacs[event.pac_id] = {
                    "pac_id": event.pac_id,
                    "title": event.pac_title,
                    "status": "EXECUTING",
                    "lane": event.lane,
                    "started_at": event.timestamp
                }
            elif event.event_type in (HeartbeatEventType.PAC_COMPLETE, HeartbeatEventType.PAC_FAILED):
                if event.pac_id in active_pacs:
                    active_pacs[event.pac_id]["status"] = event.pac_status
                    active_pacs[event.pac_id]["completed_at"] = event.timestamp
                    if event.ber_score:
                        active_pacs[event.pac_id]["ber_score"] = event.ber_score
    
    # Filter to only truly active PACs
    executing = [p for p in active_pacs.values() if p["status"] == "EXECUTING"]
    
    return jsonify({
        "pacs": executing,
        "count": len(executing)
    })


# ==================== Agent Status Endpoint ====================

@heartbeat_bp.route("/agents", methods=["GET"])
def get_agent_status():
    """
    Get status of all registered agents.
    
    Response:
        {
            "agents": {
                "GID-00": {"name": "BENSON", "role": "Orchestrator", "status": "ACTIVE"},
                ...
            }
        }
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({"error": "Heartbeat system not initialized"}), 503
    
    return jsonify({
        "agents": emitter.get_active_agents()
    })


# ==================== Health Check ====================

@heartbeat_bp.route("/health", methods=["GET"])
def heartbeat_health():
    """
    Health check for heartbeat system.
    
    Response:
        {
            "status": "healthy",
            "stream_active": true,
            "sequence": 42,
            "uptime_events": 100
        }
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({
            "status": "unavailable",
            "stream_active": False,
            "error": "Heartbeat system not initialized"
        }), 503
    
    return jsonify({
        "status": "healthy",
        "stream_active": True,
        "sequence": emitter._sequence,
        "uptime_events": len(emitter.stream.get_history()),
        "session_id": emitter.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ==================== Manual Event Injection (Admin Only) ====================

@heartbeat_bp.route("/emit", methods=["POST"])
def emit_manual_event():
    """
    Manually emit a heartbeat event (admin use only).
    
    Request Body:
        {
            "event_type": "VISIBILITY_CHECK",
            "pac_id": "PAC-P744-...",
            "details": {...}
        }
    
    Response:
        {"success": true, "sequence": 43}
    """
    emitter = get_emitter()
    if not emitter:
        return jsonify({"error": "Heartbeat system not initialized"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    event_type_str = data.get("event_type", "VISIBILITY_CHECK")
    try:
        event_type = HeartbeatEventType[event_type_str]
    except KeyError:
        return jsonify({"error": f"Invalid event_type: {event_type_str}"}), 400
    
    event = HeartbeatEvent(
        event_type=event_type,
        pac_id=data.get("pac_id"),
        pac_title=data.get("pac_title"),
        lane=data.get("lane"),
        task_id=data.get("task_id"),
        task_title=data.get("task_title"),
        agent_gid=data.get("agent_gid"),
        agent_name=data.get("agent_name"),
        details=data.get("details", {})
    )
    
    event.sequence_number = emitter._next_sequence()
    event.session_id = emitter.session_id
    emitter.stream.publish(event)
    
    return jsonify({
        "success": True,
        "sequence": event.sequence_number
    })


# ==================== Blueprint Registration Helper ====================

def register_heartbeat_routes(app):
    """Register heartbeat routes with Flask app."""
    app.register_blueprint(heartbeat_bp)
    return heartbeat_bp


# ==================== Standalone Test Server ====================

if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    register_heartbeat_routes(app)
    
    print("Heartbeat API Test Server")
    print("=" * 50)
    print("Endpoints:")
    print("  GET  /api/v1/heartbeat/stream   - SSE stream")
    print("  GET  /api/v1/heartbeat/history  - Event history")
    print("  GET  /api/v1/heartbeat/state    - Current state")
    print("  GET  /api/v1/heartbeat/agents   - Agent status")
    print("  GET  /api/v1/heartbeat/health   - Health check")
    print("  POST /api/v1/heartbeat/emit     - Manual emit")
    print()
    
    app.run(debug=True, port=5001, threaded=True)
