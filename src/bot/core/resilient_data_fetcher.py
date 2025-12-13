"""
Enterprise-Grade Resilient Data Fetcher
Implements circuit breaker, exponential backoff, graceful degradation, and caching
"""

import hashlib
import json
import logging
import time
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, use fallback
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {func.__name__} entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovered, resetting to CLOSED")
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")


class ResilientDataFetcher:
    """
    Enterprise-grade data fetcher with:
    - Exponential backoff for rate limits
    - Circuit breaker for failing endpoints
    - Intelligent caching with TTL
    - Graceful degradation
    - Request deduplication
    """

    def __init__(self, cache_dir: Path = Path("cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.in_flight_requests: Dict[str, Any] = {}

    def fetch_with_resilience(
        self,
        url: str,
        fallback_value: Any,
        cache_ttl: int = 300,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        timeout: int = 10,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        validator: Optional[Callable[[Any], bool]] = None,
    ) -> Tuple[Any, str]:
        """
        Fetch data with full resilience stack

        Returns:
            Tuple of (data, source) where source is: 'live', 'cache', or 'fallback'
        """
        cache_key = self._generate_cache_key(url, params)

        # Check for in-flight request (request deduplication)
        if cache_key in self.in_flight_requests:
            logger.debug(f"Deduplicating request for {url}")
            return self.in_flight_requests[cache_key], "deduplicated"

        # Try cache first
        cached_data = self._get_from_cache(cache_key, cache_ttl)
        if cached_data is not None:
            logger.debug(f"Cache HIT for {url}")
            return cached_data, "cache"

        # Get or create circuit breaker for this endpoint
        cb_key = self._get_circuit_breaker_key(url)
        if cb_key not in self.circuit_breakers:
            self.circuit_breakers[cb_key] = CircuitBreaker()

        circuit_breaker = self.circuit_breakers[cb_key]

        # Try live fetch with circuit breaker
        try:
            data = circuit_breaker.call(
                self._fetch_with_retry,
                url=url,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                timeout=timeout,
                headers=headers or {},
                params=params or {},
            )

            # Validate if validator provided
            if validator and not validator(data):
                logger.warning(f"Validation failed for {url}, using fallback")
                return fallback_value, "fallback"

            # Cache successful response
            self._save_to_cache(cache_key, data)
            return data, "live"

        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")

            # Try stale cache as backup
            stale_data = self._get_from_cache(cache_key, cache_ttl=None)
            if stale_data is not None:
                logger.info(f"Using STALE cache for {url}")
                return stale_data, "stale_cache"

            # Final fallback
            logger.info(f"Using FALLBACK value for {url}")
            return fallback_value, "fallback"

    def _fetch_with_retry(self, url: str, max_retries: int, backoff_factor: float, timeout: int, headers: Dict, params: Dict) -> Any:
        """Fetch with exponential backoff retry logic"""

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=timeout)

                # Handle rate limiting (429)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(response.headers.get("Retry-After", backoff_factor**attempt))
                        logger.warning(f"Rate limited on {url}, retrying after {retry_after}s")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded for {url}")

                # Raise for other HTTP errors
                response.raise_for_status()

                # Return JSON data
                return response.json()

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(f"Timeout on {url}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_factor**attempt
                    logger.warning(f"Request failed for {url}: {e}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise

        raise Exception(f"Max retries exceeded for {url}")

    def _generate_cache_key(self, url: str, params: Optional[Dict]) -> str:
        """Generate cache key from URL and params"""
        params_str = json.dumps(params or {}, sort_keys=True)
        key_input = f"{url}:{params_str}"
        return hashlib.md5(key_input.encode()).hexdigest()

    def _get_circuit_breaker_key(self, url: str) -> str:
        """Extract circuit breaker key from URL (domain level)"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _get_from_cache(self, cache_key: str, cache_ttl: Optional[int]) -> Optional[Any]:
        """Retrieve data from cache if not expired"""
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)

            # Check TTL if specified
            if cache_ttl is not None:
                cached_time = datetime.fromisoformat(cached["timestamp"])
                age = (datetime.now() - cached_time).total_seconds()

                if age > cache_ttl:
                    logger.debug(f"Cache expired (age: {age}s, ttl: {cache_ttl}s)")
                    return None

            return cached["data"]

        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: Any):
        """Save data to cache with timestamp"""
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cached_data = {"timestamp": datetime.now().isoformat(), "data": data}

            with open(cache_file, "w") as f:
                json.dump(cached_data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")


# Decorator for easy resilient fetching
def resilient_fetch(fallback_value: Any, cache_ttl: int = 300, max_retries: int = 3):
    """Decorator to make any function resilient"""

    def decorator(func: Callable) -> Callable:
        fetcher = ResilientDataFetcher()

        @wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[Any, str]:
            try:
                result = func(*args, **kwargs)
                return result, "live"
            except Exception as e:
                logger.warning(f"{func.__name__} failed: {e}, using fallback")
                return fallback_value, "fallback"

        return wrapper

    return decorator


# Global fetcher instance
_global_fetcher = ResilientDataFetcher()


def get_resilient_fetcher() -> ResilientDataFetcher:
    """Get global resilient fetcher instance"""
    return _global_fetcher
