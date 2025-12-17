# Gateway Airlock Enforcement Specification

**Status:** CANONICAL
**Version:** v1.0
**Authoring Agent:** Sam (GID-06), Security & Threat Engineer
**Applies To:** ChainBridge Gateway; all execution paths
**Governance:** Gateway Contract v1; CCDS v1 (ENFORCED)
**Related:** [gateway_threat_model.md](gateway_threat_model.md)

---

## 1. Purpose

This document defines **enforceable middleware policy** for the ChainBridge Gateway Airlock pattern. The goal is to ensure no LLM, agent, or external caller can bypass gateway controls to reach execution, secrets, or datastores.

**Core Invariants:**
- **"No PDO → No Execution"** — Every module/pipeline/OCC mutation requires a valid, gateway-issued PDO.
- **"No Gateway → No Action"** — No execution path exists outside gateway middleware.

---

## 2. Canonical Middleware Order

All requests to protected endpoints **MUST** pass through this middleware stack in exact order. Failure at any layer terminates the request immediately (fail-closed).

```
┌─────────────────────────────────────────────────────────────┐
│                     INCOMING REQUEST                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: AUTHENTICATION (AuthN)                            │
│  ─────────────────────────────────────────────────────────  │
│  • Verify bearer token / API key / mTLS cert                │
│  • Extract principal identity (user_id, service_id, agent)  │
│  • Reject: 401 Unauthorized                                 │
│  • Audit: AUTH_FAILED event                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: AUTHORIZATION (AuthZ)                             │
│  ─────────────────────────────────────────────────────────  │
│  • Check principal permissions for endpoint + action        │
│  • Enforce scope (read/write/execute) per resource          │
│  • Reject: 403 Forbidden                                    │
│  • Audit: AUTHZ_DENIED event                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: RATE LIMITING                                     │
│  ─────────────────────────────────────────────────────────  │
│  • Apply limits per: user, agent, model-tier, endpoint      │
│  • Enforce request size caps                                │
│  • Reject: 429 Too Many Requests                            │
│  • Audit: RATE_LIMITED event                                │
│  • Headers: X-RateLimit-Limit, X-RateLimit-Remaining        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: PDO VERIFICATION                                  │
│  ─────────────────────────────────────────────────────────  │
│  • Validate GatewayIntent → GatewayPDO flow                 │
│  • Verify PDO signature/hash if required                    │
│  • Check PDO.outcome == APPROVED                            │
│  • Reject: 422 Unprocessable Entity                         │
│  • Audit: PDO_REJECTED event with reasons                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5: EXECUTION                                         │
│  ─────────────────────────────────────────────────────────  │
│  • Route to handler (module/pipeline/OCC/ChainBoard)        │
│  • Execute with sandboxed context                           │
│  • Return: 200/201/204 on success                           │
│  • Audit: EXECUTION_COMPLETE event                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Protected Endpoint Families

| Endpoint Pattern | Protection Level | PDO Required | Notes |
|------------------|------------------|--------------|-------|
| `/modules/register` | **ADMIN** | Yes | Disabled in prod by default |
| `/modules/{name}/execute` | **ELEVATED** | Yes | Module allowlist enforced |
| `/pipelines` (POST) | **ELEVATED** | Yes | Pipeline creation |
| `/pipelines/{name}/execute` | **ELEVATED** | Yes | Pipeline execution |
| `/occ/artifacts` (mutate) | **ELEVATED** | Yes | OCC create/update/delete |
| `/occ/decisions` (mutate) | **ELEVATED** | Yes | Decision recording |
| `/occ/proofpacks` (mutate) | **ELEVATED** | Yes | ProofPack generation |
| `/occ/*` (read) | **STANDARD** | No | Read-only operations |
| `/api/chainboard/*` | **STANDARD** | No | Projection layer (read-only) |
| `/health`, `/`, `/docs` | **PUBLIC** | No | Health/info endpoints |

---

## 4. Rejection Behavior

### 4.1 HTTP Status Codes

| Failure Layer | HTTP Code | Response Body | Retry Allowed |
|---------------|-----------|---------------|---------------|
| AuthN | `401 Unauthorized` | `{"error": "authentication_required", "detail": "..."}` | Yes (with valid creds) |
| AuthZ | `403 Forbidden` | `{"error": "permission_denied", "detail": "..."}` | No |
| Rate Limit | `429 Too Many Requests` | `{"error": "rate_limited", "retry_after": <seconds>}` | Yes (after backoff) |
| PDO Rejected | `422 Unprocessable Entity` | `{"error": "pdo_rejected", "reasons": [...]}` | No (intent invalid) |
| PDO Missing | `400 Bad Request` | `{"error": "pdo_required", "detail": "..."}` | Yes (with valid PDO) |
| Execution Error | `500 Internal Server Error` | `{"error": "execution_failed", "detail": "..."}` | Depends |

### 4.2 Audit Event Schema

Every rejection **MUST** emit an audit event:

```json
{
  "event_type": "GATEWAY_REJECTION",
  "timestamp": "2025-12-17T12:00:00Z",
  "layer": "AUTHN | AUTHZ | RATE_LIMIT | PDO_VERIFY",
  "principal": {
    "type": "user | service | agent",
    "id": "<principal_id>",
    "agent_gid": "<GID if agent>"
  },
  "request": {
    "method": "POST",
    "path": "/modules/foo/execute",
    "correlation_id": "<req_correlation_id>"
  },
  "rejection": {
    "code": 401,
    "reason": "<machine_readable_reason>",
    "detail": "<human_detail>"
  }
}
```

### 4.3 Response Headers (Always Present)

```
X-Request-Id: <correlation_id>
X-Gateway-Layer: <last_passed_layer>
X-RateLimit-Limit: <limit>
X-RateLimit-Remaining: <remaining>
X-RateLimit-Reset: <epoch_timestamp>
```

---

## 5. Rate Limiting Tiers

### 5.1 Per-User Limits

| Tier | Read Endpoints | Mutate Endpoints | Execute Endpoints |
|------|----------------|------------------|-------------------|
| **Anonymous** | 10 req/min | 0 (blocked) | 0 (blocked) |
| **Authenticated** | 60 req/min | 20 req/min | 10 req/min |
| **Operator** | 120 req/min | 60 req/min | 30 req/min |
| **Service** | 300 req/min | 100 req/min | 50 req/min |

### 5.2 Per-Agent Limits

| Agent Role | Concurrent Tasks | Requests/min | Notes |
|------------|------------------|--------------|-------|
| BENSON (GID-00) | 3 | 30 | Orchestrator |
| CODY (GID-02) | 5 | 50 | Backend heavy |
| SONNY (GID-03) | 5 | 50 | Frontend heavy |
| SAM (GID-06) | 2 | 20 | Security audit |
| DAN (GID-07) | 3 | 30 | DevOps |
| Default | 2 | 20 | Conservative |

### 5.3 Per-Model-Tier Limits (TPM = Tokens Per Minute)

| Model Tier | TPM Limit | Concurrent Requests | Notes |
|------------|-----------|---------------------|-------|
| **Core** (Opus, GPT-5) | 60,000 | 5 | Primary reasoning |
| **Standard** (Sonnet, GPT-4.1) | 100,000 | 10 | Coding tasks |
| **Elevated Risk** | 20,000 | 2 | Experimental models |

### 5.4 Request Size Limits

| Endpoint Family | Max Request Body | Max Response Body |
|-----------------|------------------|-------------------|
| `/modules/*/execute` | 1 MB | 10 MB |
| `/pipelines/*/execute` | 2 MB | 20 MB |
| `/occ/*` | 512 KB | 5 MB |
| `/api/chainboard/*` | 256 KB | 2 MB |

---

## 6. Environment Flags (prod vs dev)

### 6.1 Feature Flags

| Flag | Default (dev) | Default (prod) | Description |
|------|---------------|----------------|-------------|
| `GATEWAY_ALLOW_DYNAMIC_MODULES` | `true` | `false` | Permit `/modules/register` |
| `GATEWAY_ALLOW_OCC_WRITES` | `true` | `true` | Permit OCC mutations |
| `GATEWAY_REQUIRE_AUTH` | `false` | `true` | Enforce AuthN middleware |
| `GATEWAY_REQUIRE_PDO` | `false` | `true` | Enforce PDO verification |
| `GATEWAY_ENFORCE_RATE_LIMITS` | `false` | `true` | Enforce rate limiting |
| `GATEWAY_MODULE_ALLOWLIST` | `*` | `<explicit_list>` | Allowed module names |
| `GATEWAY_CORS_ORIGINS` | `*` | `<trusted_origins>` | CORS origin allowlist |
| `PROOFPACK_REQUIRE_SIGNATURE` | `false` | `true` | Require signed ProofPacks |

### 6.2 Behavior Matrix

| Scenario | dev | prod |
|----------|-----|------|
| Unauthenticated request to `/modules/*/execute` | ⚠️ Allowed (warn) | ❌ 401 Rejected |
| Dynamic module registration | ✅ Allowed | ❌ 403 Rejected |
| Missing PDO on execute | ⚠️ Allowed (warn) | ❌ 400 Rejected |
| Rate limit exceeded | ⚠️ Logged only | ❌ 429 Rejected |
| Unsigned ProofPack export | ✅ Allowed | ❌ 422 Rejected |
| CORS from unknown origin | ✅ Allowed | ❌ Blocked |

---

## 7. Secret Isolation Requirements

### 7.1 Forbidden in LLM Context

The following **MUST NEVER** appear in agent context, prompts, or metadata:

- API keys (OpenAI, Anthropic, etc.)
- Database connection strings
- JWT secrets / signing keys
- `.env` file contents
- Private keys (Ed25519, RSA, etc.)
- Service account credentials
- OAuth client secrets

### 7.2 Redaction Middleware

Before any data reaches `AgentRuntime.prepare_prompt()`:

1. Strip environment variables from context
2. Redact patterns matching `(?i)(api[_-]?key|secret|token|password|credential)`
3. Block file reads from `.env*`, `*.pem`, `*.key` paths
4. Replace matched secrets with `[REDACTED:<type>]`

### 7.3 Audit on Redaction

```json
{
  "event_type": "SECRET_REDACTED",
  "timestamp": "...",
  "context_path": "task.context.env.OPENAI_API_KEY",
  "redaction_type": "api_key",
  "principal": "..."
}
```

---

## 8. Security Acceptance Checklist

This checklist is **machine-verifiable** and **MUST** pass before any merge to `main`.

### 8.1 Gateway Middleware (LAYER enforcement)

```yaml
# gateway_airlock_checks.yaml
checks:
  - id: SEC-GW-001
    name: AuthN middleware present on protected routes
    query: "grep -r '@require_auth' api/ gateway/"
    expect: matches > 0
    severity: CRITICAL

  - id: SEC-GW-002
    name: AuthZ middleware present on elevated routes
    query: "grep -r '@require_permission' api/ gateway/"
    expect: matches > 0
    severity: CRITICAL

  - id: SEC-GW-003
    name: Rate limit middleware present
    query: "grep -r 'RateLimitMiddleware\\|@rate_limit' api/ gateway/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-GW-004
    name: PDO verification on execute endpoints
    query: "grep -r 'verify_pdo\\|require_pdo' api/ gateway/"
    expect: matches > 0
    severity: CRITICAL

  - id: SEC-GW-005
    name: No wildcard CORS in prod config
    query: "grep -r 'allow_origins.*\\*' api/server.py"
    expect: matches == 0 OR gated_by_env_flag
    severity: CRITICAL
```

### 8.2 Secret Isolation

```yaml
  - id: SEC-ISO-001
    name: No hardcoded secrets in source
    query: "grep -rE '(sk-|AKIA|ghp_|xox[baprs]-)[A-Za-z0-9]{20,}' --include='*.py'"
    expect: matches == 0
    severity: CRITICAL

  - id: SEC-ISO-002
    name: Redaction middleware registered
    query: "grep -r 'SecretRedactionMiddleware\\|redact_secrets' tools/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-ISO-003
    name: .env files excluded from agent context
    query: "grep -r '\\.env' tools/agent_loader.py tools/agent_runtime.py"
    expect: matches == 0 OR explicit_block
    severity: HIGH
```

### 8.3 PDO Enforcement

```yaml
  - id: SEC-PDO-001
    name: GatewayPDO required for module execute
    query: "test -f gateway/pdo_schema.py && grep 'PDOOutcome' gateway/"
    expect: matches > 0
    severity: CRITICAL

  - id: SEC-PDO-002
    name: PDO rejection returns 422
    query: "grep -r '422\\|Unprocessable' api/ gateway/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-PDO-003
    name: PDO audit events emitted
    query: "grep -r 'PDO_REJECTED\\|pdo_rejected' api/ gateway/ core/"
    expect: matches > 0
    severity: HIGH
```

### 8.4 Rate Limiting

```yaml
  - id: SEC-RL-001
    name: Per-user rate limits defined
    query: "grep -rE 'per_user|user_limit|RateLimit.*user' api/ gateway/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-RL-002
    name: 429 response on rate limit
    query: "grep -r '429\\|Too Many Requests' api/ gateway/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-RL-003
    name: Rate limit headers in response
    query: "grep -r 'X-RateLimit' api/ gateway/"
    expect: matches > 0
    severity: MEDIUM
```

### 8.5 Audit Trail

```yaml
  - id: SEC-AUD-001
    name: Rejection events logged
    query: "grep -rE 'GATEWAY_REJECTION|AUTH_FAILED|AUTHZ_DENIED|RATE_LIMITED' api/ gateway/ core/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-AUD-002
    name: Audit events include principal
    query: "grep -r 'principal.*id\\|actor.*id' core/occ/"
    expect: matches > 0
    severity: MEDIUM

  - id: SEC-AUD-003
    name: Correlation ID in all responses
    query: "grep -r 'X-Request-Id\\|correlation_id' api/"
    expect: matches > 0
    severity: MEDIUM
```

### 8.6 Environment Gating

```yaml
  - id: SEC-ENV-001
    name: Dynamic modules gated by flag
    query: "grep -r 'GATEWAY_ALLOW_DYNAMIC_MODULES' api/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-ENV-002
    name: PDO requirement gated by flag
    query: "grep -r 'GATEWAY_REQUIRE_PDO' api/ gateway/"
    expect: matches > 0
    severity: HIGH

  - id: SEC-ENV-003
    name: Auth requirement gated by flag
    query: "grep -r 'GATEWAY_REQUIRE_AUTH' api/ gateway/"
    expect: matches > 0
    severity: HIGH
```

---

## 9. Enforcement Timeline

| Phase | Scope | Target Date | Blocker |
|-------|-------|-------------|---------|
| **Phase 1** | PDO schema + validation | Merged | — |
| **Phase 2** | AuthN/AuthZ stubs | Current PR | — |
| **Phase 3** | Rate limiting middleware | +1 sprint | Blocks prod deploy |
| **Phase 4** | Secret redaction | +1 sprint | Blocks agent runtime |
| **Phase 5** | Full audit trail | +2 sprints | Blocks compliance |

---

## 10. References

- [gateway_threat_model.md](gateway_threat_model.md) — Threat register and mitigations
- [gateway/intent_schema.py](../../gateway/intent_schema.py) — GatewayIntent schema
- [gateway/pdo_schema.py](../../gateway/pdo_schema.py) — GatewayPDO schema
- [gateway/validator.py](../../gateway/validator.py) — Intent validation
- [gateway/decision_engine.py](../../gateway/decision_engine.py) — Deterministic decision engine
- [api/server.py](../../api/server.py) — FastAPI gateway (to be hardened)
- [ChainBridge/tools/agent_runtime.py](../../ChainBridge/tools/agent_runtime.py) — Agent orchestration (secret isolation target)

---

**🔴 END — SAM (GID-06) — SECURITY & THREAT ENGINEERING**
