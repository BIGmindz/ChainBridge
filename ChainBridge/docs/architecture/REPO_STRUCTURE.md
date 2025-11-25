# ChainBridge Repository Structure

This document captures the current layout after creating a dedicated legacy area for historical BensonBot code and grouping docs by focus area.

## Core Platform
- `api/`: FastAPI operator / ChainBridge backend.
- `chainboard-ui/`: Operator Console React frontend.
- `chainiq-service/`: ChainIQ risk & intel engine.
- `chainpay-service/`: ChainPay settlements engine.
- `core/`: Shared domain logic that current services import.
- `tools/`: Agent framework, CLIs, and shadow pilot tooling.
- `scripts/`: Seeders, demo helpers, migrations utilities.
- `tests/`: API + service + intel test suites.
- `docs/`: Documentation grouped into `architecture/`, `product/`, and `ops/`.
- `.github/`: CI configuration (kept at repo root per constraint).

## Legacy Areas (BensonBot / Trading Engine)
- `legacy/legacy-benson-bot/`: Historical BensonBot trading engine content, moved from the repo root into `legacy/`.
- Import check: `rg "legacy-benson-bot"` and `rg "benson" core legacy-benson-bot tools tests` returned no references inside current services, so the move does not affect api/ or ChainPay/ChainIQ.

## Additional Notes
- Runtime artifacts (`*.db`, `cache/`, coverage outputs) remain at root for now; consider relocating to a future `var/` with gitignore rules in a follow-up.
- If any shared utilities emerge inside `legacy/legacy-benson-bot/`, extract them into `core/` before deleting legacy paths.
- Documentation entry points now live under `docs/architecture/` (structure and index), `docs/product/` (milestones and playbooks), and `docs/ops/` (operator/runbook materials).
- Root `PROJECT_CHECKLIST.md`, `PROJECT_STATUS_SUMMARY.md`, and `M02_QUICK_REFERENCE.md` are stubs; canonical content is under `docs/product/` and enforced by `scripts/ci/check_docs_canonical.py`.

### ALEX Gateway (Runtime Governance Firewall)

- Location: `api/agents/alex_gateway.py`
- Responsibilities:
  - Enforces ChainBridge mantra (proof/pipes/cash)
  - Validates wrapper/supremacy/kill-switch states
  - Validates required ALEX output structure
  - Raises hard failures on governance violations to block unsafe flows

## Agent Governance Gate

- Tests:
  - `tests/agents/test_alex_mantra_enforcement.py`
  - `tests/agents/test_alex_response_structure.py`
  - `tests/agents/test_alex_chainpay_integration.py`
  - `tests/agents/test_alex_response_contract.py`
  - `tests/agents/test_alex_gateway.py`
- CI Job:
  - `alex-governance` (ALEX Governance Gate) in `.github/workflows/tests.yml` and mirrored in `.github/workflows/agent_ci.yml`

These enforce:

- ChainBridge mantra:
  - Speed without proof gets blocked.
  - Proof without pipes doesn’t scale.
  - Pipes without cash don’t settle.
  - You need all three.
- Ricardian wrapper rules (ACTIVE vs FROZEN/TERMINATED).
- Digital supremacy rules (COMPLIANT / NEEDS_PROOF vs BLOCKED).
- Kill-switch rules (SAFE vs UNSAFE).
- ALEX response structure (BLUF, Issues, Frameworks, Governance, Analysis, Risk, Controls, RACI, Final Determination).

**Branch protection** on `main` requires the `alex-governance` job to pass.
If this gate fails, no merges are allowed.

## Conventions

- `docs/architecture/` – All architecture diagrams and system design docs.
- `docs/product/` – Product narratives, project checklists, sprint quick references.
- `docs/ops/` – Runbooks, operational SOPs, deployment guides (if present).
- `docs/ci/` – CI and governance documentation (including ALEX Governance Gate).
- `AGENTS 2/` – Canonical AI agent prompts and checklists.
- `AGENTS/` – Deprecated; historical only.
- `legacy/legacy-benson-bot/` – Quarantined legacy trading engine; do not import.
