#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# PAC-SWARM-P17-P18-P21-EXEC — ChainBridge Sovereign Relay v2.2.1
# RNP Clean Build (Replace, No Patch)
# Governance Tier: CONSTITUTIONAL_LAW
# Invariant: TRIPLE_GATE_SECURITY (Physical → Identity → Friction)
# ═══════════════════════════════════════════════════════════════════════════════
"""
ChainBridge Sovereign Relay v2.2.1

Consolidated bridge implementing the Triple Gate architecture:
- P16: Hardware Sovereignty (GPIO/Serial Kill Switch)
- P18: Identity Binding (Ed25519 Signature Verification)
- P21: Cognitive Friction (High-Stakes Acknowledgment)

"The code is clean. The gates are shut. Only the Sovereign may pass."
"""

import json
import logging
import os
import sys

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════
# P16: HARDWARE SOVEREIGNTY IMPORT
# ═══════════════════════════════════════════════════════════════════════════════
# This module must exist in the same directory (deployed via P16)
try:
    from sovereign_kill_daemon import kill_switch
except ImportError:
    print("CRITICAL: sovereign_kill_daemon missing. Hardware Sovereignty violated.")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

HOST = "0.0.0.0"
PORT = 8080

# P18: Identity Binding (Ed25519 Public Key)
ARCHITECT_PUB_KEY_HEX = os.getenv("ARCHITECT_PUB_KEY_HEX")

# Version
RELAY_VERSION = "2.2.1"

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [SOVEREIGN_BRIDGE] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("BridgeRelay")

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="ChainBridge Sovereign Relay", version=RELAY_VERSION)

# ═══════════════════════════════════════════════════════════════════════════════
# P17: STARTUP BINDING
# ═══════════════════════════════════════════════════════════════════════════════


@app.on_event("startup")
async def startup_sequence():
    """Sovereign Binding Sequence - Initialize all gates."""
    logger.info("🔒 INITIATING SOVEREIGN BINDING SEQUENCE...")

    # 1. Bind Hardware Shield (P16)
    logger.info("   [1/3] Binding Physical Kill Switch...")
    kill_switch.start()

    # 2. Verify Identity Anchor (P18)
    logger.info("   [2/3] Verifying Identity Keys...")
    if not ARCHITECT_PUB_KEY_HEX:
        logger.critical("❌ FATAL: ARCHITECT_PUB_KEY_HEX missing from env. FAILING CLOSED.")
        os._exit(1)  # Fail Closed

    # 3. Initialize Ledger
    logger.info("   [3/3] Locking Ledger File System...")
    os.makedirs("active_pacs", exist_ok=True)

    logger.info("✅ SOVEREIGN BRIDGE v2.2.1 ACTIVE.")


# ═══════════════════════════════════════════════════════════════════════════════
# P18: IDENTITY MIDDLEWARE (Gate 2)
# ═══════════════════════════════════════════════════════════════════════════════


@app.middleware("http")
async def sovereign_gate(request: Request, call_next):
    """
    Identity verification middleware.
    
    All requests (except /health) must include a valid Ed25519 signature
    in the X-Concordium-Signature header.
    """
    # Health check bypass (Read-Only status)
    if request.url.path == "/health":
        return await call_next(request)

    # GATE 2: IDENTITY (P18)
    sig_hex = request.headers.get("X-Concordium-Signature")
    if not sig_hex:
        logger.warning(f"⛔ REJECTED: Missing Signature from {request.client.host}")
        return Response(
            content='{"status": "REJECTED", "reason": "MISSING_SIG"}',
            status_code=401,
            media_type="application/json"
        )

    try:
        # Consume body for signature verification
        body_bytes = await request.body()

        # Verify Ed25519 signature
        verify_key = VerifyKey(bytes.fromhex(ARCHITECT_PUB_KEY_HEX))
        verify_key.verify(body_bytes, bytes.fromhex(sig_hex))

        # Re-inject body for the endpoint
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive

    except BadSignatureError:
        logger.critical(f"⛔ FORGED PACKET DETECTED from {request.client.host}")
        return Response(
            content='{"status": "DENIED", "reason": "INVALID_SIG"}',
            status_code=403,
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Gate Error: {e}")
        return Response(
            content='{"status": "ERROR", "reason": "GATE_FAILURE"}',
            status_code=500,
            media_type="application/json"
        )

    response = await call_next(request)
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class PACPayload(BaseModel):
    """PAC ingress payload."""
    pac_id: str
    classification: str
    content: str


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@app.post("/pac-ingress")
async def ingress(payload: PACPayload, x_cognitive_friction: str = Header(None)):
    """
    P21: COGNITIVE FRICTION GATE (Gate 3)
    
    High-stakes PACs require explicit friction acknowledgement.
    Classification tiers requiring friction:
    - CONSTITUTIONAL_LAW
    - HARDWARE_OVERRIDE
    - CORE_CONSOLIDATION
    """
    # GATE 3: COGNITIVE FRICTION (P21)
    high_stakes_tiers = ["CONSTITUTIONAL_LAW", "HARDWARE_OVERRIDE", "CORE_CONSOLIDATION"]

    if payload.classification in high_stakes_tiers:
        required_token = "I_AM_FULLY_AWARE_OF_THE_CONSEQUENCES"
        if x_cognitive_friction != required_token:
            logger.warning(f"⚠️ FRICTION CHECK FAILED for {payload.pac_id}")
            raise HTTPException(
                status_code=428,
                detail="Precondition Required: Cognitive Friction Header Missing"
            )

    # DECISION → OUTCOME
    safe_id = payload.pac_id.replace("/", "_").replace("\\", "_")
    file_path = f"active_pacs/{safe_id}.json"

    try:
        with open(file_path, "w") as f:
            json.dump(payload.dict(), f, indent=2)
        logger.info(f"💾 PAC {safe_id} ANCHORED to Disk.")
        return {"status": "ANCHORED", "id": safe_id}
    except Exception as e:
        logger.error(f"IO Error: {e}")
        raise HTTPException(status_code=500, detail="Bridge Storage Failure")


@app.get("/health")
async def health():
    """Health check endpoint - bypasses identity gate."""
    return {
        "status": "ONLINE",
        "version": f"v{RELAY_VERSION}",
        "sovereignty": "HARDWARE_BACKED"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print(f"🌉 CHAINBRIDGE SOVEREIGN RELAY v{RELAY_VERSION}")
    print("   Triple Gate Security (P16 + P18 + P21)")
    print("=" * 70)
    print("Gates:")
    print("   [1] PHYSICAL  - Hardware Kill Switch (GPIO/Serial)")
    print("   [2] IDENTITY  - Ed25519 Signature (X-Concordium-Signature)")
    print("   [3] FRICTION  - High-Stakes Acknowledgment (X-Cognitive-Friction)")
    print("=" * 70)
    print(f"🔑 Identity Key: {'SET' if ARCHITECT_PUB_KEY_HEX else 'NOT SET'}")
    print("=" * 70)
    print("The code is clean. The gates are shut. Only the Sovereign may pass.")
    print("=" * 70)
    print(f"🚀 Starting relay on http://{HOST}:{PORT}")
    print("=" * 70)

    uvicorn.run(app, host=HOST, port=PORT)
