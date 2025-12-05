# ALEX Tool Governance Policy (V1)

**Owner:** GID-08 ALEX — Governance & Alignment Engine

## 1. Purpose & Scope
This document defines how VS Code / GitHub Copilot tools, terminals, file edits, and MCP servers are governed for all ChainBridge projects (ChainBridge core, ChainPay, ChainIQ, ChainSense, and future crypto initiatives).

It focuses on:
- Auto-approve behavior for Copilot tools in VS Code.
- Risk-based rules for terminal commands and file edits.
- Guardrails for secrets and environment files.
- A practical baseline Benson can hand to Cody, Sonny, Pax, Maggie, Dan, etc.

## 2. Tool Categories
We classify tools used via Copilot Chat and VS Code into:

1. **Terminal commands**
   - Shell commands executed in the workspace (e.g., `ls`, `pytest`, `make iq-tests`).
2. **File edits**
   - Copilot or tools modifying repository files (code, docs, configs).
3. **MCP tools**
   - Filesystem, terminal, HTTP, GitHub, ChainPay, XRPL, and other protocol-based servers.

## 3. Risk Levels
Each action/tool is assigned a risk level:

- **Low Risk**
  - Read-only inspection of project state.
  - Examples: `ls`, `pwd`, `git status -sb`, `cat` non-secret files, `ruff --version`.

- **Medium Risk**
  - Write operations to project files under version control.
  - Examples: `pytest`, `ruff`, `make test`, `make lint`, code generation/edits in `src/`, `chainpay-service/`, `chainiq-service/`, `chainboard-ui/`, and `docs/`.

- **High Risk**
  - Commands that can modify or delete data, change permissions, or interact with external networks.
  - Examples: `rm`, `mv` (destructive renames), `chmod`, `chown`, `curl`/`wget` to arbitrary hosts, `docker` commands, `kubectl`, `psql` against live DBs.

- **Forbidden for Auto-Approve**
  - Anything that can damage the system, exfiltrate secrets, or operate outside the project scope **must never** be auto-approved by Copilot.
  - These commands may only be run when **manually typed and executed by the human**.

## 4. Auto-Approve Policy

### 4.1 Global Default
- `chat.tools.global.autoApprove` **MUST remain `false`**.
- Auto-approve is configured explicitly per tool class (terminal, edits, MCP) with **least privilege by default**.

### 4.2 Terminal Auto-Approve Rules

| Command pattern / type                 | Risk   | Auto-approve | Notes |
|----------------------------------------|--------|--------------|-------|
| `pwd`, `ls`, `ls -la`                  | Low    | Yes          | Any workspace path. |
| `git status`, `git status -sb`         | Low    | Yes          | Read-only repo status. |
| `cat` non-secret project files         | Low    | Yes          | Excludes .env and secrets. |
| `pytest`, `python -m pytest ...`       | Medium | Optional     | Allowed when running tests under repo root. |
| `make test`, `make lint`, `make iq-tests` | Medium | Optional  | Safe project automation; may be auto-approved. |
| `ruff`, `ruff check`, `ruff format`    | Medium | Optional     | Linting/formatting only. |
| `rm`, any `rm -rf`                     | High   | Never        | Must **never** be auto-approved. Human-only. |
| `chmod`, `chown`, `sudo`               | High   | Never        | Forbidden for auto-approve. |
| `curl`, `wget` to arbitrary URLs       | High   | Never        | Must always prompt; human inspects URL. |
| `docker *`, `kubectl *`                | High   | Never        | Infra-impacting; human-only. |

**Rules:**
- Low risk commands **may** be configured as `autoApprove: true`.
- Medium risk commands may be `autoApprove: true` if they are **idempotent, project-scoped, and non-destructive** (tests, linters, formatters). Benson may tune on/off per repo.
- High risk and destructive commands are **never** auto-approved. Copilot must **always prompt** and the user must manually run them.

### 4.3 File Edit Auto-Approve Rules

- Code and doc edits inside the repo may be auto-approved **only** when:
  - They touch **tracked project files**, and
  - The user has context that the change is safe (e.g., refactor, test file update, doc edit).
- Edits to certain paths **must never** be auto-approved:
  - `.env`, `.env.*` (any environment file).
  - `config/*.secrets.*`, `*.pem`, `*.key`, credentials or token files.
  - Global system paths (`/etc/*`, `/usr/*`, home directory dotfiles not part of the repo).

**Secrets & Environment Files:**
- `.env` and `.env.*` editors must always **prompt**; suggestions can be shown but never auto-applied.
- Any AI-suggested change to secrets or env files must be:
  - Human-initiated.
  - Manually edited by the user.
  - Logged in `docs/governance/AGENT_ACTIVITY_LOG.md` if the AI suggestion influenced the change.

## 5. Example `settings.json` Snippet (Non-Binding Template)

The following VS Code Copilot Chat settings block is a **template** to illustrate ALEX’s policy. It must be adapted and applied by a human (Benson/Cody), not auto-written by ALEX.

```jsonc
{
  "chat.tools.global.autoApprove": false,
  "chat.tools.terminal.autoApprove": {
    // Low-risk read-only commands
    "pwd": true,
    "ls": true,
    "ls -la": true,
    "git status": true,
    "git status -sb": true,

    // Medium-risk but safe project commands (opt-in)
    "pytest": true,
    "python -m pytest": true,
    "make test": true,
    "make lint": true,
    "make iq-tests": true,
    "ruff": true,
    "ruff check": true,

    // Explicit denials (never auto-approve)
    "rm": false,
    "rm -rf": false,
    "chmod": false,
    "chown": false,
    "sudo": false,
    "curl": false,
    "wget": false,
    "docker": false,
    "kubectl": false
  },
  "chat.tools.edits.autoApprove": {
    "*": true,
    ".env": false,
    ".env.*": false
  }
}
```

> Note: Command keys are illustrative. Actual keying and pattern support may vary; when in doubt, treat any unclassified command as **not auto-approved**.

## 6. Agent Responsibilities

- **Benson (GID-00)**
  - Owns final sign-off for global tool governance and auto-approve profiles.
  - Reviews ALEX’s proposals before broad rollout.

- **ALEX (GID-08)**
  - Authors and maintains this policy.
  - Logs any changes to tool/auto-approve behavior in `AGENT_ACTIVITY_LOG.md`.
  - Proposes updates when new tools or MCP servers are introduced.

- **Cody, Sonny, Pax, Maggie, Dan, etc.**
  - Request new tool privileges or exceptions via PACs.
  - Follow this policy when configuring local `settings.json` or project-level settings.
  - Ensure that any exceptions are documented in WRAPs and logged in the activity log.

## 7. Change Management & Logging

- Any change to:
  - Global auto-approve behavior,
  - Terminal allowlist/denylist,
  - Edit auto-approve rules for sensitive files,
  **must** be logged under GID-08 in `docs/governance/AGENT_ACTIVITY_LOG.md`.

- Recommended log format:
  - `YYYY-MM-DD – Updated tool governance; files: docs/governance/ALEX_TOOL_GOVERNANCE_V1.md; tests: none (docs-only).`

## 8. Residual Risks (V1)

1. **Misclassified Commands**
   - Risk: A command is treated as low/medium risk when it can have high impact (e.g., a custom script that deletes data).
   - Mitigation: Keep `chat.tools.global.autoApprove=false` and require PAC review for expanding allowlists.

2. **Local Environment Drift**
   - Risk: Different machines have different `settings.json` and tool behaviors.
   - Mitigation: Document the agreed template here and in team onboarding; periodically align via ALEX-led governance reviews.

3. **Future Tool Types**
   - Risk: New tool categories (e.g., remote MCP servers) bypass this policy.
   - Mitigation: Any new tool type must ship with an ALEX PAC updating this doc and `ALEX_MCP_POLICY_V1.md` before being widely enabled.

## 9. Appendix: Baseline VS Code `settings.json` Governance Snippet

Use this as the default stance unless superseded by a newer ALEX PAC. Apply manually in VS Code; do not auto-write it. Keep it consistent with the MCP registry and the allowlist/denylist rules above.

```jsonc
{
  // Global: never blanket auto-approve tools
  "chat.tools.global.autoApprove": false,

  // Manage allowlists explicitly; do not inherit defaults blindly
  "chat.tools.terminal.ignoreDefaultAutoApproveRules": true,

  // Edits: allow project files; never auto-approve env/secret edits
  "chat.tools.edits.autoApprove": {
    "**/*": true,
    "**/.vscode/*.json": false,
    "**/.env": false,
    "**/.env.*": false
  },

  // Terminal: narrow allowlist for safe read-only commands
  "chat.tools.terminal.autoApprove": {
    "pwd": true,
    "ls": true,
    "ls -la": true,
    "git status": true,
    "git status -sb": true,

    // Destructive or networked commands must not be auto-approved
    "rm": false,
    "rm -rf": false,
    "curl": false,
    "wget": false,
    "chmod": false,
    "chown": false,
    "sudo": false,
    "docker": false,
    "kubectl": false
  }
}
```

Note: Treat any command not explicitly allowlisted as “prompt required.” Keep `.env` and secrets edits human-only. Align any MCP usage with `ALEX_MCP_POLICY_V1.md` and record new servers in `ALEX_MCP_SERVER_REGISTRY.md`.
