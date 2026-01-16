"""
Audit Query API - Heartbeat Event Audit Endpoints
==================================================

PAC Reference: PAC-P745-OCC-HEARTBEAT-PERSISTENCE-AUDIT
Classification: LAW_TIER
Author: SONNY (GID-02) - API
Orchestrator: BENSON (GID-00)

Exposes audit query endpoints for heartbeat event verification.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from flask import Blueprint, request, jsonify

# Import stores
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from ChainBridge.core.orchestration.heartbeat.event_store import (
        get_event_store,
        HeartbeatEventStore,
        RetentionPolicy
    )
    from ChainBridge.core.orchestration.heartbeat.hash_chain import (
        get_chain_manager,
        HashChainManager
    )
except ImportError:
    get_event_store = lambda: None
    get_chain_manager = lambda: None


# Create Blueprint
audit_bp = Blueprint("audit", __name__, url_prefix="/api/v1/audit")


# ==================== PAC Audit Endpoints ====================

@audit_bp.route("/pac/<pac_id>", methods=["GET"])
def get_pac_audit(pac_id: str):
    """
    Get complete audit trail for a PAC.
    
    Response:
        {
            "pac_id": "PAC-P745-...",
            "event_count": 25,
            "chain_valid": true,
            "events": [...],
            "chain_summary": {...}
        }
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    limit = request.args.get("limit", 1000, type=int)
    events = store.query_by_pac(pac_id, limit=limit)
    chain_summary = store.get_chain_summary(pac_id)
    verification = store.verify_chain(pac_id)
    
    return jsonify({
        "pac_id": pac_id,
        "event_count": len(events),
        "chain_valid": verification["verified"],
        "chain_summary": chain_summary,
        "verification": verification,
        "events": [e.to_dict() for e in events]
    })


@audit_bp.route("/pac/<pac_id>/verify", methods=["GET"])
def verify_pac_chain(pac_id: str):
    """
    Verify hash chain integrity for a PAC.
    
    Response:
        {
            "pac_id": "PAC-P745-...",
            "status": "VALID",
            "verified": true,
            "event_count": 25,
            "chain_head": "abc123...",
            "broken_links": []
        }
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    result = store.verify_chain(pac_id)
    return jsonify(result)


@audit_bp.route("/pac/<pac_id>/summary", methods=["GET"])
def get_pac_summary(pac_id: str):
    """
    Get summary of a PAC's event chain.
    
    Response:
        {
            "pac_id": "PAC-P745-...",
            "exists": true,
            "event_count": 25,
            "chain_head": "abc123...",
            "first_event": "2026-01-13T...",
            "last_event": "2026-01-13T...",
            "event_types": {"PAC_START": 1, "TASK_START": 4, ...}
        }
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    return jsonify(store.get_chain_summary(pac_id))


# ==================== Event Query Endpoints ====================

@audit_bp.route("/events/recent", methods=["GET"])
def get_recent_events():
    """
    Get most recent events across all PACs.
    
    Query Parameters:
        - limit: Max events (default 100)
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    limit = request.args.get("limit", 100, type=int)
    events = store.query_recent(limit)
    
    return jsonify({
        "count": len(events),
        "events": [e.to_dict() for e in events]
    })


@audit_bp.route("/events/by-type/<event_type>", methods=["GET"])
def get_events_by_type(event_type: str):
    """
    Get events by type.
    
    Query Parameters:
        - limit: Max events (default 100)
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    limit = request.args.get("limit", 100, type=int)
    events = store.query_by_type(event_type, limit)
    
    return jsonify({
        "event_type": event_type,
        "count": len(events),
        "events": [e.to_dict() for e in events]
    })


@audit_bp.route("/events/by-hash/<content_hash>", methods=["GET"])
def get_event_by_hash(content_hash: str):
    """
    Get event by its content hash.
    
    Returns single event or 404.
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    event = store.query_by_hash(content_hash)
    if not event:
        return jsonify({"error": "Event not found", "hash": content_hash}), 404
    
    return jsonify(event.to_dict())


@audit_bp.route("/events/by-session/<session_id>", methods=["GET"])
def get_events_by_session(session_id: str):
    """
    Get all events for a session.
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    limit = request.args.get("limit", 1000, type=int)
    events = store.query_by_session(session_id, limit)
    
    return jsonify({
        "session_id": session_id,
        "count": len(events),
        "events": [e.to_dict() for e in events]
    })


# ==================== Chain Proof Endpoints ====================

@audit_bp.route("/chain/<pac_id>/proof", methods=["GET"])
def get_chain_proof(pac_id: str):
    """
    Get cryptographic proof of a PAC's event chain.
    
    Useful for external audit verification.
    """
    manager = get_chain_manager()
    if not manager:
        return jsonify({"error": "Chain manager not initialized"}), 503
    
    proof = manager.get_chain_proof(pac_id)
    return jsonify(proof)


@audit_bp.route("/chain/<pac_id>/export", methods=["GET"])
def export_chain(pac_id: str):
    """
    Export full chain for external verification.
    
    Returns complete block data.
    """
    manager = get_chain_manager()
    if not manager:
        return jsonify({"error": "Chain manager not initialized"}), 503
    
    blocks = manager.export_chain(pac_id)
    return jsonify({
        "pac_id": pac_id,
        "block_count": len(blocks),
        "blocks": blocks
    })


# ==================== Statistics Endpoints ====================

@audit_bp.route("/stats", methods=["GET"])
def get_audit_stats():
    """
    Get event store statistics.
    
    Response:
        {
            "total_events": 1000,
            "unique_pacs": 50,
            "unique_sessions": 25,
            "event_type_distribution": {...}
        }
    """
    store = get_event_store()
    if not store:
        return jsonify({"error": "Event store not initialized"}), 503
    
    return jsonify(store.get_stats())


@audit_bp.route("/health", methods=["GET"])
def audit_health():
    """
    Health check for audit system.
    """
    store = get_event_store()
    manager = get_chain_manager()
    
    return jsonify({
        "status": "healthy" if store and manager else "degraded",
        "event_store": "available" if store else "unavailable",
        "chain_manager": "available" if manager else "unavailable",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ==================== Blueprint Registration ====================

def register_audit_routes(app):
    """Register audit routes with Flask app."""
    app.register_blueprint(audit_bp)
    return audit_bp


# ==================== Standalone Test ====================

if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    register_audit_routes(app)
    
    print("Audit API Test Server")
    print("=" * 50)
    print("Endpoints:")
    print("  GET  /api/v1/audit/pac/<pac_id>          - Full audit trail")
    print("  GET  /api/v1/audit/pac/<pac_id>/verify   - Verify chain")
    print("  GET  /api/v1/audit/pac/<pac_id>/summary  - Chain summary")
    print("  GET  /api/v1/audit/events/recent         - Recent events")
    print("  GET  /api/v1/audit/events/by-type/<type> - Events by type")
    print("  GET  /api/v1/audit/events/by-hash/<hash> - Event by hash")
    print("  GET  /api/v1/audit/chain/<pac_id>/proof  - Chain proof")
    print("  GET  /api/v1/audit/stats                 - Statistics")
    print()
    
    app.run(debug=True, port=5002, threaded=True)
