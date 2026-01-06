# ChainBridge Platform

ChainBridge is the freight intelligence platform that closes enterprise logistics deals. It unifies shipment health (ChainIQ), settlements (ChainPay), the Operator Console (ChainBoard), and upcoming ChainSense insights behind a single API gateway.

---

## 🚀 V1.0.0 Quick Start (One Command)

```bash
./start_chainbridge.sh
```

That's it. The script will:
- ✅ Check Kill Switch safety status
- ✅ Activate Python virtual environment
- ✅ Start API Server (Port 8000)
- ✅ Start UI Dashboard (Port 5173)
- ✅ Open ChainBoard in your browser
- ✅ Clean shutdown on `Ctrl+C`

### V1.0.0 Core Features

| Feature | Description |
|---------|-------------|
| 🧠 **Benson Orchestrator** | Constitutional CPU with PDO governance |
| 🛑 **Kill Switch** | EU AI Act Art. 14 compliant emergency stop |
| 👁️ **God-View Dashboard** | Real-time system status, agents, policies |
| 📜 **ChainDocs Policy Engine** | Immutable policies with SHA256 hash citations |
| 🤖 **Agent Swarm Factory** | 12-agent registry with spawn/delegate capability |
| 🔑 **Single-Command Launchpad** | Zero-config startup with clean shutdown |

> **See [V1_RELEASE_NOTES.md](V1_RELEASE_NOTES.md) for complete release details.**

---

## Quickstart (Manual Setup)

1. **Prepare Python + Node toolchain**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-runtime.txt
   ```
2. **Start the backend gateway**
   ```bash
   ./scripts/dev/run_api_gateway.sh
   ```
3. **Launch the Operator Console**
   ```bash
   ./scripts/dev/run_chainboard.sh
   ```
4. Visit `http://localhost:5173` (UI) with `VITE_API_BASE_URL` defaulting to `http://localhost:8001`.

> Need everything at once? Run both services with the VS Code task **“Start ChainBridge Stack”** (see `.vscode/tasks.json`).

## Services at a Glance

| Service | Path | Port | Description |
| ------- | ---- | ---- | ----------- |
| API Gateway | `services/api-gateway/` | 8001 | FastAPI surface fanning out to ChainIQ, ChainPay, ChainSense |
| ChainBoard UI | `services/chainboard-service/` | 5173 | Operator Console (React + Vite) |
| ChainIQ | `services/chainiq-service/` | 8102 | Shipment health, risk scoring, intelligence feeds |
| ChainPay | `services/chainpay-service/` | 8103 | Settlement plans, cash flow visibility |
| ChainSense | `services/chainsense-service/` | 8104 | External signal ingestion (WIP) |

Shared code lives in `platform/`, infrastructure in `infra/`, and all historical crypto automation has been quarantined in `legacy/bensonbot/`.

## Documentation Map

- Structure: `docs/architecture/REPO_STRUCTURE.md`
- Operator Console: `docs/product/OPERATOR_CONSOLE_OVERVIEW.md`
- ChainIQ: `docs/product/CHAINIQ_OVERVIEW.md`
- ChainPay: `docs/product/CHAINPAY_OVERVIEW.md`
- Demo flows: `scripts/demo/` (see readmes inside)

Each service folder includes a README with deeper setup, API references, and links to its tests under `tests/services/`.

## Developer Experience

- **Scripts:** One-command launchers live under `scripts/dev/` and are mirrored as VS Code tasks.
- **VS Code:** Recommended extensions + settings are in `.vscode/`. Tasks include `Start API Gateway`, `Start ChainBoard UI`, and `Start ChainBridge Stack`.
- **Testing:**
  - `pytest tests/api` for gateway contracts
  - `pytest tests/services/<name>` for service checks
  - `pytest tests/e2e` for full stack flows
- **Formatting & linting:** Python via `ruff`, TypeScript via `npm run lint` inside each service.

### Agent Safety & Governance

ChainBridge uses ALEX as a gatekeeper for flows that touch legal, risk, and settlement logic.

- Governance tests live in `tests/agents/`.
- CI job `alex-governance` (ALEX Governance Gate) must pass on every PR.
- Branch protection on `main` requires this job; if it fails, the merge is blocked.

This ensures:

- The ChainBridge mantra is always enforced.
- Ricardian wrapper, digital supremacy, and kill-switch states are honored.
- ALEX outputs follow a strict, auditable structure.

## Legacy & What to Ignore

The old BensonBot trading stack now lives under `legacy/bensonbot/`. Treat it as read-only history—do not copy code or dependencies back into the platform. If a capability matters, reimplement it inside `platform/` or an appropriate service with a modern review.

Build fast, prove the story, keep the pipes clean.
