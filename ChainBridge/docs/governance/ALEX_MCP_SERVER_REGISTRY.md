# ALEX MCP Server Registry

**Purpose:** Canonical registry of all MCP servers approved or proposed for ChainBridge use (ChainBridge core, ChainPay, ChainIQ, ChainSense, and related projects). Every MCP server must be recorded here with scope, auth, owner, and status before agents rely on it.

## Table Schema (fields to populate per MCP server)
- **id:** Short identifier (e.g., `local-tools`, `github-scm`, `chainpay-mcp`).
- **name:** Human-readable name.
- **type:** One of `local-dev | scm | internal-business | external-data | other` (aligns with ALEX_MCP_POLICY_V1 classes).
- **scope:** What the MCP can access/do (files, repos, APIs, environments, read vs write).
- **auth:** How it authenticates (none | PAT | OAuth | local | service-token | other).
- **owner:** Responsible human/agent (e.g., `Benson (GID-00)`, `Dan (GID-07)`).
- **status:** `proposed | approved | deprecated | disabled`.
- **notes:** Risk constraints, environment bounds, onboarding PAC link/ID.

## Registry (examples — replace with real entries)
| id           | name                      | type       | scope                                    | auth  | owner             | status   | notes                                           |
|--------------|---------------------------|------------|------------------------------------------|-------|-------------------|----------|-------------------------------------------------|
| example-dev  | Example Local Dev MCP     | local-dev  | Local project files (read-only)          | none  | Benson (GID-00)   | proposed | Example only; replace with real MCPs.           |
| example-scm  | Example GitHub SCM MCP    | scm        | Repo metadata + PRs (no secrets)         | PAT   | Dan (GID-07)      | proposed | Example; requires ALEX onboarding PAC before use. |

*The above rows are examples; real MCP servers must be added via an ALEX PAC and recorded here with accurate status/auth/scope.*

## Onboarding & Change Protocol
- Follow `docs/governance/ALEX_MCP_POLICY_V1.md` for the checklist (purpose/owner, scope, auth, failure modes, logging/audit).
- Every new MCP server must have an ALEX PAC ID for its onboarding and must be entered here with `status=approved` before production/staged use.
- Any scope expansion or decommissioning must update this registry and be logged under GID-08 in `docs/governance/AGENT_ACTIVITY_LOG.md`.
