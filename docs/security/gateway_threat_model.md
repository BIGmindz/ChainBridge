# ChainBridge Gateway Threat Model (Canonical v1)

**Status:** CANONICAL
**Version:** v1
**Authoring Agent:** Sam (GID-06), Security & Threat Engineer, Color: Dark Red
**Applies To:** ChainBridge Gateway; PDO / ProofPack lifecycle; OCC / Operator Control; CI / Governance Enforcement
**Governance:** CCDS v1 (ENFORCED); CALP v1 (ENFORCED); Gateway Contract v1 (REFERENCED)
*Security without provenance is a governance risk; this model is anchored to the canonical gateway contract.*

## Scope & Assets
- Gateway: FastAPI surface at `/`, `/health`, module/pipeline execute endpoints, OCC routers (`/occ/*`), ChainBoard projection layer (`/api/chainboard`).
- PDO lifecycle: OCC artifact + audit events + ProofPack generation/verification (integrity manifest, optional Ed25519 signature) stored via `ArtifactStore` (JSON persistence at `data/artifacts.json` by default).
- Adjacent services: ChainBoard UI (read-only projections), ChainIQ/ChainPay connectors, CI governance (ALEX gate, tests).

## Assumptions & Trust Boundaries
- Gateway Contract v1 is mandatory for all gateway traffic and governs request handling.
- No execution path exists outside the Gateway; all module/pipeline execution is mediated by gateway controls.
- PDO / ProofPack integrity is enforced by middleware (hash + signature validation on emit and read).

## Trust Boundaries
- External callers → Gateway (public HTTP surface, currently unauthenticated, wide CORS).
- Gateway → OCC store (in-memory + JSON persistence) and ProofPack generation.
- Gateway → downstream modules/pipelines that execute arbitrary Python modules.
- CI/CD → protected branches (ALEX governance tests, lint/tests).

## Bypass Vectors
1) Prompt injection
- Surface: Any module that ingests untrusted text (e.g., sentiment, future LLM-backed modules), ChainBoard projections reused by operators.
- Risk: Malicious payload steers model or operator workflow; could taint ProofPack notes or audit details.
- Path: Unvalidated payload in `artifact.payload`, `AuditEvent.details`, `ProofPack.notes` rendered to staff or LLMs.

2) Direct API calls
- Surface: `/modules/*`, `/pipelines/*`, `/occ/*`, `/api/chainboard/*` lack auth and rate limits; CORS set to `*`.
- Risk: Unauthorized module execution (arbitrary code in modules), mass artifact creation/deletion, ProofPack generation with forged notes, event stream scraping.
- Path: Direct HTTP to gateway bypassing UI; host header switching could target non-prod stores if same network.

3) CI bypass
- Surface: Local runs skipping `make lint` / `pytest`, forced merge of failing ALEX gate, or editing pipeline to skip governance tests.
- Risk: Deploying modules/pipelines without guardrails; weakened ProofPack signature logic; disabled artifact persistence.
- Path: Branch protection misconfig, ad-hoc deployments, or tampering with CI config/tests.

## Error Severity Model
- Fatal security errors: compromise trust/integrity or uncontrolled execution. Examples: unsigned/incorrect ProofPack hashes, missing signature verification where required, arbitrary module execution without auth, tampering with audit/event logs, disabled ALEX governance in release branch, CORS allowing credentialed cross-site without auth checks.
- Recoverable security errors: handled and observable; execution can halt safely. Examples: ProofPack generation fails but logs event and returns 500; malformed artifact payload rejected with 4xx; SSE stream drops but reconnects; rate-limit block.

## Mitigations
- Gateway-only execution paths
  - Require authN/Z on gateway (JWT/OPA) before `/modules/*`, `/pipelines/*`, `/occ/*`; deny direct store access.
  - Enforce allowlist of module names and pipeline definitions server-side; disable dynamic module path registration in prod (`ModuleManager.load_module`).
  - Add per-route rate limits and input size caps; reject execution without `Content-Type: application/json`.

- Signature / hash validation (ProofPack / PDO integrity)
  - Enforce `IntegrityManifest.is_signed` for prod exports; reject unsigned ProofPacks when `env=prod`.
  - Verify manifest hash + signature on fetch/verification endpoints; persist verification result in audit log.
  - Rotate `key_id` and keep public keys pinned; include manifest hash in any external download URLs.

- Prompt injection hardening
  - Treat `artifact.payload`, `AuditEvent.details`, `ProofPack.notes` as untrusted; store and render as text with escaping; strip HTML/JS.
  - For LLM/analytic modules, inject system prompt shields and apply schema validation; block tool calls that try to reach network or filesystem.

- Direct API call controls
  - Lock CORS to trusted origins; require auth headers; add IP allow/deny lists for ops endpoints.
  - Add HMAC request signing for machine clients hitting `/occ/*` and ProofPack generation.
  - Log and alert on creation/update/delete on artifacts and on ProofPack regeneration; include actor identity in audit events.

- CI/governance protections
  - Keep ALEX governance tests required on `main`; prevent `pytest -k 'not agents'` in CI by pinning test selection.
  - Sign release artifacts / container images; verify in deploy pipeline (fail closed on mismatch).
  - Block merges that change `ArtifactStore` persistence path or disable ProofPack signing without security review.

## Threat Register
| ID | Threat | Vector | Impact | Likelihood | Mitigations | Status |
| -- | ------ | ------ | ------ | ---------- | ----------- | ------ |
| T1 | Prompt injection taints PDO/ProofPack | Untrusted text in payload/notes/events | Operator/LLM compromise, bad decisions | Medium | Escape+validate inputs; prompt shields; audit logging | Open |
| T2 | Unauthorized module execution | Direct calls to `/modules/*` | Remote code exec via custom modules | High | AuthZ; module allowlist; rate limits; disable dynamic loads | Open |
| T3 | Unauthorized OCC mutation | Direct calls to `/occ/*` | Artifact tamper, fake audit trail | High | AuthZ; HMAC signing; audit alerts; integrity checks | Open |
| T4 | Unsigned or forged ProofPack | Missing signature verify | Integrity loss of PDO evidence | Medium | Require signatures in prod; verify on read; key rotation | Open |
| T5 | CI governance bypass | Skip ALEX/tests or alter CI | Ship insecure pipelines/modules | Medium | Branch protection; pinned CI scripts; review rule for CI changes | Open |
| T6 | Data exfil via SSE | `/api/chainboard/events/stream` | Leak audit events to attacker | Medium | AuthZ+origin pin; per-tenant filtering; rate limits; heartbeat timeouts | Open |

## Recommended Next Steps (near term)
- Add gateway authN/Z middleware and tighten CORS.
- Enforce ProofPack signing + verification in prod; document key rotation.
- Add module/pipeline allowlist and disable runtime `load_module` outside dev.
- Wire HMAC signing + actor identity into `/occ/*` and ProofPack generation; log verification results.
- Keep ALEX governance job required; add CI check to prevent skipping agent/security tests.
