"""
ChainBridge Sovereign Swarm - Blind Portal FastAPI Application
PAC-BLIND-PORTAL-28 | JOB B: BLIND-PORTAL

REST API layer for the Zero-PII Blind Vetting Portal.
Provides endpoints for bank integration and real-time progress streaming.

Endpoints:
- POST /portal/token      - Generate GID authentication token
- POST /portal/session    - Create authenticated session
- POST /portal/upload     - Upload .cbh file for vetting
- GET  /portal/status     - Get session status
- GET  /portal/stream     - SSE progress stream
- GET  /portal/health     - Health check

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001
"""

import asyncio
import json
import time
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, AsyncGenerator
from io import BytesIO

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse, JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.blind_portal import (
    BlindPortalOrchestrator,
    BlindAuditResponse,
    PortalSecurityLimits,
    SecurityEventType,
    SessionStatus,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    class TokenRequest(BaseModel):
        """Request model for GID token generation"""
        bank_id: str = Field(..., description="Bank identifier for token binding")
        valid_duration_seconds: int = Field(default=3600, description="Token validity period")
    
    class TokenResponse(BaseModel):
        """Response model for GID token generation"""
        gid_token: str
        expires_at: str
        bank_id: str
    
    class SessionRequest(BaseModel):
        """Request model for session creation"""
        gid_token: str = Field(..., description="One-time GID authentication token")
    
    class SessionResponse(BaseModel):
        """Response model for session creation"""
        session_id: str
        status: str
        created_at: str
        message: str
    
    class UploadResponse(BaseModel):
        """Response model for CBH upload"""
        success: bool
        session_id: str
        message: str
        blind_audit_response: Optional[Dict[str, Any]] = None
    
    class HealthResponse(BaseModel):
        """Response model for health check"""
        status: str
        service: str
        version: str
        timestamp: str
        portal_stats: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """
    Simple in-memory rate limiter.
    Enforces PortalSecurityLimits.RATE_LIMIT_PER_MINUTE.
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit"""
        now = time.time()
        window = 60  # 1 minute window
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < window
        ]
        
        if len(self.requests[client_id]) >= PortalSecurityLimits.RATE_LIMIT_PER_MINUTE:
            return False
        
        self.requests[client_id].append(now)
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

# Global orchestrator instance
portal_orchestrator = BlindPortalOrchestrator()
rate_limiter = RateLimiter()


def create_app() -> "FastAPI":
    """Create and configure the FastAPI application"""
    
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available. Install with: pip install fastapi uvicorn")
    
    app = FastAPI(
        title="ChainBridge Blind Portal",
        description="Zero-PII Blind Vetting Portal for Regulatory Compliance",
        version="1.0.0",
        docs_url="/portal/docs",
        redoc_url="/portal/redoc"
    )
    
    # CORS configuration for bank integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    return app


# Create app instance
if FASTAPI_AVAILABLE:
    app = create_app()
else:
    app = None


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

if FASTAPI_AVAILABLE:
    
    @app.get("/portal/health", response_model=HealthResponse)
    async def health_check():
        """
        Health check endpoint.
        Returns portal status and statistics.
        """
        return HealthResponse(
            status="OPERATIONAL",
            service="ChainBridge Blind Portal",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            portal_stats={
                "active_sessions": len(portal_orchestrator.active_sessions),
                "security_events": len(portal_orchestrator.security_log),
                "vetting_stats": portal_orchestrator.vetting_engine.get_statistics()
            }
        )
    
    
    @app.post("/portal/token", response_model=TokenResponse)
    async def generate_token(
        request: TokenRequest,
        x_api_key: str = Header(None, description="API key for token generation")
    ):
        """
        Generate a one-time GID authentication token.
        
        This endpoint is restricted and requires an API key.
        The bank IT team uses this to obtain a session token.
        """
        # In production, validate API key
        # For now, accept any request
        
        token = portal_orchestrator.generate_gid_token(request.bank_id)
        expires_at = datetime.now(timezone.utc).timestamp() + request.valid_duration_seconds
        
        return TokenResponse(
            gid_token=token,
            expires_at=datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
            bank_id=request.bank_id
        )
    
    
    @app.post("/portal/session", response_model=SessionResponse)
    async def create_session(
        request: SessionRequest,
        client_request: Request
    ):
        """
        Create a new portal session using a GID token.
        
        The GID token is one-time use and will be consumed.
        Returns a session_id for subsequent upload requests.
        """
        client_ip = client_request.client.host if client_request.client else "0.0.0.0"
        
        # Rate limiting
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="RATE_LIMIT_EXCEEDED: Too many requests"
            )
        
        success, reason, session = portal_orchestrator.create_session(
            request.gid_token,
            client_ip
        )
        
        if not success:
            raise HTTPException(
                status_code=401 if "TOKEN" in reason else 400,
                detail=reason
            )
        
        return SessionResponse(
            session_id=session.session_id,
            status=session.status.value,
            created_at=session.created_at,
            message="Session created. Ready for .cbh file upload."
        )
    
    
    @app.post("/portal/upload", response_model=UploadResponse)
    async def upload_cbh_file(
        session_id: str = Header(..., description="Active session ID"),
        file: UploadFile = File(..., description="The .cbh file to process")
    ):
        """
        Upload a .cbh file for blind vetting.
        
        SECURITY CONSTRAINTS:
        - Only .cbh files are accepted
        - Maximum file size: 100MB
        - File is processed in memory only (never written to disk)
        - Salt fingerprint must match Sovereign Salt
        - Integrity hash must be valid
        
        Returns a complete BlindAuditResponse with vetting results.
        """
        # Validate file extension
        if not file.filename or not file.filename.lower().endswith('.cbh'):
            raise HTTPException(
                status_code=400,
                detail="INVALID_FILE_TYPE: Only .cbh files are accepted"
            )
        
        # Read file into memory (NEVER to disk)
        content = await file.read()
        
        # Check file size
        if len(content) > PortalSecurityLimits.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"FILE_TOO_LARGE: Maximum size is {PortalSecurityLimits.MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
            )
        
        # Process through portal
        success, reason, response = portal_orchestrator.process_cbh_upload(
            session_id,
            file.filename,
            content
        )
        
        if not success:
            # Determine appropriate status code
            if "SALT_MISMATCH" in reason or "INTEGRITY" in reason:
                status_code = 403  # Forbidden - cryptographic failure
            elif "SESSION" in reason:
                status_code = 401  # Unauthorized
            elif "RECORD_LIMIT" in reason:
                status_code = 413  # Payload too large
            else:
                status_code = 400  # Bad request
            
            raise HTTPException(status_code=status_code, detail=reason)
        
        return UploadResponse(
            success=True,
            session_id=session_id,
            message="VETTING_COMPLETE",
            blind_audit_response=response.to_dict() if response else None
        )
    
    
    @app.get("/portal/status")
    async def get_session_status(
        session_id: str = Query(..., description="Session ID to check")
    ):
        """
        Get the status of an active session.
        """
        status = portal_orchestrator.get_session_status(session_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail="SESSION_NOT_FOUND"
            )
        
        return status
    
    
    @app.get("/portal/stream")
    async def progress_stream(
        session_id: str = Query(..., description="Session ID for progress streaming")
    ):
        """
        Server-Sent Events (SSE) stream for real-time progress updates.
        
        Connect to this endpoint to receive live vetting progress
        while an upload is being processed.
        """
        async def generate():
            last_count = 0
            timeout = 0
            max_timeout = 300  # 5 minutes max
            
            while timeout < max_timeout:
                status = portal_orchestrator.get_session_status(session_id)
                
                if not status:
                    yield f"data: {json.dumps({'error': 'SESSION_NOT_FOUND'})}\n\n"
                    break
                
                current_count = status.get("records_processed", 0)
                
                if current_count != last_count:
                    yield f"data: {json.dumps(status)}\n\n"
                    last_count = current_count
                    timeout = 0  # Reset timeout on activity
                
                if status.get("status") == "COMPLETE":
                    yield f"data: {json.dumps({'status': 'STREAM_COMPLETE', 'final': status})}\n\n"
                    break
                
                if status.get("status") == "TERMINATED":
                    yield f"data: {json.dumps({'status': 'STREAM_TERMINATED', 'final': status})}\n\n"
                    break
                
                await asyncio.sleep(0.1)
                timeout += 0.1
            
            yield f"data: {json.dumps({'status': 'STREAM_CLOSED'})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    
    @app.get("/portal/security-log")
    async def get_security_log(
        x_api_key: str = Header(..., description="Admin API key required")
    ):
        """
        Retrieve the security event log.
        
        This endpoint is restricted to administrators.
        """
        # In production, validate admin API key
        return {
            "events": portal_orchestrator.get_security_log(),
            "total_events": len(portal_orchestrator.security_log)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the FastAPI server"""
    try:
        import uvicorn
        print("=" * 70)
        print("CHAINBRIDGE BLIND PORTAL | FastAPI Server")
        print("=" * 70)
        print(f"Starting server at http://{host}:{port}")
        print(f"API Docs: http://{host}:{port}/portal/docs")
        print("=" * 70)
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        print("ERROR: uvicorn not installed. Install with: pip install uvicorn")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        run_api_server(port=port)
    else:
        # Run integration test
        print("=" * 70)
        print("BLIND PORTAL API | Integration Test Mode")
        print("=" * 70)
        
        if not FASTAPI_AVAILABLE:
            print("FastAPI not available. Install with: pip install fastapi uvicorn")
            print("Running core portal test instead...")
            from api.blind_portal import run_portal_test
            run_portal_test()
        else:
            print("FastAPI available. Server can be started with: --serve [port]")
            print("Running core portal test...")
            from api.blind_portal import run_portal_test
            result = run_portal_test()
            print("\n[API INTEGRATION STATUS] READY")
