# Authentication System Specification

**PAC Reference:** PAC-SEC-P821  
**Governance Tier:** POLICY  
**Priority:** 2 (Critical Security Gap)  
**Status:** IMPLEMENTED

---

## 1. Executive Summary

This document specifies the authentication middleware stack implemented per PAC-SEC-P821 to address the critical security gap identified in the ChainBridge API layer. All API execution paths now require authentication with fail-closed behavior.

## 2. Constitutional Invariants

The authentication system enforces the following constitutional invariants:

| Invariant | Description | Enforcement |
|-----------|-------------|-------------|
| **INV-AUTH-001** | All API requests MUST pass authentication (fail-closed) | HARD |
| **INV-AUTH-002** | GID binding MUST be verified against gid_registry.json | HARD |
| **INV-AUTH-003** | Session state MUST be Redis-backed with TTL enforcement | HARD |
| **INV-AUTH-004** | Rate limiting MUST use sliding window per endpoint | HARD |
| **INV-AUTH-005** | Request signatures MUST be cryptographically verified | HARD |
| **INV-AUTH-006** | Token expiry MUST be enforced with zero tolerance | HARD |
| **INV-AUTH-007** | API keys MUST be stored as salted hashes | HARD |

## 3. Architecture

### 3.1 Middleware Stack

The authentication middleware is applied as a stack with the following execution order:

```
Request → [RateLimitMiddleware] → [SignatureMiddleware] → [AuthMiddleware] → [IdentityMiddleware] → [SessionMiddleware] → Application
```

### 3.2 Component Overview

| Component | File | Responsibility |
|-----------|------|----------------|
| RateLimitMiddleware | `api/middleware/rate_limit.py` | Sliding window rate limiting |
| SignatureMiddleware | `api/middleware/signature.py` | Cryptographic request verification |
| AuthMiddleware | `api/middleware/auth.py` | JWT/API key validation |
| IdentityMiddleware | `api/middleware/identity.py` | GID registry binding |
| SessionMiddleware | `api/middleware/session.py` | Redis session management |

### 3.3 Configuration Files

| File | Purpose |
|------|---------|
| `config/auth_config.yaml` | Runtime configuration for all auth components |
| `core/governance/auth_policies.json` | Constitutional enforcement rules |
| `config/api_keys.json` | Secure storage for API key hashes |

## 4. Authentication Methods

### 4.1 JWT Authentication

**Header Format:**
```
Authorization: Bearer <token>
```

**Token Claims:**
- `sub` - Subject (user ID)
- `gid` - Agent GID (optional, for agent requests)
- `iss` - Issuer (must match `chainbridge`)
- `aud` - Audience (must match `chainbridge-api`)
- `exp` - Expiry timestamp (enforced with zero tolerance)
- `iat` - Issued at timestamp

**Configuration:**
```yaml
jwt:
  algorithm: HS256
  expiry_seconds: 3600
  issuer: chainbridge
  audience: chainbridge-api
```

### 4.2 API Key Authentication

**Header Format:**
```
X-API-Key: <key>
```

**Storage Format:**
```json
{
  "key-id": {
    "hash": "<sha256-hash>",
    "salt": "<random-salt>",
    "user_id": "<user-identifier>",
    "gid": "<optional-gid>",
    "enabled": true,
    "tier": "pro",
    "scopes": ["read", "write"]
  }
}
```

## 5. GID Identity Binding

### 5.1 Enforcement Rules

Per `gid_registry.json`:

| Rule | Description |
|------|-------------|
| RULE-GID-001 | All PACs must reference a valid GID |
| RULE-GID-002 | Unknown GID → immediate rejection (HARD FAIL) |
| RULE-GID-003 | GID format must match `GID-XX` where XX is 00-99 |
| RULE-GID-004 | GIDs are immutable once assigned |
| RULE-GID-005 | No agent may operate without a registered GID |
| RULE-GID-006 | System components are non-persona |
| RULE-GID-007 | Only SYSTEM_ORCHESTRATOR may issue BER |

### 5.2 Lane Permissions

Agent requests are validated against execution lane permissions:

```
/v1/transaction/* → CORE lane required
/v1/governance/* → GOVERNANCE lane required
/api/* → API lane required
```

Agents with `execution_lanes: ["ALL"]` bypass lane restrictions.

## 6. Rate Limiting

### 6.1 Algorithm

**Sliding Window Log** algorithm provides:
- Continuous window (no fixed boundaries)
- O(log N) operations with Redis sorted sets
- Accurate rate tracking
- Memory-efficient with automatic cleanup

### 6.2 Default Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Default | 100 | 60s |
| `/v1/transaction` | 10 | 60s |
| `/v1/governance` | 20 | 60s |
| `/v1/governance/scram` | 5 | 60s |
| `/health` | 1000 | 60s |

### 6.3 Tier Multipliers

| Tier | Multiplier |
|------|------------|
| free | 1.0x |
| basic | 2.0x |
| pro | 5.0x |
| enterprise | 10.0x |

### 6.4 Response Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1703001234
Retry-After: 42
```

## 7. Request Signatures

### 7.1 Signature Format

**Headers:**
```
X-Signature: sha256=<base64-signature>
X-Timestamp: <unix-timestamp-ms>
X-Nonce: <random-nonce>
```

### 7.2 Signed Payload Construction

```
<method>|<path>|<timestamp>|<body-hash>|<nonce>
```

**Example:**
```
POST|/v1/transaction|1703000000000|e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855|abc123
```

### 7.3 Required Endpoints

Signature verification is required for:
- `/v1/transaction`
- `/v1/governance/scram`

### 7.4 Timestamp Tolerance

Requests are rejected if timestamp differs from server time by more than **5 minutes** (300 seconds).

## 8. Session Management

### 8.1 Session Storage

Sessions are stored in Redis with automatic TTL enforcement:

```
Key: chainbridge:session:<session-id>
TTL: 3600 seconds (1 hour)
```

### 8.2 Session Data

```json
{
  "session_id": "<256-bit-random>",
  "user_id": "<user-identifier>",
  "gid": "<optional-gid>",
  "created_at": "<iso-timestamp>",
  "last_accessed": "<iso-timestamp>",
  "expires_at": "<iso-timestamp>",
  "ip_address": "<client-ip>",
  "user_agent": "<user-agent>"
}
```

### 8.3 Cookie Configuration

```yaml
cookie:
  name: chainbridge_session
  httponly: true
  secure: true
  samesite: lax
```

## 9. Exempt Paths

The following paths bypass authentication:

- `/` - Root/API info
- `/health`, `/healthz` - Health checks
- `/ready`, `/readyz` - Readiness probes
- `/metrics` - Prometheus metrics
- `/docs`, `/redoc` - API documentation
- `/openapi.json` - OpenAPI specification

## 10. Error Responses

### 10.1 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Authentication required",
  "code": "AUTH_REQUIRED"
}
```

**Codes:**
- `AUTH_REQUIRED` - No credentials provided
- `INVALID_TOKEN` - Invalid or expired JWT
- `INVALID_API_KEY` - Invalid API key
- `MISSING_SIGNATURE` - Signature required but missing
- `INVALID_SIGNATURE` - Signature verification failed

### 10.2 403 Forbidden

```json
{
  "error": "Forbidden",
  "message": "Invalid agent identity",
  "code": "INVALID_GID"
}
```

**Codes:**
- `INVALID_GID` - GID not in registry
- `GID_REQUIRED` - Agent identity required
- `LANE_DENIED` - Agent not permitted in lane

### 10.3 429 Too Many Requests

```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 42
}
```

## 11. Security Considerations

### 11.1 Fail-Closed Behavior

**INV-AUTH-001** mandates fail-closed authentication:
- Any validation error → 401 Unauthorized
- Any system error → 401 Unauthorized (never expose internals)
- Missing credentials → 401 Unauthorized
- `AuthConfig(fail_closed=False)` → Raises `ValueError`

### 11.2 Constant-Time Comparison

All credential comparisons use `hmac.compare_digest()` to prevent timing attacks.

### 11.3 Secret Management

Secrets are loaded from environment variables:
- `JWT_SECRET_KEY` - JWT signing key
- `SIGNATURE_SECRET_KEY` - Request signature key
- `REDIS_URL` - Redis connection string

## 12. Testing

### 12.1 Unit Tests

Location: `tests/api/test_auth_middleware.py`

Coverage:
- JWT validation (valid, expired, malformed, wrong issuer)
- API key validation (valid, invalid, disabled)
- GID validation (valid, unknown, invalid format)
- Rate limiting (within limit, exceeded, per-identifier)
- Signature verification (valid, invalid, replay)

### 12.2 Integration Tests

Location: `tests/integration/test_auth_enforcement.py`

Coverage:
- Full request lifecycle
- Exempt path bypass
- JWT authentication flow
- API key authentication flow
- GID identity binding
- Rate limit headers

### 12.3 CI Workflow

Location: `.github/workflows/auth-validation.yml`

Jobs:
1. Lint auth middleware
2. Run unit tests with coverage
3. Run integration tests with Redis
4. Validate security configuration
5. Verify fail-closed behavior
6. Validate GID registry format

## 13. Deployment

### 13.1 Environment Variables

```bash
# Required
export JWT_SECRET_KEY="<256-bit-random-key>"
export SIGNATURE_SECRET_KEY="<256-bit-random-key>"

# Optional (with defaults)
export REDIS_URL="redis://localhost:6379/0"
export CORS_ORIGINS="*"
```

### 13.2 Redis Setup

Session and rate limit storage requires Redis:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 13.3 API Key Generation

To generate a new API key:

```python
import hashlib
import secrets
import json

api_key = secrets.token_urlsafe(32)
salt = secrets.token_hex(16)
key_hash = hashlib.sha256(f"{salt}{api_key}".encode()).hexdigest()

print(f"API Key: {api_key}")
print(f"Store this in api_keys.json:")
print(json.dumps({
    "hash": key_hash,
    "salt": salt,
    "user_id": "your-user-id",
    "enabled": True,
    "tier": "pro"
}, indent=2))
```

## 14. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025 | Initial implementation per PAC-SEC-P821 |

---

**Document Classification:** POLICY  
**Governance Binding:** PAC-SEC-P821  
**Review Cycle:** Quarterly  
**Last Updated:** 2025
