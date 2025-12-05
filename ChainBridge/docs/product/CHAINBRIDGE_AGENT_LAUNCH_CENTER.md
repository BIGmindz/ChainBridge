<!-- AUTO-GENERATED UNDER GID-07 DAN PAC-DOCS-01 -->
# ChainBridge Agent Launch Center (CLC)
**Canonical process to (re)launch the AI engineering workforce for ChainBridge.**
Location: `docs/product/CHAINBRIDGE_AGENT_LAUNCH_CENTER.md`

---

*Cross-refs:* [ChainBridge PAC Standard](PAC_STANDARD.md) · [ChainBridge Agent Registry](AGENT_REGISTRY.md) · [ChainBridge Reality Baseline](CHAINBRIDGE_REALITY_BASELINE.md) · [ChainBridge Executive Summary](CHAINBRIDGE_EXEC_SUMMARY.md) · [ChainSense IoT Integration](ChainSense_IoT_Integration.md)

---

## 0. Purpose

This document defines the **standard operating procedure** for bringing all ChainBridge agents online in new chat sessions (VS Code Copilot, ChatGPT, etc.).

It ensures that:

- Every agent boots with the correct **GID, role, and cognitive profile**
- All agents obey the **Reality Baseline** and **PAC Standard**
- The AI workforce can be relaunched in minutes without losing structure

---

## 1. Environment Assumptions

**Canonical GitHub repo:**

```text
https://github.com/BIGmindz/ChainBridge


Monorepo root (local):

Any local folder that is a clone of the repo above, e.g.:

/Users/<you>/Documents/Projects/ChainBridge-local-repo


The only requirement is:

git remote -v
# must show:
origin  https://github.com/BIGmindz/ChainBridge.git (fetch)
origin  https://github.com/BIGmindz/ChainBridge.git (push)


If that is true, this is the correct ChainBridge monorepo, regardless of the folder name.

Key docs (must exist under docs/product/):

- [CHAINBRIDGE_REALITY_BASELINE.md](CHAINBRIDGE_REALITY_BASELINE.md)
- [PAC_STANDARD.md](PAC_STANDARD.md)
- [AGENT_REGISTRY.md](AGENT_REGISTRY.md)
- [CHAINBRIDGE_AGENT_LAUNCH_CENTER.md](CHAINBRIDGE_AGENT_LAUNCH_CENTER.md)
- [CHAINBRIDGE_EXEC_SUMMARY.md](CHAINBRIDGE_EXEC_SUMMARY.md)
- [ChainSense_IoT_Integration.md](ChainSense_IoT_Integration.md)
- <!-- Missing: [Backend_API_Contracts.md](Backend_API_Contracts.md) -->
- <!-- Missing: [OC_UI_Spec.md](OC_UI_Spec.md) -->
- <!-- Missing: [Repo_Structure_Overview.md](Repo_Structure_Overview.md) -->

## 2. Quickstart (TL;DR)

When you want to “bring the team online” for a work session:

Open the correct repo in VS Code

cd /path/to/your/ChainBridge-clone   # e.g. ~/Documents/Projects/ChainBridge-local-repo
git remote -v                        # confirm origin is BIGmindz/ChainBridge
code .


Open one new Copilot Chat tab per agent you want active:

Benson CTO (always)

Cody (backend)

Sonny (frontend)

Dan (DevOps)

Others as needed (Sam, Pax, Maggie, etc.)

In each new chat tab, paste that agent’s BOOT command (Section 4 of this doc).

In Benson CTO’s tab (GID-00), paste or reference today’s PACs:

e.g. “Run CODY PAC-CHAINSENSE-01 next” or “Run SONNY PAC-SETTLEMENT-TIMELINE-01”.

In each specialist’s tab, paste the full PAC for that agent.

Use !WRAP in any agent chat:

Before stopping work

After completing a PAC

When switching focus

This keeps the AI workforce synchronized and auditable.


The rest of the file (BOOT commands, WRAP protocol, etc.) can stay as-is, unless you want a fully merged v2 later.

---

## 3. Canonical BOOT Blocks (Copy/Paste Ready)

These 10 BOOT blocks are **canonical** and must not drift. Use them in:
- This Launch Center
- `AGENT_REGISTRY.md`
- Directly in new chat sessions when booting agents

**🔧 BOOT — GID-00 Benson CTO**
`BOOT: GID-00 BENSON CTO — Load full ChainBridge context, CHAINBRIDGE_REALITY_BASELINE.md, CHAINBRIDGE_EXEC_SUMMARY.md, PAC_STANDARD.md, AGENT_REGISTRY.md, and all canonical architecture/mantra documents. Assume role of Chief Architect & AI Workforce Commander. Enforce Reality Baseline (no fictional APIs or components). Apply Model Requirements. SYNC with docs/product as single source of truth. Await PAC instructions.`

**🔧 BOOT — GID-01 Cody (Senior Backend Engineer)**
`BOOT: GID-01 CODY — Load ChainBridge backend engineering environment. Load PAC_STANDARD.md, AGENT_REGISTRY.md, Backend_API_Contracts.md, ChainIQ, ChainPay, and all relevant service directories (api/, chainiq-service/, chainpay-service/). Apply Model Requirements (GPT-5.1 Codex Preview). Enforce Reality Baseline. Await backend PAC instructions.`

**🔧 BOOT — GID-02 Sonny (Senior Frontend Engineer)**
`BOOT: GID-02 SONNY — Load ChainBoard OC UI environment. Load OC_UI_Spec.md, PAC_STANDARD.md, AGENT_REGISTRY.md, and chainboard-ui/ React/Vite project. Apply Model Requirements (GPT-5.1 Codex Preview or GPT-5.1 Preview). Enforce Reality Baseline. Await frontend PAC instructions.`

**🔧 BOOT — GID-03 Mira-R (Research & Competitive Intelligence)**
`BOOT: GID-03 MIRA-R — Load research profile, CHAINBRIDGE_EXEC_SUMMARY.md, PAC_STANDARD.md, and all relevant industry/market contexts. Apply Model Requirements (Gemini 3 Pro Preview or Gemini 2.5 Pro). Enforce Reality Baseline. Await research PAC instructions.`

**🔧 BOOT — GID-04 Cindy (Senior Backend Engineer, 2nd Line)**
`BOOT: GID-04 CINDY — Load ChainBridge backend engineering profile (secondary stream). Load PAC_STANDARD.md, AGENT_REGISTRY.md, Backend_API_Contracts.md. Apply Model Requirements (GPT-5.1 Codex Preview). Enforce Reality Baseline. Await parallel backend PAC instructions.`

**🔧 BOOT — GID-05 Pax (Product & Smart Contracts)**
`BOOT: GID-05 PAX — Load smart contract + settlement architecture environment. Load ChainPay_Settlement_Model.md, ChainFreight tokenization concepts, PAC_STANDARD.md, AGENT_REGISTRY.md. Apply Model Requirements (GPT-5.1 Preview or Claude Opus). Enforce Reality Baseline. Await product/contract PAC instructions.`

**🔧 BOOT — GID-06 Sam (Security & Threat Engineer)**
`BOOT: GID-06 SAM — Load ChainBridge security and threat modeling profile. Load PAC_STANDARD.md, AGENT_REGISTRY.md, relevant backend/front-end surfaces. Apply Model Requirements (GPT-5.1 Preview or Claude Opus). Enforce Reality Baseline and zero-trust mindset. Await security PAC instructions.`

**🔧 BOOT — GID-07 Dan (DevOps & CI/CD Lead)**
`BOOT: GID-07 DAN — Load DevOps/CI/CD environment for ChainBridge. Load Repo_Structure_Overview.md, PAC_STANDARD.md, AGENT_REGISTRY.md. Apply Model Requirements (GPT-5.1 Codex Preview or GPT-5.1 Preview). Enforce Reality Baseline. Await CI/CD and repo PAC instructions.`

**🔧 BOOT — GID-08 ALEX (Governance & Alignment Engine)**
`BOOT: GID-08 ALEX — Load governance + alignment profile. Load CHAINBRIDGE_REALITY_BASELINE.md, PAC_STANDARD.md, AGENT_REGISTRY.md, and CHAINBRIDGE_AGENT_LAUNCH_CENTER.md. Apply Model Requirements (GPT-5.1 Preview or Claude Opus). Enforce ChainBridge Mantra. Monitor model selection & drift. Await governance PAC instructions.`

**🔧 BOOT — GID-10 Maggie (Machine Learning & Applied AI Lead)**
`BOOT: GID-10 MAGGIE — Load ChainBridge ML architecture, ChainIQ context, PAC_STANDARD.md, AGENT_REGISTRY.md, and ML pipeline references. Apply Model Requirements (GPT-5.1 Preview / GPT-5.1 Codex Preview). Enforce Reality Baseline. Await ML PAC instructions.`

---

## 4. Universal Agent Reboot Macro (Human Cheat Sheet)

Keep this macro in a visible place (Notes, Notion, etc.):

```text
CHAINBRIDGE AGENT REBOOT MACRO

If a chat resets, freezes, or the wrong model loads:

1) Select the correct model (see Model Policy / PAC_STANDARD.md).
2) Paste the agent’s BOOT command from CHAINBRIDGE_AGENT_LAUNCH_CENTER.md or AGENT_REGISTRY.md.
3) Continue PAC execution.

Rule: IF ANYTHING BREAKS → PASTE BOOT.
```

---

## 5. Cheat Sheet You Can Paste Anywhere

Here’s a **one-block “launch macro”** you can keep in Notes, Notion, etc.:

```text
CHAINBRIDGE DAILY LAUNCH

1) Open correct repo:
   cd ~/Documents/Projects/ChainBridge-local-repo
   git remote -v   # must show origin = https://github.com/BIGmindz/ChainBridge.git
   code .

2) Open Copilot Chat tabs:
   - Tab 1: Benson CTO
   - Tab 2: Cody (backend)
   - Tab 3: Sonny (frontend)
   - Tab 4: Dan (DevOps) [optional]
   - Others as needed

3) In each tab, paste BOOT command from CHAINBRIDGE_AGENT_LAUNCH_CENTER.md.

4) In Benson tab, decide today’s PACs (what we’re working on).

5) Paste each PAC into the matching agent tab.

6) When done or pausing, type !WRAP in each tab to get a SITREP and next steps.
```
