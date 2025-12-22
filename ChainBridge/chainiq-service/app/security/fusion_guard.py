"""
Fusion Guard - Memory Safety & Security Module (SAM GID-06)
PAC-SAM-NEXT-021: Security Hardening – Fusion Layer Memory Safety Sweep

Provides comprehensive security controls for the ChainIQ Fusion layer:

SECURITY FEATURES:
1. Strict Parsing Logic - Validates all inputs against allowlists
2. Bounded List Returns - Prevents unbounded memory allocation
3. Timing-Safe Comparisons - Mitigates timing side-channel attacks
4. Rate Limiting - Prevents DoS and resource exhaustion
5. Secure Serialization - Blocks unsafe pickle operations
6. Input Sanitization - Prevents injection attacks

ALEX Governance Rule: "Fusion Memory Safety"
- All fusion endpoints must use FusionGuard validation
- Maximum list size: 10,000 items
- Maximum payload size: 1MB
- Rate limit: 100 requests/minute per client

Threat Coverage:
- Memory exhaustion attacks (unbounded lists)
- Timing side-channel attacks
- Serialization/deserialization attacks
- DoS via expensive computations
- Input injection attacks
- Resource exhaustion

Author: SAM (GID-06) - Security & Threat Engineer
Date: 2025-12-11
Version: 1.0
"""

import hmac
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class FusionSecurityError(Exception):
    """Base exception for fusion security violations."""

    def __init__(self, message: str, error_code: str = "FUSION_SECURITY_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class FusionRateLimitError(FusionSecurityError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class FusionValidationError(FusionSecurityError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None, invalid_value: Any = None):
        super().__init__(message, error_code="VALIDATION_FAILED")
        self.field = field
        # Never log the actual invalid value in production (could contain secrets)
        self.invalid_value_type = type(invalid_value).__name__ if invalid_value else None


class FusionSerializationError(FusionSecurityError):
    """Raised when unsafe serialization is detected."""

    def __init__(self, message: str):
        super().__init__(message, error_code="UNSAFE_SERIALIZATION")


class FusionMemoryError(FusionSecurityError):
    """Raised when memory safety limits are exceeded."""

    def __init__(self, message: str, limit: int, actual: int):
        super().__init__(message, error_code="MEMORY_LIMIT_EXCEEDED")
        self.limit = limit
        self.actual = actual


# ═══════════════════════════════════════════════════════════════════════════════
# ALEX GOVERNANCE RULES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ALEXFusionMemorySafetyRule:
    """
    ALEX Governance Rule: Fusion Memory Safety

    This rule enforces memory safety constraints on all fusion layer operations.
    Violations are logged and may trigger alerts.
    """

    # Maximum items in any list response
    MAX_LIST_SIZE: int = 10_000

    # Maximum payload size in bytes (1MB)
    MAX_PAYLOAD_BYTES: int = 1_048_576

    # Maximum string length for any single field
    MAX_STRING_LENGTH: int = 65_536

    # Maximum recursion depth for nested objects
    MAX_RECURSION_DEPTH: int = 10

    # Rate limit: requests per minute per client
    RATE_LIMIT_RPM: int = 100

    # Maximum number of concurrent requests per client
    MAX_CONCURRENT_REQUESTS: int = 10

    # Allowlist for corridor codes
    VALID_CORRIDOR_PATTERN: str = r"^[A-Z]{2}-[A-Z]{2}$"

    # Allowlist for shipment IDs
    VALID_SHIPMENT_ID_PATTERN: str = r"^[A-Z0-9\-_]{1,64}$"

    # Allowlist for model version formats
    VALID_MODEL_VERSION_PATTERN: str = r"^v?\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?$"

    # Policy identifier for audit logging
    POLICY_ID: str = "PAC-SAM-NEXT-021"
    POLICY_NAME: str = "Fusion Memory Safety"

    def validate_list_size(self, items: List[Any], context: str = "list") -> None:
        """Validate list does not exceed maximum size."""
        if len(items) > self.MAX_LIST_SIZE:
            raise FusionMemoryError(
                f"List size {len(items)} exceeds maximum {self.MAX_LIST_SIZE} for {context}", limit=self.MAX_LIST_SIZE, actual=len(items)
            )

    def validate_payload_size(self, payload: bytes, context: str = "payload") -> None:
        """Validate payload does not exceed maximum size."""
        if len(payload) > self.MAX_PAYLOAD_BYTES:
            raise FusionMemoryError(
                f"Payload size {len(payload)} bytes exceeds maximum {self.MAX_PAYLOAD_BYTES} for {context}",
                limit=self.MAX_PAYLOAD_BYTES,
                actual=len(payload),
            )

    def validate_string_length(self, value: str, field: str = "string") -> None:
        """Validate string does not exceed maximum length."""
        if len(value) > self.MAX_STRING_LENGTH:
            raise FusionValidationError(f"String length {len(value)} exceeds maximum {self.MAX_STRING_LENGTH} for {field}", field=field)

    def validate_corridor(self, corridor: str) -> bool:
        """Validate corridor code format."""
        if not re.match(self.VALID_CORRIDOR_PATTERN, corridor):
            raise FusionValidationError("Invalid corridor format. Expected XX-YY (e.g., US-CN)", field="corridor", invalid_value=corridor)
        return True

    def validate_shipment_id(self, shipment_id: str) -> bool:
        """Validate shipment ID format."""
        if not re.match(self.VALID_SHIPMENT_ID_PATTERN, shipment_id):
            raise FusionValidationError(
                "Invalid shipment_id format. Expected alphanumeric with dashes/underscores (max 64 chars)",
                field="shipment_id",
                invalid_value=shipment_id,
            )
        return True

    def validate_model_version(self, version: str) -> bool:
        """Validate model version format."""
        if not re.match(self.VALID_MODEL_VERSION_PATTERN, version):
            raise FusionValidationError(
                "Invalid model_version format. Expected vX.Y.Z or X.Y.Z", field="model_version", invalid_value=version
            )
        return True


# Global ALEX rule instance
ALEX_FUSION_MEMORY_SAFETY = ALEXFusionMemorySafetyRule()


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""

    tokens: float = 100.0
    last_update: float = field(default_factory=time.time)
    max_tokens: float = 100.0
    refill_rate: float = 100.0 / 60.0  # tokens per second


class RateLimiter:
    """
    Token bucket rate limiter for fusion endpoints.

    Features:
    - Per-client rate limiting
    - Configurable limits per endpoint
    - Automatic cleanup of stale buckets
    - Thread-safe operations (for async use)
    """

    def __init__(self, requests_per_minute: int = 100, burst_size: int = 20, cleanup_interval: int = 300):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.cleanup_interval = cleanup_interval
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.last_cleanup = time.time()

        # Calculate refill rate (tokens per second)
        self.refill_rate = requests_per_minute / 60.0

    def _get_client_key(self, client_id: str, endpoint: str = "") -> str:
        """Generate bucket key for client + endpoint."""
        return f"{client_id}:{endpoint}" if endpoint else client_id

    def _get_or_create_bucket(self, key: str) -> RateLimitBucket:
        """Get existing bucket or create new one."""
        if key not in self.buckets:
            self.buckets[key] = RateLimitBucket(
                tokens=float(self.burst_size), max_tokens=float(self.burst_size), refill_rate=self.refill_rate
            )
        return self.buckets[key]

    def _refill_bucket(self, bucket: RateLimitBucket) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket.last_update

        # Add tokens based on elapsed time
        bucket.tokens = min(bucket.max_tokens, bucket.tokens + (elapsed * bucket.refill_rate))
        bucket.last_update = now

    def _cleanup_stale_buckets(self) -> None:
        """Remove buckets that haven't been used recently."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        stale_threshold = now - self.cleanup_interval
        stale_keys = [key for key, bucket in self.buckets.items() if bucket.last_update < stale_threshold]

        for key in stale_keys:
            del self.buckets[key]

        self.last_cleanup = now

        if stale_keys:
            logger.debug(f"Cleaned up {len(stale_keys)} stale rate limit buckets")

    def check_rate_limit(self, client_id: str, endpoint: str = "", cost: float = 1.0) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            client_id: Client identifier (IP, API key, etc.)
            endpoint: Optional endpoint for per-endpoint limits
            cost: Token cost for this request (default 1.0)

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int)
        """
        self._cleanup_stale_buckets()

        key = self._get_client_key(client_id, endpoint)
        bucket = self._get_or_create_bucket(key)

        self._refill_bucket(bucket)

        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True, 0

        # Calculate retry-after based on token deficit
        deficit = cost - bucket.tokens
        retry_after = int(deficit / bucket.refill_rate) + 1

        return False, retry_after

    def consume(self, client_id: str, endpoint: str = "", cost: float = 1.0) -> None:
        """
        Consume rate limit token or raise exception.

        Args:
            client_id: Client identifier
            endpoint: Optional endpoint
            cost: Token cost

        Raises:
            FusionRateLimitError: If rate limit exceeded
        """
        allowed, retry_after = self.check_rate_limit(client_id, endpoint, cost)

        if not allowed:
            raise FusionRateLimitError(
                f"Rate limit exceeded for client {client_id[:8]}... on {endpoint or 'global'}", retry_after=retry_after
            )

    def get_remaining(self, client_id: str, endpoint: str = "") -> int:
        """Get remaining tokens for client."""
        key = self._get_client_key(client_id, endpoint)
        bucket = self._get_or_create_bucket(key)
        self._refill_bucket(bucket)
        return int(bucket.tokens)


# ═══════════════════════════════════════════════════════════════════════════════
# TIMING-SAFE COMPARISONS
# ═══════════════════════════════════════════════════════════════════════════════


class TimingSafeCompare:
    """
    Timing-safe comparison utilities to prevent timing side-channel attacks.

    All comparisons take constant time regardless of input similarity.
    """

    @staticmethod
    def compare_strings(a: str, b: str) -> bool:
        """
        Compare two strings in constant time.

        Uses HMAC comparison to prevent timing attacks.
        """
        if not isinstance(a, str) or not isinstance(b, str):
            return False

        return hmac.compare_digest(a.encode(), b.encode())

    @staticmethod
    def compare_bytes(a: bytes, b: bytes) -> bool:
        """
        Compare two byte strings in constant time.
        """
        if not isinstance(a, bytes) or not isinstance(b, bytes):
            return False

        return hmac.compare_digest(a, b)

    @staticmethod
    def compare_hashes(hash_a: str, hash_b: str) -> bool:
        """
        Compare two hash strings in constant time.

        Validates format before comparison.
        """
        # Validate hex format
        hex_pattern = re.compile(r"^[a-fA-F0-9]+$")

        if not hex_pattern.match(hash_a) or not hex_pattern.match(hash_b):
            return False

        # Normalize to lowercase
        return hmac.compare_digest(hash_a.lower().encode(), hash_b.lower().encode())

    @staticmethod
    def compare_tokens(token_a: str, token_b: str) -> bool:
        """
        Compare two authentication tokens in constant time.

        Returns False for empty or None tokens.
        """
        if not token_a or not token_b:
            return False

        return hmac.compare_digest(token_a.encode(), token_b.encode())


# ═══════════════════════════════════════════════════════════════════════════════
# SECURE SERIALIZER
# ═══════════════════════════════════════════════════════════════════════════════


class SecureSerializer:
    """
    Secure serialization utilities that block unsafe operations.

    SECURITY:
    - Blocks pickle deserialization (RCE risk)
    - Validates JSON depth and size
    - Sanitizes output to prevent injection
    """

    # Maximum JSON recursion depth
    MAX_DEPTH = 10

    # Maximum JSON size in bytes
    MAX_SIZE = 1_048_576  # 1MB

    # Blocked module prefixes for pickle inspection
    BLOCKED_MODULES = frozenset(
        [
            "os",
            "sys",
            "subprocess",
            "socket",
            "builtins",
            "__builtin__",
            "importlib",
            "eval",
            "exec",
            "compile",
            "open",
            "file",
            "input",
            "raw_input",
            "pickle",
            "marshal",
            "shelve",
            "dill",
            "cloudpickle",
        ]
    )

    @classmethod
    def validate_json_depth(cls, obj: Any, current_depth: int = 0) -> bool:
        """
        Validate JSON object doesn't exceed maximum depth.

        Raises:
            FusionValidationError: If depth exceeds limit
        """
        if current_depth > cls.MAX_DEPTH:
            raise FusionValidationError(f"JSON depth {current_depth} exceeds maximum {cls.MAX_DEPTH}", field="json_depth")

        if isinstance(obj, dict):
            for value in obj.values():
                cls.validate_json_depth(value, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                cls.validate_json_depth(item, current_depth + 1)

        return True

    @classmethod
    def safe_json_loads(cls, data: Union[str, bytes]) -> Any:
        """
        Safely parse JSON with size and depth validation.

        Args:
            data: JSON string or bytes

        Returns:
            Parsed JSON object

        Raises:
            FusionSerializationError: If JSON is invalid or unsafe
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        # Check size
        if len(data) > cls.MAX_SIZE:
            raise FusionSerializationError(f"JSON size {len(data)} exceeds maximum {cls.MAX_SIZE}")

        try:
            obj = json.loads(data)
        except json.JSONDecodeError as e:
            raise FusionSerializationError(f"Invalid JSON: {e}")

        # Validate depth
        cls.validate_json_depth(obj)

        return obj

    @classmethod
    def safe_json_dumps(cls, obj: Any, **kwargs) -> str:
        """
        Safely serialize object to JSON.

        Args:
            obj: Object to serialize
            **kwargs: Additional json.dumps arguments

        Returns:
            JSON string

        Raises:
            FusionSerializationError: If serialization fails
        """
        # Validate depth before serialization
        cls.validate_json_depth(obj)

        try:
            result = json.dumps(obj, **kwargs)
        except (TypeError, ValueError) as e:
            raise FusionSerializationError(f"JSON serialization failed: {e}")

        # Check output size
        if len(result) > cls.MAX_SIZE:
            raise FusionSerializationError(f"Serialized JSON size {len(result)} exceeds maximum {cls.MAX_SIZE}")

        return result

    @classmethod
    def is_pickle_safe(cls, data: bytes) -> Tuple[bool, str]:
        """
        Check if pickle data appears safe (heuristic check).

        WARNING: This is NOT a guarantee of safety. Pickle should be avoided
        for untrusted data. This only catches obvious malicious patterns.

        Returns:
            Tuple of (is_safe, reason)
        """
        # Check for pickle magic bytes
        if not data.startswith(b"\x80"):
            return False, "Invalid pickle magic bytes"

        # Look for dangerous patterns (imports)
        dangerous_patterns = [
            b"__reduce__",
            b"__reduce_ex__",
            b"__getstate__",
            b"__setstate__",
        ]

        for pattern in dangerous_patterns:
            if pattern in data:
                return False, f"Dangerous pattern detected: {pattern.decode()}"

        # Check for blocked module imports
        try:
            text = data.decode("latin-1")  # Safe decode for binary inspection
            for module in cls.BLOCKED_MODULES:
                if module in text:
                    return False, f"Blocked module detected: {module}"
        except Exception:
            pass

        return True, "Passed heuristic checks (use with caution)"


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════


class StrictInputValidator:
    """
    Strict input validation for fusion layer inputs.

    Validates against allowlists and rejects any non-conforming input.
    """

    # Allowlist for score ranges
    SCORE_MIN = 0.0
    SCORE_MAX = 1.0

    # Allowlist for integer ranges
    DEFAULT_INT_MIN = 0
    DEFAULT_INT_MAX = 1_000_000

    # Safe characters for string fields
    SAFE_STRING_PATTERN = re.compile(r"^[\w\s\-_.@:,/]+$", re.UNICODE)

    @classmethod
    def validate_score(cls, value: float, field: str = "score") -> float:
        """Validate score is in valid range."""
        if not isinstance(value, (int, float)):
            raise FusionValidationError(f"Invalid type for {field}: expected number", field=field, invalid_value=value)

        if value < cls.SCORE_MIN or value > cls.SCORE_MAX:
            raise FusionValidationError(
                f"Score {field} must be between {cls.SCORE_MIN} and {cls.SCORE_MAX}", field=field, invalid_value=value
            )

        return float(value)

    @classmethod
    def validate_int_range(cls, value: int, field: str = "integer", min_val: int = None, max_val: int = None) -> int:
        """Validate integer is in valid range."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise FusionValidationError(f"Invalid type for {field}: expected integer", field=field, invalid_value=value)

        min_val = min_val if min_val is not None else cls.DEFAULT_INT_MIN
        max_val = max_val if max_val is not None else cls.DEFAULT_INT_MAX

        if value < min_val or value > max_val:
            raise FusionValidationError(f"Integer {field} must be between {min_val} and {max_val}", field=field, invalid_value=value)

        return value

    @classmethod
    def validate_safe_string(cls, value: str, field: str = "string", max_length: int = 1024) -> str:
        """Validate string contains only safe characters."""
        if not isinstance(value, str):
            raise FusionValidationError(f"Invalid type for {field}: expected string", field=field, invalid_value=value)

        if len(value) > max_length:
            raise FusionValidationError(f"String {field} exceeds maximum length {max_length}", field=field)

        if not cls.SAFE_STRING_PATTERN.match(value):
            raise FusionValidationError(f"String {field} contains unsafe characters", field=field, invalid_value=value)

        return value

    @classmethod
    def validate_list_bounded(cls, items: List[Any], field: str = "list", max_items: int = 10_000) -> List[Any]:
        """Validate list doesn't exceed maximum size."""
        if not isinstance(items, list):
            raise FusionValidationError(f"Invalid type for {field}: expected list", field=field, invalid_value=items)

        if len(items) > max_items:
            raise FusionMemoryError(f"List {field} size {len(items)} exceeds maximum {max_items}", limit=max_items, actual=len(items))

        return items

    @classmethod
    def validate_dict_depth(cls, obj: Dict[str, Any], field: str = "dict", max_depth: int = 10, current_depth: int = 0) -> Dict[str, Any]:
        """Validate dictionary doesn't exceed maximum depth."""
        if not isinstance(obj, dict):
            raise FusionValidationError(f"Invalid type for {field}: expected dict", field=field, invalid_value=obj)

        if current_depth > max_depth:
            raise FusionValidationError(f"Dict {field} depth {current_depth} exceeds maximum {max_depth}", field=field)

        for key, value in obj.items():
            if isinstance(value, dict):
                cls.validate_dict_depth(value, field, max_depth, current_depth + 1)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        cls.validate_dict_depth(item, field, max_depth, current_depth + 1)

        return obj


# ═══════════════════════════════════════════════════════════════════════════════
# STRICT PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class StrictFusionBaseModel(BaseModel):
    """
    Base Pydantic model with strict validation for fusion layer.

    Features:
    - Rejects extra fields (forbid)
    - Validates assignment
    - String length limits
    - List size limits
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        str_max_length=65536,
    )


class FusionScoreInput(StrictFusionBaseModel):
    """Validated input for fusion scoring."""

    shipment_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Z0-9\-_]+$", description="Shipment identifier")

    corridor: Optional[str] = Field(None, pattern=r"^[A-Z]{2}-[A-Z]{2}$", description="Trade corridor (e.g., US-CN)")

    scores: List[float] = Field(..., min_length=1, max_length=100, description="List of component scores")

    weights: Optional[List[float]] = Field(None, min_length=1, max_length=100, description="Optional weights for scores")

    model_version: str = Field(default="v0.2.0", pattern=r"^v?\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?$", description="Model version identifier")

    @field_validator("scores", "weights")
    @classmethod
    def validate_score_range(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Ensure all scores are in valid range."""
        if v is None:
            return v
        for i, score in enumerate(v):
            if score < 0.0 or score > 1.0:
                raise ValueError(f"Score at index {i} out of range [0.0, 1.0]")
        return v


class FusionBatchInput(StrictFusionBaseModel):
    """Validated batch input for fusion operations."""

    items: List[FusionScoreInput] = Field(..., min_length=1, max_length=1000, description="Batch of fusion inputs")

    correlation_id: Optional[str] = Field(None, max_length=64, pattern=r"^[a-zA-Z0-9\-_]+$", description="Request correlation ID")


class FusionResponse(StrictFusionBaseModel):
    """Validated fusion response."""

    shipment_id: str = Field(..., description="Shipment identifier")
    fused_score: float = Field(..., ge=0.0, le=1.0, description="Fused score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")
    components: Dict[str, float] = Field(default_factory=dict, description="Score components")
    model_version: str = Field(default="v0.2.0", description="Model version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


# ═══════════════════════════════════════════════════════════════════════════════
# FUSION GUARD - MAIN SECURITY ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════


class FusionGuard:
    """
    Main security orchestrator for fusion layer.

    Combines all security controls:
    - Rate limiting
    - Input validation
    - Payload size checks
    - Timing-safe operations
    - Audit logging

    Usage:
        guard = FusionGuard()

        # In endpoint
        guard.validate_request(client_id, payload)
        result = process_fusion(payload)
        return guard.validate_response(result)
    """

    def __init__(self, rate_limiter: RateLimiter = None, alex_rule: ALEXFusionMemorySafetyRule = None):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.alex_rule = alex_rule or ALEX_FUSION_MEMORY_SAFETY
        self.validator = StrictInputValidator()
        self.serializer = SecureSerializer()

        # Audit log for security events
        self._security_events: List[Dict[str, Any]] = []
        self._max_security_events = 1000

    def _log_security_event(self, event_type: str, client_id: str, details: Dict[str, Any], severity: str = "INFO") -> None:
        """Log security event for audit."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "client_id": client_id[:16] if client_id else "unknown",  # Truncate for privacy
            "severity": severity,
            "details": details,
            "policy": self.alex_rule.POLICY_ID,
        }

        # Maintain bounded list
        self._security_events.append(event)
        if len(self._security_events) > self._max_security_events:
            self._security_events = self._security_events[-self._max_security_events :]

        # Log based on severity
        if severity == "ERROR":
            logger.error(f"FUSION_SECURITY: {event_type} - {details}")
        elif severity == "WARNING":
            logger.warning(f"FUSION_SECURITY: {event_type} - {details}")
        else:
            logger.info(f"FUSION_SECURITY: {event_type} - {details}")

    def check_rate_limit(self, client_id: str, endpoint: str = "") -> None:
        """
        Check rate limit for client.

        Raises:
            FusionRateLimitError: If rate limit exceeded
        """
        try:
            self.rate_limiter.consume(client_id, endpoint)
        except FusionRateLimitError as e:
            self._log_security_event(
                "RATE_LIMIT_EXCEEDED", client_id, {"endpoint": endpoint, "retry_after": e.retry_after}, severity="WARNING"
            )
            raise

    def validate_payload_size(self, payload: Union[str, bytes], context: str = "request") -> None:
        """
        Validate payload size.

        Raises:
            FusionMemoryError: If payload too large
        """
        if isinstance(payload, str):
            payload = payload.encode()

        try:
            self.alex_rule.validate_payload_size(payload, context)
        except FusionMemoryError as e:
            self._log_security_event(
                "PAYLOAD_SIZE_EXCEEDED", "system", {"context": context, "size": len(payload), "limit": e.limit}, severity="WARNING"
            )
            raise

    def validate_json_input(self, data: Union[str, bytes]) -> Any:
        """
        Validate and parse JSON input.

        Returns:
            Parsed JSON object

        Raises:
            FusionSerializationError: If JSON is invalid
        """
        return self.serializer.safe_json_loads(data)

    def validate_corridor(self, corridor: str) -> str:
        """Validate corridor format."""
        self.alex_rule.validate_corridor(corridor)
        return corridor

    def validate_shipment_id(self, shipment_id: str) -> str:
        """Validate shipment ID format."""
        self.alex_rule.validate_shipment_id(shipment_id)
        return shipment_id

    def validate_list_response(self, items: List[Any], context: str = "response") -> List[Any]:
        """
        Validate list response doesn't exceed limits.

        Returns:
            Truncated list if necessary
        """
        max_size = self.alex_rule.MAX_LIST_SIZE

        if len(items) > max_size:
            self._log_security_event(
                "LIST_TRUNCATED", "system", {"context": context, "original_size": len(items), "truncated_to": max_size}, severity="INFO"
            )
            return items[:max_size]

        return items

    def validate_fusion_input(self, input_data: Dict[str, Any]) -> FusionScoreInput:
        """
        Validate fusion input against strict schema.

        Returns:
            Validated FusionScoreInput

        Raises:
            FusionValidationError: If validation fails
        """
        try:
            return FusionScoreInput(**input_data)
        except ValidationError as e:
            raise FusionValidationError(f"Input validation failed: {e.error_count()} errors", field="input")

    def validate_batch_input(self, input_data: Dict[str, Any]) -> FusionBatchInput:
        """
        Validate batch fusion input.

        Returns:
            Validated FusionBatchInput

        Raises:
            FusionValidationError: If validation fails
        """
        try:
            return FusionBatchInput(**input_data)
        except ValidationError as e:
            raise FusionValidationError(f"Batch validation failed: {e.error_count()} errors", field="batch_input")

    def timing_safe_compare(self, a: str, b: str) -> bool:
        """Perform timing-safe string comparison."""
        return TimingSafeCompare.compare_strings(a, b)

    def get_security_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events for audit."""
        return self._security_events[-limit:]

    def get_rate_limit_remaining(self, client_id: str, endpoint: str = "") -> int:
        """Get remaining rate limit tokens for client."""
        return self.rate_limiter.get_remaining(client_id, endpoint)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY INJECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Global FusionGuard instance
_fusion_guard: Optional[FusionGuard] = None


def get_fusion_guard() -> FusionGuard:
    """Get or create global FusionGuard instance."""
    global _fusion_guard
    if _fusion_guard is None:
        _fusion_guard = FusionGuard()
    return _fusion_guard


def validate_fusion_input(input_data: Dict[str, Any]) -> FusionScoreInput:
    """Convenience function to validate fusion input."""
    return get_fusion_guard().validate_fusion_input(input_data)


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════


def rate_limit_dependency(requests_per_minute: int = 100, endpoint: str = "") -> Callable:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @router.get("/endpoint")
        async def endpoint(
            _: None = Depends(rate_limit_dependency(100, "endpoint"))
        ):
            ...
    """

    def dependency(request) -> None:
        # Get client identifier from request
        client_id = getattr(request, "client", None)
        if client_id:
            client_id = f"{client_id.host}:{client_id.port}"
        else:
            client_id = request.headers.get("X-Forwarded-For", "unknown")

        guard = get_fusion_guard()
        guard.check_rate_limit(client_id, endpoint)

    return dependency


def payload_size_dependency(max_bytes: int = 1_048_576) -> Callable:
    """
    FastAPI dependency for payload size validation.

    Usage:
        @router.post("/endpoint")
        async def endpoint(
            body: bytes = Body(...),
            _: None = Depends(payload_size_dependency(1_048_576))
        ):
            ...
    """

    async def dependency(request) -> None:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            raise FusionMemoryError(
                f"Content-Length {content_length} exceeds maximum {max_bytes}", limit=max_bytes, actual=int(content_length)
            )

    return dependency
