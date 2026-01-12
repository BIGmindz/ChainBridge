"""
Signature Middleware - Cryptographic Request Verification
==========================================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: Request Signature Verification

INVARIANTS:
  INV-AUTH-005: Request signatures MUST be cryptographically verified
  INV-SIG-001: Signature algorithm MUST be HMAC-SHA256 or better
  INV-SIG-002: Signature MUST cover timestamp to prevent replay
  INV-SIG-003: Timestamp skew tolerance MUST be configurable (default 5 min)

SIGNATURE FORMAT:
  X-Signature: <algorithm>=<base64-signature>
  X-Timestamp: <unix-timestamp-ms>
  X-Nonce: <random-nonce> (optional, for replay protection)

SIGNED PAYLOAD:
  <method>|<path>|<timestamp>|<body-hash>|<nonce>

EXAMPLE:
  POST /v1/transaction at timestamp 1703000000000 with body {"amount": 100}
  Signed payload: POST|/v1/transaction|1703000000000|<sha256-of-body>|<nonce>
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
logger = logging.getLogger("chainbridge.signature")

# Default configuration
DEFAULT_TIMESTAMP_TOLERANCE = 300  # 5 minutes
DEFAULT_NONCE_TTL = 600  # 10 minutes


@dataclass
class SignatureConfig:
    """Signature verification configuration."""
    # Secret for HMAC
    secret_key: str = field(default_factory=lambda: os.environ.get("SIGNATURE_SECRET_KEY", ""))
    
    # Algorithm (hmac-sha256 or hmac-sha512)
    algorithm: str = "hmac-sha256"
    
    # Headers
    signature_header: str = "X-Signature"
    timestamp_header: str = "X-Timestamp"
    nonce_header: str = "X-Nonce"
    
    # Tolerance
    timestamp_tolerance_seconds: int = DEFAULT_TIMESTAMP_TOLERANCE
    
    # Nonce replay protection
    enable_nonce_check: bool = True
    nonce_ttl_seconds: int = DEFAULT_NONCE_TTL
    
    # Redis for nonce storage
    redis_url: str = "redis://localhost:6379/0"
    
    # Skip verification for certain content types
    skip_body_hash_content_types: Set[str] = field(default_factory=lambda: {
        "multipart/form-data",
    })
    
    # Endpoints that require signature
    required_endpoints: Set[str] = field(default_factory=lambda: {
        "/v1/transaction",
        "/v1/governance",
    })
    
    # Force signature for all endpoints
    require_all: bool = False


@dataclass
class SignatureResult:
    """Result of signature verification."""
    valid: bool
    error: Optional[str] = None
    algorithm: Optional[str] = None
    timestamp: Optional[int] = None
    nonce: Optional[str] = None


class NonceStore:
    """
    Nonce storage for replay protection.
    
    Uses Redis for distributed deployment.
    Falls back to in-memory with TTL for single instance.
    """
    
    def __init__(self, redis_url: str, ttl: int):
        self.ttl = ttl
        self._redis = None
        self._memory_store: Dict[str, float] = {}
        self._connect_redis(redis_url)
    
    def _connect_redis(self, redis_url: str) -> None:
        """Attempt Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            logger.debug("Nonce store connected to Redis")
        except ImportError:
            self._redis = None
        except Exception as e:
            logger.debug(f"Redis connection failed for nonce store: {e}")
            self._redis = None
    
    def check_and_store(self, nonce: str) -> bool:
        """
        Check if nonce has been used, store if not.
        
        Returns True if nonce is valid (not seen before).
        Returns False if nonce is replayed.
        """
        if self._redis:
            try:
                key = f"chainbridge:nonce:{nonce}"
                # SET with NX (only if not exists) and EX (expiry)
                result = self._redis.set(key, "1", nx=True, ex=self.ttl)
                return result is not None
            except Exception as e:
                logger.error(f"Redis nonce check failed: {e}")
        
        # Memory fallback
        now = time.time()
        
        # Cleanup expired nonces
        expired = [n for n, ts in self._memory_store.items() if now - ts > self.ttl]
        for n in expired:
            del self._memory_store[n]
        
        # Check and store
        if nonce in self._memory_store:
            return False
        
        self._memory_store[nonce] = now
        return True


class SignatureVerifier:
    """
    Cryptographic signature verifier.
    
    Supports HMAC-SHA256 and HMAC-SHA512.
    Enforces timestamp tolerance and nonce checking.
    """
    
    def __init__(self, config: SignatureConfig):
        self.config = config
        self._secret = config.secret_key.encode() if config.secret_key else b""
        self.nonce_store = NonceStore(config.redis_url, config.nonce_ttl_seconds)
    
    def _get_hash_func(self, algorithm: str):
        """Get hash function for algorithm."""
        if algorithm in ("hmac-sha256", "sha256"):
            return hashlib.sha256
        elif algorithm in ("hmac-sha512", "sha512"):
            return hashlib.sha512
        else:
            return None
    
    def compute_signature(
        self,
        method: str,
        path: str,
        timestamp: int,
        body_hash: str,
        nonce: str = "",
    ) -> str:
        """Compute expected signature for request."""
        # Build signed payload
        payload = f"{method}|{path}|{timestamp}|{body_hash}|{nonce}"
        
        hash_func = self._get_hash_func(self.config.algorithm)
        if not hash_func:
            raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")
        
        signature = hmac.new(
            self._secret,
            payload.encode(),
            hash_func,
        ).digest()
        
        return base64.b64encode(signature).decode()
    
    def verify(
        self,
        method: str,
        path: str,
        signature_header: str,
        timestamp: int,
        body: bytes,
        nonce: Optional[str] = None,
    ) -> SignatureResult:
        """
        Verify request signature.
        
        Returns SignatureResult with validation status.
        """
        try:
            # Parse signature header
            if "=" not in signature_header:
                return SignatureResult(valid=False, error="Invalid signature format")
            
            algorithm, provided_sig_b64 = signature_header.split("=", 1)
            
            # Validate algorithm
            if algorithm != self.config.algorithm.replace("hmac-", ""):
                return SignatureResult(valid=False, error="Unsupported algorithm")
            
            # Validate timestamp
            now_ms = int(time.time() * 1000)
            timestamp_diff = abs(now_ms - timestamp)
            tolerance_ms = self.config.timestamp_tolerance_seconds * 1000
            
            if timestamp_diff > tolerance_ms:
                return SignatureResult(
                    valid=False,
                    error=f"Timestamp outside tolerance: {timestamp_diff}ms > {tolerance_ms}ms",
                )
            
            # Validate nonce (if enabled and provided)
            if self.config.enable_nonce_check and nonce:
                if not self.nonce_store.check_and_store(nonce):
                    return SignatureResult(valid=False, error="Nonce already used (replay detected)")
            
            # Compute body hash
            body_hash = hashlib.sha256(body).hexdigest() if body else ""
            
            # Compute expected signature
            expected_sig = self.compute_signature(
                method=method,
                path=path,
                timestamp=timestamp,
                body_hash=body_hash,
                nonce=nonce or "",
            )
            
            # Compare signatures (constant-time)
            try:
                provided_sig = base64.b64decode(provided_sig_b64)
                expected_sig_bytes = base64.b64decode(expected_sig)
            except Exception:
                return SignatureResult(valid=False, error="Invalid signature encoding")
            
            if not hmac.compare_digest(provided_sig, expected_sig_bytes):
                return SignatureResult(valid=False, error="Signature mismatch")
            
            return SignatureResult(
                valid=True,
                algorithm=algorithm,
                timestamp=timestamp,
                nonce=nonce,
            )
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return SignatureResult(valid=False, error="Verification failed")


class SignatureMiddleware(BaseHTTPMiddleware):
    """
    Signature verification middleware.
    
    Enforces INV-AUTH-005: Request signatures MUST be cryptographically verified.
    
    Verifies:
      1. Signature matches expected value
      2. Timestamp is within tolerance
      3. Nonce has not been used (replay protection)
    """
    
    def __init__(
        self,
        app,
        exempt_paths: FrozenSet[str] = frozenset(),
        config: Optional[SignatureConfig] = None,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths
        self.config = config or SignatureConfig()
        self.verifier = SignatureVerifier(self.config)
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from signature verification."""
        if path in self.exempt_paths:
            return True
        path_normalized = path.rstrip("/")
        if path_normalized in self.exempt_paths:
            return True
        for exempt in self.exempt_paths:
            if path.startswith(exempt + "/"):
                return True
        return False
    
    def _requires_signature(self, path: str) -> bool:
        """Check if path requires signature verification."""
        if self.config.require_all:
            return True
        
        path_normalized = path.rstrip("/")
        for required in self.config.required_endpoints:
            if path_normalized == required or path_normalized.startswith(required + "/"):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Verify signature for incoming request."""
        path = request.url.path
        
        # Check exemption
        if self._is_exempt(path):
            return await call_next(request)
        
        # Check if signature required
        if not self._requires_signature(path):
            return await call_next(request)
        
        # Extract signature headers
        signature = request.headers.get(self.config.signature_header)
        timestamp_str = request.headers.get(self.config.timestamp_header)
        nonce = request.headers.get(self.config.nonce_header)
        
        # Validate required headers present
        if not signature:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Missing request signature",
                    "code": "MISSING_SIGNATURE",
                },
            )
        
        if not timestamp_str:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Missing request timestamp",
                    "code": "MISSING_TIMESTAMP",
                },
            )
        
        # Parse timestamp
        try:
            timestamp = int(timestamp_str)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid timestamp format",
                    "code": "INVALID_TIMESTAMP",
                },
            )
        
        # Read request body
        body = await request.body()
        
        # Verify signature
        result = self.verifier.verify(
            method=request.method,
            path=path,
            signature_header=signature,
            timestamp=timestamp,
            body=body,
            nonce=nonce,
        )
        
        if not result.valid:
            logger.warning(
                f"Signature verification failed: path={path} error={result.error} "
                f"ip={request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid request signature",
                    "code": "INVALID_SIGNATURE",
                },
            )
        
        # Attach verification result to request state
        request.state.signature = result
        
        return await call_next(request)
