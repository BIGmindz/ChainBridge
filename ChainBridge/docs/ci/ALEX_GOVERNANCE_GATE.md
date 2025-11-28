# ALEX Governance Gate (alex-governance)

## BLUF

ALEX is a deterministic **governance gatekeeper** for ChainBridge flows that touch legal wrappers, digital supremacy, kill‑switch safety, and settlement paths. The GitHub Actions job `alex-governance` (ALEX Governance Gate) must pass on protected branches (including `main`) before merges are allowed.

---

## What ALEX Enforces

**ChainBridge Mantra**

> Speed without proof gets blocked.
> Proof without pipes doesn’t scale.
> Pipes without cash don’t settle.
> You need all three.

If any of **proof**, **pipes**, or **cash** is missing, ALEX must block the flow.

**Governance Rules**

- **Ricardian wrapper state** must be `ACTIVE` (not `FROZEN` or `TERMINATED`).
- **Digital Supremacy** must be `COMPLIANT` or `NEEDS_PROOF` (never `BLOCKED`).
- **Kill-switch** must be `SAFE` (never `UNSAFE`).
- **ALEX responses** must include the required sections:
  - BLUF
  - Issues
  - Applicable Frameworks
  - Governance Checks
  - Analysis
  - Risk Classification
  - Required Controls
  - RACI
  - Final Determination

Any violation of these rules is treated as a **test failure** and therefore a **CI failure**.

---

## Test Locations

Governance is enforced by tests in `tests/agents/`:

- `tests/agents/test_alex_mantra_enforcement.py`
- `tests/agents/test_alex_response_structure.py`

These tests encode the mantra checks, wrapper/supremacy/kill‑switch rules, and ALEX response structure contract.

---

## CI Job: `alex-governance`

- **Workflow file:** `.github/workflows/tests.yml`
- **Job ID:** `alex-governance`
- **Job name:** `ALEX Governance Gate`
- **Command:** `pytest -q tests/agents` (Python 3.11)

Branch protection on `main` requires this job.
If `alex-governance` fails, **the merge is blocked**.

---

## Local Runbook

From the ChainBridge repo root:

```bash
cd /Users/johnbozza/Documents/Projects/ChainBridge-local-repo/ChainBridge
source .venv/bin/activate
pytest -q tests/agents

# or

make test-alex
```

In VS Code:

- Open the Command Palette → **Run Task…**
- Select: `ALEX: Run Governance Tests`

This uses the same command as CI to avoid drift.

---

## When the Gate Fails

1. Open the failing CI job `ALEX Governance Gate` (`alex-governance`).
2. Identify which test(s) in `tests/agents/` failed.
3. Fix the **underlying governance violation** (wrapper/supremacy/kill‑switch state, response structure, or mantra breach) rather than weakening the tests.
4. Re‑run locally:

   ```bash
   source .venv/bin/activate
   pytest -q tests/agents
   ```

5. Push your changes and re‑run the PR CI.

For governance model details, see:

- `docs/SECURITY_AGENT_FRAMEWORK.md` (ALEX Governance Gate – Non‑Negotiable)
- `docs/architecture/REPO_STRUCTURE.md` (Agent Governance Gate section)

---

## Related Docs

- `docs/ci/ALEX_GOVERNANCE_GATE.md` (this file)
- `docs/SECURITY_AGENT_FRAMEWORK.md` – ALEX Governance Gate and agent threat model
- `docs/architecture/REPO_STRUCTURE.md` – Repository layout + Agent Governance Gate location
- `AGENTS 2/` – Canonical prompts and checklists for all agents (including ALEX)

ALEX is not a creative assistant.
ALEX is a deterministic gate that enforces lawful proof, lawful pipes, and lawful cash.
