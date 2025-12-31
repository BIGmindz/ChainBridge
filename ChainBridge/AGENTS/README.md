# AGENTS — CANONICAL AGENT DEFINITIONS

> **Status:** CANONICAL / LOCKED
> **Authority:** PAC-BENSON-CANONICAL-IDENTITY-RECONCILIATION-01
> **Ratification Date:** 2025-12-22

---

## Directory Policy

```
DIRECTORY_POLICY {
  canonical_directory: "AGENTS/"
  status: "SINGLE_SOURCE_OF_TRUTH"
  deprecated_alternatives: [
    "AGENTS 2/ → archived to archive/deprecated/"
  ]
}
```

---

## Governance Rules

1. **This is the ONLY agent definition directory**
2. All agent prompts, checklists, and knowledge scopes live here
3. No duplicate directories are permitted
4. Changes require explicit PAC authorization

---

## Canonical Registry Reference

The authoritative agent registry is:
- `docs/governance/AGENT_REGISTRY.json`
- `docs/governance/AGENT_REGISTRY.md`

This directory contains implementation artifacts that MUST align with the registry.

---

## Forbidden Actions

- ❌ Creating alternative agent directories
- ❌ Adding agents not registered in AGENT_REGISTRY.json
- ❌ Modifying agent definitions without PAC

---

🟦🟩 **Benson (GID-00)** — Chief Architect / Orchestrator
