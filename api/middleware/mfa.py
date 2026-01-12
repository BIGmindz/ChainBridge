"""
Multi-Factor Authentication Middleware
======================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: MFA Challenge and Verification
Agent: CODY (GID-01)

INVARIANTS:
  INV-AUTH-014: High-risk auth MUST trigger MFA challenge (MAGGIE enforced)

SUPPORTED METHODS:
  - TOTP (Time-based One-Time Password)
  - SMS OTP
  - Push Notifications
  - Hardware Tokens (via hardware_token.py)
  - Biometric (via biometric.py)

RISK-BASED TRIGGERS:
  - ChainIQ risk score > 0.7
  - New device detection
  - Unusual location
  - High-value transaction
  - Privilege escalation
"""

import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("chainbridge.auth.mfa")


class MFAMethod(Enum):
    """Supported MFA methods."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    HARDWARE = "hardware"
    BIOMETRIC = "biometric"


class MFATrigger(Enum):
    """Events that trigger MFA challenge."""
    HIGH_RISK_SCORE = "high_risk_score"
    NEW_DEVICE = "new_device"
    NEW_LOCATION = "new_location"
    HIGH_VALUE_TRANSACTION = "high_value_transaction"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SENSITIVE_OPERATION = "sensitive_operation"
    FAILED_ATTEMPTS = "failed_attempts"


@dataclass
class MFAConfig:
    """MFA configuration."""
    # TOTP settings
    totp_digits: int = 6
    totp_interval: int = 30
    totp_algorithm: str = "sha1"
    totp_tolerance: int = 1  # Accept codes ±1 interval
    
    # SMS/Email settings
    otp_length: int = 6
    otp_expiry_seconds: int = 300  # 5 minutes
    max_otp_attempts: int = 3
    
    # Push notification settings
    push_timeout_seconds: int = 60
    push_provider: str = "firebase"
    
    # Risk thresholds
    risk_threshold: float = 0.7
    high_value_threshold: float = 10000.0
    
    # Rate limiting
    max_mfa_challenges_per_hour: int = 10
    cooldown_seconds: int = 60


@dataclass
class MFAChallenge:
    """Represents an active MFA challenge."""
    challenge_id: str
    user_id: str
    method: MFAMethod
    trigger: MFATrigger
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MFAResult:
    """Result of MFA verification."""
    verified: bool
    method: Optional[MFAMethod] = None
    challenge_id: Optional[str] = None
    error: Optional[str] = None
    remaining_attempts: int = 0


class TOTPGenerator:
    """
    Time-based One-Time Password generator (RFC 6238).
    
    Compatible with Google Authenticator, Authy, etc.
    """
    
    def __init__(self, config: MFAConfig):
        self.config = config
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret (base32 encoded)."""
        secret_bytes = secrets.token_bytes(20)
        return base64.b32encode(secret_bytes).decode('ascii')
    
    def generate_code(self, secret: str, timestamp: Optional[int] = None) -> str:
        """Generate TOTP code for given secret and timestamp."""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Decode secret
        secret_bytes = base64.b32decode(secret.upper())
        
        # Calculate time counter
        counter = timestamp // self.config.totp_interval
        
        # Pack counter as big-endian 8-byte integer
        counter_bytes = struct.pack(">Q", counter)
        
        # Generate HMAC
        if self.config.totp_algorithm == "sha1":
            hmac_digest = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
        elif self.config.totp_algorithm == "sha256":
            hmac_digest = hmac.new(secret_bytes, counter_bytes, hashlib.sha256).digest()
        else:
            raise ValueError(f"Unsupported algorithm: {self.config.totp_algorithm}")
        
        # Dynamic truncation
        offset = hmac_digest[-1] & 0x0F
        code_int = struct.unpack(">I", hmac_digest[offset:offset+4])[0]
        code_int &= 0x7FFFFFFF  # Clear sign bit
        code_int %= 10 ** self.config.totp_digits
        
        return str(code_int).zfill(self.config.totp_digits)
    
    def verify_code(self, secret: str, code: str) -> bool:
        """
        Verify TOTP code with tolerance window.
        
        Accepts codes from (current - tolerance) to (current + tolerance) intervals.
        """
        current_time = int(time.time())
        
        for delta in range(-self.config.totp_tolerance, self.config.totp_tolerance + 1):
            check_time = current_time + (delta * self.config.totp_interval)
            expected_code = self.generate_code(secret, check_time)
            
            if hmac.compare_digest(code, expected_code):
                return True
        
        return False
    
    def generate_provisioning_uri(
        self,
        secret: str,
        user_email: str,
        issuer: str = "ChainBridge"
    ) -> str:
        """Generate otpauth:// URI for authenticator app setup."""
        import urllib.parse
        
        params = {
            "secret": secret,
            "issuer": issuer,
            "algorithm": self.config.totp_algorithm.upper(),
            "digits": str(self.config.totp_digits),
            "period": str(self.config.totp_interval),
        }
        
        label = urllib.parse.quote(f"{issuer}:{user_email}")
        query = urllib.parse.urlencode(params)
        
        return f"otpauth://totp/{label}?{query}"


class OTPManager:
    """
    One-Time Password manager for SMS/Email verification.
    
    Generates, stores, and verifies OTPs with rate limiting.
    """
    
    def __init__(self, config: MFAConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        self._otp_store: Dict[str, Dict[str, Any]] = {}  # Fallback in-memory store
    
    def generate_otp(self, user_id: str, method: MFAMethod) -> str:
        """Generate a new OTP for the user."""
        otp = "".join(
            str(secrets.randbelow(10))
            for _ in range(self.config.otp_length)
        )
        
        challenge_id = secrets.token_urlsafe(16)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.config.otp_expiry_seconds
        )
        
        otp_data = {
            "otp_hash": hashlib.sha256(otp.encode()).hexdigest(),
            "user_id": user_id,
            "method": method.value,
            "challenge_id": challenge_id,
            "expires_at": expires_at.isoformat(),
            "attempts": 0,
        }
        
        key = f"mfa:otp:{user_id}:{challenge_id}"
        
        if self.redis:
            self.redis.setex(
                key,
                self.config.otp_expiry_seconds,
                json.dumps(otp_data)
            )
        else:
            self._otp_store[key] = otp_data
        
        logger.info(f"Generated OTP for user {user_id} via {method.value}")
        return otp
    
    def verify_otp(self, user_id: str, challenge_id: str, otp: str) -> MFAResult:
        """Verify an OTP."""
        key = f"mfa:otp:{user_id}:{challenge_id}"
        
        if self.redis:
            data = self.redis.get(key)
            if data:
                otp_data = json.loads(data)
            else:
                return MFAResult(verified=False, error="Invalid or expired OTP")
        else:
            otp_data = self._otp_store.get(key)
            if not otp_data:
                return MFAResult(verified=False, error="Invalid or expired OTP")
        
        # Check expiry
        expires_at = datetime.fromisoformat(otp_data["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return MFAResult(verified=False, error="OTP expired")
        
        # Check attempts
        if otp_data["attempts"] >= self.config.max_otp_attempts:
            return MFAResult(verified=False, error="Max attempts exceeded")
        
        # Verify OTP
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        if hmac.compare_digest(otp_hash, otp_data["otp_hash"]):
            # Delete OTP after successful verification
            if self.redis:
                self.redis.delete(key)
            else:
                del self._otp_store[key]
            
            return MFAResult(
                verified=True,
                method=MFAMethod(otp_data["method"]),
                challenge_id=challenge_id
            )
        
        # Increment attempts
        otp_data["attempts"] += 1
        if self.redis:
            remaining_ttl = self.redis.ttl(key)
            self.redis.setex(key, remaining_ttl, json.dumps(otp_data))
        else:
            self._otp_store[key] = otp_data
        
        remaining = self.config.max_otp_attempts - otp_data["attempts"]
        return MFAResult(
            verified=False,
            error="Invalid OTP",
            remaining_attempts=remaining
        )


class MFAChallengeManager:
    """
    Manages MFA challenge lifecycle.
    
    Creates, tracks, and verifies MFA challenges with risk-based triggers.
    """
    
    def __init__(self, config: MFAConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        self.totp = TOTPGenerator(config)
        self.otp_manager = OTPManager(config, redis_client)
        self._challenges: Dict[str, MFAChallenge] = {}
    
    def should_challenge(
        self,
        user_id: str,
        risk_score: float = 0.0,
        transaction_value: float = 0.0,
        is_new_device: bool = False,
        is_new_location: bool = False,
        operation: str = ""
    ) -> Optional[MFATrigger]:
        """
        Determine if MFA challenge should be triggered.
        
        Returns the trigger reason, or None if no challenge needed.
        """
        if risk_score >= self.config.risk_threshold:
            return MFATrigger.HIGH_RISK_SCORE
        
        if is_new_device:
            return MFATrigger.NEW_DEVICE
        
        if is_new_location:
            return MFATrigger.NEW_LOCATION
        
        if transaction_value >= self.config.high_value_threshold:
            return MFATrigger.HIGH_VALUE_TRANSACTION
        
        sensitive_ops = {"delete", "transfer", "admin", "config", "key_rotation"}
        if operation.lower() in sensitive_ops:
            return MFATrigger.SENSITIVE_OPERATION
        
        return None
    
    def create_challenge(
        self,
        user_id: str,
        method: MFAMethod,
        trigger: MFATrigger,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MFAChallenge:
        """Create a new MFA challenge."""
        challenge_id = secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc)
        
        if method == MFAMethod.PUSH:
            expiry_seconds = self.config.push_timeout_seconds
        else:
            expiry_seconds = self.config.otp_expiry_seconds
        
        challenge = MFAChallenge(
            challenge_id=challenge_id,
            user_id=user_id,
            method=method,
            trigger=trigger,
            created_at=now,
            expires_at=now + timedelta(seconds=expiry_seconds),
            metadata=metadata or {}
        )
        
        key = f"mfa:challenge:{challenge_id}"
        challenge_data = {
            "challenge_id": challenge_id,
            "user_id": user_id,
            "method": method.value,
            "trigger": trigger.value,
            "created_at": challenge.created_at.isoformat(),
            "expires_at": challenge.expires_at.isoformat(),
            "attempts": 0,
            "verified": False,
            "metadata": challenge.metadata,
        }
        
        if self.redis:
            self.redis.setex(key, expiry_seconds, json.dumps(challenge_data))
        else:
            self._challenges[challenge_id] = challenge
        
        logger.info(
            f"MFA challenge created: {challenge_id} for user {user_id} "
            f"via {method.value} (trigger: {trigger.value})"
        )
        
        return challenge
    
    def verify_challenge(
        self,
        challenge_id: str,
        code: str,
        user_secret: Optional[str] = None
    ) -> MFAResult:
        """
        Verify an MFA challenge.
        
        Args:
            challenge_id: The challenge to verify
            code: User-provided verification code
            user_secret: TOTP secret for TOTP verification
        """
        key = f"mfa:challenge:{challenge_id}"
        
        if self.redis:
            data = self.redis.get(key)
            if not data:
                return MFAResult(verified=False, error="Invalid or expired challenge")
            challenge_data = json.loads(data)
        else:
            challenge = self._challenges.get(challenge_id)
            if not challenge:
                return MFAResult(verified=False, error="Invalid or expired challenge")
            challenge_data = {
                "method": challenge.method.value,
                "user_id": challenge.user_id,
            }
        
        method = MFAMethod(challenge_data["method"])
        
        if method == MFAMethod.TOTP:
            if not user_secret:
                return MFAResult(verified=False, error="TOTP secret required")
            
            verified = self.totp.verify_code(user_secret, code)
            if verified:
                self._mark_verified(challenge_id)
                return MFAResult(
                    verified=True,
                    method=method,
                    challenge_id=challenge_id
                )
            return MFAResult(verified=False, error="Invalid TOTP code")
        
        elif method in (MFAMethod.SMS, MFAMethod.EMAIL):
            return self.otp_manager.verify_otp(
                challenge_data["user_id"],
                challenge_id,
                code
            )
        
        return MFAResult(verified=False, error=f"Unsupported method: {method}")
    
    def _mark_verified(self, challenge_id: str):
        """Mark challenge as verified."""
        key = f"mfa:challenge:{challenge_id}"
        if self.redis:
            self.redis.delete(key)
        elif challenge_id in self._challenges:
            del self._challenges[challenge_id]


class MFAMiddleware(BaseHTTPMiddleware):
    """
    Multi-Factor Authentication middleware.
    
    Integrates with risk scoring to trigger MFA challenges.
    """
    
    def __init__(
        self,
        app,
        config: Optional[MFAConfig] = None,
        redis_client=None,
        exempt_paths: frozenset = frozenset()
    ):
        super().__init__(app)
        self.config = config or MFAConfig()
        self.challenge_manager = MFAChallengeManager(self.config, redis_client)
        self.exempt_paths = exempt_paths
    
    async def dispatch(self, request: Request, call_next):
        """Process request and handle MFA if required."""
        path = request.url.path
        
        # Skip exempt paths
        if path in self.exempt_paths:
            return await call_next(request)
        
        # Check for pending MFA challenge
        mfa_challenge = request.headers.get("X-MFA-Challenge-ID")
        mfa_code = request.headers.get("X-MFA-Code")
        
        if mfa_challenge and mfa_code:
            # Verify MFA
            user_secret = getattr(request.state, "totp_secret", None)
            result = self.challenge_manager.verify_challenge(
                mfa_challenge,
                mfa_code,
                user_secret
            )
            
            if not result.verified:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "MFA verification failed",
                        "message": result.error,
                        "remaining_attempts": result.remaining_attempts,
                    }
                )
            
            # MFA verified - proceed
            request.state.mfa_verified = True
            request.state.mfa_method = result.method
        
        # Check if MFA is required (integrated with risk scoring)
        risk_score = getattr(request.state, "risk_score", 0.0)
        transaction_value = 0.0  # Could be extracted from request body
        is_new_device = getattr(request.state, "is_new_device", False)
        is_new_location = getattr(request.state, "is_new_location", False)
        
        trigger = self.challenge_manager.should_challenge(
            user_id=getattr(request.state, "user_id", "unknown"),
            risk_score=risk_score,
            transaction_value=transaction_value,
            is_new_device=is_new_device,
            is_new_location=is_new_location,
            operation=request.method + " " + path
        )
        
        if trigger and not getattr(request.state, "mfa_verified", False):
            # Create challenge
            user_id = getattr(request.state, "user_id", "unknown")
            preferred_method = MFAMethod.TOTP  # Could be user preference
            
            challenge = self.challenge_manager.create_challenge(
                user_id=user_id,
                method=preferred_method,
                trigger=trigger,
                metadata={"path": path, "method": request.method}
            )
            
            return JSONResponse(
                status_code=401,
                content={
                    "error": "MFA required",
                    "code": "MFA_CHALLENGE_REQUIRED",
                    "challenge_id": challenge.challenge_id,
                    "method": challenge.method.value,
                    "trigger": challenge.trigger.value,
                    "expires_at": challenge.expires_at.isoformat(),
                }
            )
        
        return await call_next(request)


# Convenience imports
import json
