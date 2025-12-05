# ALEX MCP Governance Policy (V1)

**Owner:** GID-08 ALEX — Governance & Alignment Engine

## 1. What MCP Means for ChainBridge

The Model Context Protocol (MCP) is how ChainBridge agents call tools in a standardized way from VS Code / Copilot Chat.

In this context, an MCP server may provide:
- Filesystem access (read/write within the repo).
- Terminal execution.
- HTTP requests to services (local or remote).
- Integrations with third-party systems (GitHub, ChainPay API, ChainIQ, XRPL, etc.).

This policy defines how MCP servers are introduced, reviewed, and removed.

## 2. MCP Server Classes

We categorize MCP servers used with ChainBridge as:

1. **Local Dev Tools**
   - Filesystem browsers, search tools, code indexers.
   - Scope: The ChainBridge workspace and related project directories.

2. **SCM & Collaboration Tools**
   - GitHub PR/issue tools, code review helpers.
   - Scope: Repositories under the BIGmindz / ChainBridge organizations.

3. **Internal Business Tools**
   - ChainPay settlement gateway, ChainIQ scoring API, internal ChainBridge services.
   - Scope: Well-defined internal APIs with authentication.

4. **External Data Tools**
   - Web research, XRPL explorers, external price feeds.
   - Scope: Public APIs and websites.

## 3. Onboarding Checklist for a New MCP Server

Before enabling a new MCP server in VS Code, the following MUST be answered in a PAC (typically owned by ALEX + the requesting agent):

1. **Purpose & Owner**
   - Which GID is requesting this MCP server (Cody, Sonny, Pax, etc.)?
   - What concrete use cases does it unlock (tests, deployments, research, etc.)?

2. **Scope & Authority**
   - What resources can the MCP server read or modify?
   - Which repositories, APIs, or environments are in-bounds vs out-of-bounds?

3. **Authentication & Secrets**
   - How are credentials provided (env vars, secrets store, local config)?
   - Are secrets ever exposed to the MCP server output or logs?
   - Are `.env` and other sensitive files protected per `ALEX_TOOL_GOVERNANCE_V1.md`?

4. **Failure Modes & Misuse**
   - What happens if the MCP server misbehaves (rate limits, bad responses, security issues)?
   - Can it exfiltrate data or write to production systems?

5. **Logging & Audit**
   - Will usage be visible in code reviews, logs, or WRAPs?
   - How will ALEX/Benson audit its impact over time?

## 4. Allowed vs Disallowed Capabilities

### 4.1 Allowed (With Review)

- Read-only repo access (file search, code navigation, symbol lookup).
- Running tests, linters, and scripts within the ChainBridge workspace (e.g., `make iq-tests`, `pytest`).
- Hitting **local** ChainBridge services on developer machines (e.g., `http://localhost:8000/api/...`) for testing.
- Accessing internal APIs in **sandbox or staging** environments, not production, unless explicitly approved.

### 4.2 Disallowed (Without Special Review)

- Arbitrary external HTTP calls that may exfiltrate secrets or proprietary code.
- Direct access to production databases or payment rails.
- Commands or requests that modify cloud infrastructure (e.g., `kubectl`, cloud CLIs) without a specific PAC.

Any MCP server requiring these capabilities must ship with a **dedicated ALEX PAC** and explicit Benson sign-off.

## 5. Periodic Review & Decommissioning

ALEX should coordinate a recurring (e.g., quarterly) review of MCP servers:

- **Inventory:**
  - List all active MCP servers configured in the workspace.
  - Classify them by the categories above.

- **Assess:**
  - Are they still needed?
  - Has their scope expanded beyond the original PAC?

- **Adjust or Remove:**
  - Tighten their configuration if they now pose higher risk.
  - Decommission and remove them from VS Code / settings if unused.

Each review should result in **at least one bullet** logged under GID-08 in `AGENT_ACTIVITY_LOG.md`.

## 6. Template for MCP Onboarding PAC

When adding a new MCP server, use a PAC that includes:

- **Agent Header** (who is requesting it and why).
- **Context & Goal** (what problem it solves).
- **Constraints & Guardrails** (environments, secrets, data boundaries).
- **Tasks & Plan** (steps to configure and validate).
- **QA & Acceptance** (tests that must pass, e.g., only hitting staging).
- **WRAP** (what was enabled, and where the config lives).

## 7. Residual Risks (V1)

1. **Hidden Capabilities**
   - Risk: An MCP server exposes more power than documented (e.g., write access to paths assumed read-only).
   - Mitigation: Review MCP server documentation; test in a constrained environment; treat unknown capabilities as high-risk.

2. **Secrets Exposure**
   - Risk: MCP interactions accidentally log or transmit secrets.
   - Mitigation: Keep `.env` and secrets out of MCP read paths where possible; never paste secrets into chat; prefer local environment variables.

3. **Scope Creep Over Time**
   - Risk: As MCP servers evolve, they gain new functions without corresponding governance updates.
   - Mitigation: Enforce periodic ALEX reviews and require updated PACs for any scope expansion.
