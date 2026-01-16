"""
Rate Limiting Middleware - Sliding Window Algorithm
====================================================

PAC-SEC-P821: AUTHENTICATION MIDDLEWARE HARDENING
Component: Per-Endpoint Rate Limiting

INVARIANTS:
  INV-AUTH-004: Rate limiting MUST use sliding window per endpoint
  INV-RATE-001: Rate limits MUST be enforced before authentication
  INV-RATE-002: Rate limit state MUST be Redis-backed for distributed deployment
  INV-RATE-003: Rate exceeded MUST return 429 Too Many Requests

ALGORITHM: Sliding Window Log
  - Maintains timestamp log of recent requests
  - Window slides continuously (no fixed boundaries)
  - More accurate than fixed window counters
  - Memory-efficient with automatic cleanup
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
logger = logging.getLogger("chainbridge.ratelimit")


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"

    # Default limits (requests per window)
    default_limit: int = 100
    default_window_seconds: int = 60

    # Per-endpoint overrides
    endpoint_limits: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    # e.g., {"/v1/transaction": (10, 60), "/health": (1000, 60)}

    # Authenticated user multiplier
    authenticated_multiplier: float = 2.0

    # API key tier multipliers
    tier_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "free": 1.0,
        "basic": 2.0,
        "pro": 5.0,
        "enterprise": 10.0,
    })

    # Headers
    rate_limit_header: str = "X-RateLimit-Limit"
    rate_remaining_header: str = "X-RateLimit-Remaining"
    rate_reset_header: str = "X-RateLimit-Reset"
    retry_after_header: str = "Retry-After"


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: Optional[int] = None  # Seconds until retry allowed


class SlidingWindowRateLimiter:
    """
    Sliding window log rate limiter.

    Uses Redis sorted sets for efficient O(log N) operations.
    Falls back to in-memory storage if Redis unavailable.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._redis = None
        self._memory_store: Dict[str, List[float]] = {}
        self._connect_redis()

    def _connect_redis(self) -> None:
        """Attempt Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
            )
            self._redis.ping()
            logger.info("Rate limiter connected to Redis")
        except ImportError:
            logger.warning("redis package not installed - using in-memory rate limiting")
            self._redis = None
        except Exception as e:
            logger.warning(f"Redis connection failed - using in-memory rate limiting: {e}")
            self._redis = None

    def _key(self, identifier: str, endpoint: str) -> str:
        """Generate rate limit key."""
        return f"chainbridge:ratelimit:{identifier}:{endpoint}"

    def _get_limit(self, endpoint: str, multiplier: float = 1.0) -> Tuple[int, int]:
        """Get rate limit for endpoint."""
        if endpoint in self.config.endpoint_limits:
            limit, window = self.config.endpoint_limits[endpoint]
        else:
            limit = self.config.default_limit
            window = self.config.default_window_seconds

        return int(limit * multiplier), window

    def check(
        self,
        identifier: str,
        endpoint: str,
        multiplier: float = 1.0,
    ) -> RateLimitResult:
        """
        Check rate limit using sliding window log algorithm.

        Args:
            identifier: Client identifier (IP, user_id, api_key)
            endpoint: Request endpoint/path
            multiplier: Limit multiplier based on auth tier

        Returns:
            RateLimitResult with allowed status and metadata
        """
        now = time.time()
        limit, window = self._get_limit(endpoint, multiplier)
        window_start = now - window

        if self._redis:
            return self._check_redis(identifier, endpoint, now, window_start, limit, window)
        else:
            return self._check_memory(identifier, endpoint, now, window_start, limit, window)

    def _check_redis(
        self,
        identifier: str,
        endpoint: str,
        now: float,
        window_start: float,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        """Check rate limit using Redis sorted set."""
        key = self._key(identifier, endpoint)

        try:
            pipe = self._redis.pipeline()

            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry on key
            pipe.expire(key, window * 2)

            results = pipe.execute()
            current_count = results[1]

            # Check if over limit
            if current_count >= limit:
                # Get oldest entry to calculate retry time
                oldest = self._redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(oldest_time + window - now) + 1
                else:
                    retry_after = window

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=int(now + window),
                    retry_after=max(1, retry_after),
                )

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - current_count - 1,
                reset_at=int(now + window),
            )

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open on Redis errors (allow request)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(now + window),
            )

    def _check_memory(
        self,
        identifier: str,
        endpoint: str,
        now: float,
        window_start: float,
        limit: int,
        window: int,
    ) -> RateLimitResult:
        """Check rate limit using in-memory storage."""
        key = self._key(identifier, endpoint)

        # Get or create request log
        if key not in self._memory_store:
            self._memory_store[key] = []

        request_log = self._memory_store[key]

        # Remove old entries
        request_log[:] = [ts for ts in request_log if ts > window_start]

        # Check if over limit
        if len(request_log) >= limit:
            if request_log:
                oldest = min(request_log)
                retry_after = int(oldest + window - now) + 1
            else:
                retry_after = window

            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=int(now + window),
                retry_after=max(1, retry_after),
            )

        # Add current request
        request_log.append(now)

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - len(request_log),
            reset_at=int(now + window),
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    Enforces INV-AUTH-004: Rate limiting MUST use sliding window per endpoint.

    Rate limit is applied per:
      1. IP address (for unauthenticated requests)
      2. User ID (for authenticated requests)
      3. API key ID (for API key requests)

    Authenticated users get higher limits via multiplier.
    """

    def __init__(
        self,
        app,
        exempt_paths: FrozenSet[str] = frozenset(),
        config: Optional[RateLimitConfig] = None,
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths
        self.config = config or RateLimitConfig()
        self.limiter = SlidingWindowRateLimiter(self.config)

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        if path in self.exempt_paths:
            return True
        path_normalized = path.rstrip("/")
        if path_normalized in self.exempt_paths:
            return True
        for exempt in self.exempt_paths:
            if path.startswith(exempt + "/"):
                return True
        return False

    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier for request."""
        # Check for authenticated user
        auth = getattr(request.state, "auth", None)
        if auth and auth.authenticated:
            if auth.user_id:
                return f"user:{auth.user_id}"
            if auth.claims.get("key_id"):
                return f"key:{auth.claims['key_id']}"

        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"

    def _get_multiplier(self, request: Request) -> float:
        """Get rate limit multiplier based on authentication."""
        auth = getattr(request.state, "auth", None)
        if not auth or not auth.authenticated:
            return 1.0

        # Check for tier in API key claims
        tier = auth.claims.get("tier", "free")
        if tier in self.config.tier_multipliers:
            return self.config.tier_multipliers[tier]

        # Default authenticated multiplier
        return self.config.authenticated_multiplier

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for rate limiting."""
        # Remove trailing slash
        path = path.rstrip("/")

        # Collapse path parameters (e.g., /v1/users/123 -> /v1/users/:id)
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part.isdigit() or (len(part) == 36 and "-" in part):
                # Numeric ID or UUID
                normalized.append(":id")
            else:
                normalized.append(part)

        return "/".join(normalized)

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to request."""
        path = request.url.path

        # Check exemption
        if self._is_exempt(path):
            return await call_next(request)

        # Get identifier and endpoint
        identifier = self._get_identifier(request)
        endpoint = self._normalize_endpoint(path)
        multiplier = self._get_multiplier(request)

        # Check rate limit
        result = self.limiter.check(identifier, endpoint, multiplier)

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded: identifier={identifier} "
                f"endpoint={endpoint} limit={result.limit}"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": result.retry_after,
                },
                headers={
                    self.config.rate_limit_header: str(result.limit),
                    self.config.rate_remaining_header: "0",
                    self.config.rate_reset_header: str(result.reset_at),
                    self.config.retry_after_header: str(result.retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers[self.config.rate_limit_header] = str(result.limit)
        response.headers[self.config.rate_remaining_header] = str(result.remaining)
        response.headers[self.config.rate_reset_header] = str(result.reset_at)

        return response
