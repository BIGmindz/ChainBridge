# Agent Router Spec

## Agents
- **Benson CTO** – Orchestrator; inspects tasks and emits PACs.
- **Cody** – Backend Engineer.
- **Sonny** – Frontend Engineer.
- **DevOps Dan** – DevOps / Platform Engineer.
- **SecOps Sam** – Security / Compliance.
- **ML Mira** – ML / Signals.

## Routing Rules

### Path-Based Routing
- **Cody** owns:
  - `ChainBridge/api/**`
  - `ChainBridge/chainpay-service/**`
  - `ChainBridge/chainiq-service/**`
  - `ChainBridge/app/**`
  - `ChainBridge/scripts/**`
  - `ChainBridge/tools/**`
  - `ChainBridge/tests/**` (Python)
- **Sonny** owns:
  - `ChainBridge/chainboard-ui/**`
- **DevOps Dan** owns:
  - `.github/workflows/**`
  - `Dockerfile*`
  - `docker-compose.yml`
  - `k8s/**`
  - `Makefile*`
  - `scripts/dev/**`
- **SecOps Sam** owns:
  - Security docs (e.g., `docs/SECURITY_AGENT_FRAMEWORK.md`)
  - Auth/secrets/credential management paths
- **ML Mira** owns:
  - ML/signal areas (`ml_models`, `modules`, `signals`, `tracking`, etc.)
  - Model-heavy ChainIQ/risk pipelines

### Error-Type Routing
- Ruff/black/isort/pytest/logic errors (Python) → **Cody**
- React/TS/Vitest errors → **Sonny**
- CI / GitHub Actions / Docker / k8s → **DevOps Dan**
- Security posture / auth / secrets / vuln remediation → **SecOps Sam**
- ML training / inference / features / metrics → **ML Mira**
- Docs/governance/agent framework/branch policies → **ALEX + Docs**

## Benson CTO Behavior
- Inspects paths and error type for each task.
- Selects the appropriate agent(s) per routing tables.
- Emits one or more PAC blocks (Cody PAC, Sonny PAC, DevOps Dan PAC, etc.).
- Always enforces the ChainBridge mantra and the ALEX Governance Gate.
