# Agent Framework + Agent Health Threat Model

## 1. Scope

In-scope components:

- `AGENTS/` directory content and prompt files checked into repository.
- Validation + runtime tools: `agent_runtime`, `agent_validate`, `agent_cli`.
- Backend `GET /api/agents/status` endpoint and any caching layers.
- CI workflow (`agent_ci.yml`) that exports `agents_export.json` and uploads the `agent-prompts-json` artifact.

Out-of-scope: downstream customer APIs, non-agent microservices, third-party LLMs (covered elsewhere).

## 2. Assets

- **Agent prompts / configs:** Proprietary strategies, contact data, system instructions.
- **Validation results:** Indicates which roles are production-ready; valuable intel for abuse.
- **CI artifacts:** `agents_export.json` contains entire prompt payload; must stay internal.
- **API responses:** `/api/agents/status` reveals operational readiness counts and role names.

## 3. Threats

### Information Leakage

- Unauthorized download of `agents_export.json` reveals proprietary prompts.
- Developers accidentally log prompts or validation failures to public logs/observability tools.
- Readiness template posted externally with internal role names and status.

### Endpoint Exposure

- `/api/agents/status` exposed publicly without auth → attacker enumerates invalid roles to target.
- Rate-limit bypass on status endpoint leading to scraping and correlation with release cadence.

### Artifact Exposure

- CI artifacts retained indefinitely on public runners or shared buckets without ACLs.
- Artifact tampering or swapping after upload if storage lacks integrity checks/SSE.

### Integrity

- Malicious change to files under `AGENTS/` introduces backdoors or poisoned prompts.
- Compromised validation tooling (`agent_validate`) returns green despite missing files.
- CI pipeline manipulated so that uploaded artifact does not match validated commit.

## 4. Controls & Recommendations

### MUST

- Require auth (OIDC or session) for `/api/agents/status`; restrict to internal networks or VPN.
- Enforce branch protection + code owners for `AGENTS/` and `tools/` directories; mandate two-person review.
- Configure CI artifact storage with scoped credentials, short TTL, and server-side encryption; disable public links.
- Monitor and alert on validation pipeline failures; treat silent success with zero counts as incident.

### SHOULD

- Sign `agents_export.json` with checksum stored alongside artifact; verify before consumption.
- Implement audit logging on validation tools showing who triggered runs and what roles changed.
- Apply rate limiting + anomaly detection on `/api/agents/status` to flag scraping.
- Run dependency scanning on `agent_runtime` / `agent_validate` packages to prevent tampering.

### NICE-TO-HAVE

- Encrypt sensitive prompt sections at rest even inside repo (e.g., sealed secrets) with automated decrypt in CI.
- Provide per-role validation timestamps + actor in API for better forensics.
- Mirror status data into SIEM to correlate with other security events.

## 5. Environment Strategy

### Local Development

- Allow verbose logging for debugging but redact prompts before emitting to console.
- Developers may run `agent_cli` with personal credentials; ensure `.env` is gitignored and secrets rotated regularly.
- Artifacts generated locally must stay on encrypted disks; do not upload to personal cloud drives.

### Staging

- `/api/agents/status` accessible only via staging VPN or SSO; logs scrubbed of prompt payloads.
- Retain CI artifacts for limited duration (≤14 days) for regression analysis.
- Enable feature flags to test UI without exposing real production prompts.

### Production

- Endpoint sits behind API gateway with authentication, network ACLs, and WAF rules.
- Artifacts stored in restricted bucket, versioned, with automatic expiration (≤30 days) and access logging enabled.
- Logging level set to warn/error; prompts never logged. Only aggregate counts emitted to monitoring systems.
- Run periodic integrity scans on `AGENTS/` repo to detect unauthorized prompt changes (e.g., Git signing, checksum pipeline).
