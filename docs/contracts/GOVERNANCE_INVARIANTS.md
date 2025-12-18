# ChainBridge Governance Invariants

**Document:** GOVERNANCE_INVARIANTS.md
**Version:** 1.0
**Status:** LOCKED
**Classification:** CONTRACT (Governance Root Document)

**Contract Owner:** BENSON (GID-00)
**PAC Reference:** PAC-BENSON-GOVERNANCE-INVARIANT-LOCK-01
**Effective Date:** 2025-12-18
**Source Snapshot:** ChainBridge-exec-snapshot_2025-12-18.zip

---

## 1. Purpose

This document is the **governance root contract** for ChainBridge. It defines the non-negotiable governance invariants that:

- Control agent scope boundaries
- Enforce irreversibility of decisions
- Make governance drift mechanically detectable
- Require explicit PAC for any relaxation

**Every invariant is CI-enforced, code-backed, and auditable.**

---

## 2. Governance Invariant Domains

| Domain | ID Prefix | Scope |
|--------|-----------|-------|
| Agent Scope | INV-GOV-SCOPE | Path restrictions per agent |
| ALEX Enforcement | INV-GOV-ALEX | Hard constraint enforcement |
| Chain of Command | INV-GOV-COC | Decision routing hierarchy |
| Denial Irreversibility | INV-GOV-DENY | No retry after denial |
| Fingerprint Integrity | INV-GOV-FP | Governance drift detection |
| Repo Scope | INV-GOV-REPO | Repository boundary enforcement |
| Boot Validation | INV-GOV-BOOT | Fail-closed startup |

---

## 3. Agent Scope Invariants

### INV-GOV-SCOPE-001: Atlas Domain Boundary
**Atlas (GID-11) has ZERO domain authority over runtime code.**

| Enforcement | Location |
|-------------|----------|
| AtlasScope.is_path_forbidden() | `core/governance/atlas_scope.py:52-72` |
| ATLAS_SCOPE_LOCK_v1.yaml | `docs/governance/ATLAS_SCOPE_LOCK_v1.yaml` |
| CI scope-guard.yml | `.github/workflows/scope-guard.yml` |
| forbidden_paths list | 40+ path patterns including core/**, api/**, services/** |

**Failure Condition:** ATLAS_DOMAIN_VIOLATION denial; CI blocks PR.

---

### INV-GOV-SCOPE-002: Forbidden Regions Enforcement
**File moves in protected regions require ATLAS Move Matrix approval.**

| Enforcement | Location |
|-------------|----------|
| FORBIDDEN_REGIONS list | `.github/workflows/forbidden_regions_check.yml:46-58` |
| CRITICAL_FILES list | `.github/workflows/forbidden_regions_check.yml:61-70` |
| Move Matrix pattern | `ATLAS-MOVE-MATRIX-YYYY-MM-DD` required in PR |
| Protected regions | core, modules, src, chainpay-service, chainiq-service, etc. |

**Failure Condition:** CI blocks PR without Move Matrix approval.

---

### INV-GOV-SCOPE-003: Sensitive Domain Detection
**Code touching sensitive paths triggers strict review.**

| Enforcement | Location |
|-------------|----------|
| SENSITIVE_DOMAIN_GATEWAY.md | `docs/governance/SENSITIVE_DOMAIN_GATEWAY.md` |
| Sensitive domain list | pdo, proofpack, trust, crypto, verification, governance, audit, settlement |
| Path patterns | core/occ/schemas/pdo.py, docs/contracts/*.md, gateway/pdo_*.py |

**Failure Condition:** Forbidden language patterns block PR; outputs invalidated.

---

### INV-GOV-SCOPE-004: Archive Isolation
**Archived code is inert and cannot be imported.**

| Enforcement | Location |
|-------------|----------|
| CI import check | `.github/workflows/scope-guard.yml:54-60` |
| Pattern: `from archive` | Blocked by grep in CI |
| Ruff exclusion | Archive excluded from lint |
| Pytest exclusion | Archive excluded from test discovery |

**Failure Condition:** CI fails on `from archive` import outside archive/.

---

## 4. ALEX Enforcement Invariants

### INV-GOV-ALEX-001: ALEX Has Override Authority
**ALEX (GID-08) has veto power over all agents.**

| Enforcement | Location |
|-------------|----------|
| ALEX_RULES.json rule_9 | `.github/ALEX_RULES.json:131-145` |
| Override mapping | Cody→BLOCK_PR, Maggie→BLOCK_DEPLOYMENT, etc. |
| Mode | PROTECTION_MODE (active enforcement) |

**Failure Condition:** ALEX override blocks agent action; no bypass.

---

### INV-GOV-ALEX-002: Glass-Box ML Models Only
**Only explainable, monotonic ML models are permitted.**

| Enforcement | Location |
|-------------|----------|
| ALEX_RULES.json rule_1 | `.github/ALEX_RULES.json:13-20` |
| Allowed types | EBM, GAM, LogisticRegression, MonotoneGBDT |
| Blocked types | RandomForest, XGBoost, NeuralNetwork, DeepLearning |
| Severity | CRITICAL |

**Failure Condition:** PR blocked if black-box model detected.

---

### INV-GOV-ALEX-003: Proof Over Performance
**All settlements require risk scores and ProofPacks.**

| Enforcement | Location |
|-------------|----------|
| ALEX_RULES.json rule_2 | `.github/ALEX_RULES.json:22-34` |
| Requirements | ChainIQ risk score, ProofPack artifact, event chain, custody proof |
| Enforcement | RUNTIME_CHECK |

**Failure Condition:** Settlement blocked without proof artifacts.

---

### INV-GOV-ALEX-004: No Unbounded Attack Surface
**Dangerous code patterns are prohibited.**

| Enforcement | Location |
|-------------|----------|
| ALEX_RULES.json rule_4 | `.github/ALEX_RULES.json:52-65` |
| Blocked patterns | eval(), exec(), yaml.load(), dynamic imports, schema-less persistence |
| Severity | HIGH |

**Failure Condition:** PR blocked on dangerous pattern detection.

---

### INV-GOV-ALEX-005: Zero Silent Failures
**All exceptions must be logged and escalated.**

| Enforcement | Location |
|-------------|----------|
| ALEX_RULES.json rule_11 | `.github/ALEX_RULES.json:158-167` |
| Blocked patterns | `except: pass`, silent retry loops, swallowed exceptions |

**Failure Condition:** Warning on silent exception handling.

---

### INV-GOV-ALEX-006: CI/CD Governance Hooks
**All PRs must pass governance checks.**

| Enforcement | Location |
|-------------|----------|
| ALEX_RULES.json rule_8 | `.github/ALEX_RULES.json:111-123` |
| Requirements | Migration notes, risk assessment, governance statement, 80%+ coverage |
| PR metadata check | `.github/workflows/governance_check.yml:29-60` |

**Failure Condition:** PR blocked without required sections.

---

## 5. Chain of Command Invariants

### INV-GOV-COC-001: DRCP Denial Routing
**All DENY decisions route to Diggy (GID-00).**

| Enforcement | Location |
|-------------|----------|
| DRCP module | `core/governance/drcp.py` |
| DenialRecord.next_hop | Always set to DIGGY_GID ("GID-00") |
| DRCP constants | DIGGY_GID, DIGGY_FORBIDDEN_VERBS, DENIAL_ROUTED_VERBS |

**Failure Condition:** Denial record always includes next_hop=GID-00.

---

### INV-GOV-COC-002: Diggy Forbidden Verbs
**Diggy (GID-00) cannot EXECUTE, BLOCK, or APPROVE.**

| Enforcement | Location |
|-------------|----------|
| DIGGY_FORBIDDEN_VERBS | `core/governance/drcp.py:30` |
| Set: {"EXECUTE", "BLOCK", "APPROVE"} | Hardcoded constant |
| Diggi corrections | `core/governance/diggi_corrections.py` |

**Failure Condition:** Intent from GID-00 with forbidden verb is DENIED.

---

### INV-GOV-COC-003: Chain of Command Enforcement
**EXECUTE/BLOCK/APPROVE must route through orchestrator.**

| Enforcement | Location |
|-------------|----------|
| GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml | `docs/governance/GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml:18-21` |
| Gate: chain_of_command_enforced | Fatal=true |
| Orchestrator GID | GID-00 |

**Failure Condition:** CHAIN_OF_COMMAND_VIOLATION denial; fatal.

---

## 6. Denial Irreversibility Invariants

### INV-GOV-DENY-001: No Retry After Denial
**Agents cannot retry after denial.**

| Enforcement | Location |
|-------------|----------|
| DenialRegistry | `core/governance/denial_registry.py` |
| is_denied() check | Returns True if denial key exists |
| Persist to SQLite | `logs/denial_registry.db` |

**Failure Condition:** Duplicate intent with same key is immediately DENIED.

---

### INV-GOV-DENY-002: Denial Persistence
**Denials survive process restarts.**

| Enforcement | Location |
|-------------|----------|
| SQLite backend | `core/governance/denial_registry.py` |
| Fail-closed | DenialPersistenceError blocks execution |
| No fallback | No in-memory degradation |

**Failure Condition:** If persistence fails, execution blocks.

---

### INV-GOV-DENY-003: Denial Audit Trail
**All denials are recorded with timestamps.**

| Enforcement | Location |
|-------------|----------|
| register_denial() | `core/governance/denial_registry.py:98-114` |
| Fields | agent_gid, verb, target, denial_code, intent_id, timestamp |
| Audit export | `core/governance/audit_exporter.py` |

**Failure Condition:** Denial without audit record is invalid.

---

## 7. Governance Fingerprint Invariants

### INV-GOV-FP-001: Deterministic Governance Hash
**Governance fingerprint is computed at startup and cached.**

| Enforcement | Location |
|-------------|----------|
| GovernanceFingerprintEngine | `core/governance/governance_fingerprint.py` |
| compute_fingerprint() | SHA-256 of governance root files |
| GOVERNANCE_ROOTS | config/*.json, .github/ALEX_RULES.json, manifests/*.yaml, etc. |

**Failure Condition:** GovernanceBootError if roots unreadable.

---

### INV-GOV-FP-002: Drift Detection
**Governance files changing after boot triggers error.**

| Enforcement | Location |
|-------------|----------|
| GovernanceDriftError | `core/governance/governance_fingerprint.py:42-47` |
| Runtime check | Compare current hash to cached fingerprint |
| Fields | original_hash, current_hash |

**Failure Condition:** GovernanceDriftError raised; includes hash delta.

---

### INV-GOV-FP-003: Artifact Integrity
**Build artifact hashes are deterministic.**

| Enforcement | Location |
|-------------|----------|
| artifact-integrity.yml | `.github/workflows/artifact-integrity.yml` |
| Manifest: build/artifacts.json | Hash verification in CI |
| Stale check | Fresh hash must match stored hash |

**Failure Condition:** CI fails if artifact manifest is stale.

---

## 8. Repository Scope Invariants

### INV-GOV-REPO-001: Repo Scope Manifest
**Repository scope is defined and enforced.**

| Enforcement | Location |
|-------------|----------|
| REPO_SCOPE_MANIFEST.md | `docs/governance/REPO_SCOPE_MANIFEST.md` |
| In-scope | Governance, Gateway, ChainBoard, ChainIQ, ChainPay, CI, Archive |
| Out-of-scope | Trading bots, strategy experimentation, ML training |

**Failure Condition:** Out-of-scope artifacts trigger CI failure.

---

### INV-GOV-REPO-002: Requirements Lock
**Only authorized requirements files are permitted.**

| Enforcement | Location |
|-------------|----------|
| scope-guard.yml requirements-lock | `.github/workflows/scope-guard.yml:79-110` |
| Allowed files | requirements.txt, requirements-dev.txt |
| PAC reference | PAC-DAN-03 |

**Failure Condition:** Unauthorized requirements file blocks CI.

---

### INV-GOV-REPO-003: Forbidden Extensions
**Certain file extensions are prohibited outside archive.**

| Enforcement | Location |
|-------------|----------|
| scope-guard.yml extension check | `.github/workflows/scope-guard.yml:112-143` |
| Forbidden extensions | .ipynb, .streamlit |
| PAC reference | PAC-DAN-03 |

**Failure Condition:** Forbidden extension outside archive blocks CI.

---

## 9. Boot Validation Invariants

### INV-GOV-BOOT-001: Governance Root File Validation
**Critical governance files must exist and be valid before boot.**

| Enforcement | Location |
|-------------|----------|
| boot_checks.py | `core/governance/boot_checks.py` |
| GOVERNANCE_FILES | config/agents.json, .github/ALEX_RULES.json |
| Required fields | calp_version, governance_id, version |

**Failure Condition:** GovernanceBootError halts startup.

---

### INV-GOV-BOOT-002: Fail-Closed Boot
**Any governance violation raises fatal error.**

| Enforcement | Location |
|-------------|----------|
| GovernanceBootError | `core/governance/boot_checks.py:39-49` |
| Principle | No warnings, no defaults, deterministic errors |

**Failure Condition:** Missing or invalid governance file halts all operations.

---

### INV-GOV-BOOT-003: Checklist Dependency
**Governance validation checklist is a hard dependency.**

| Enforcement | Location |
|-------------|----------|
| governance_check.yml | `.github/workflows/governance_check.yml:101-133` |
| Required files | GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml, GOVERNANCE_VALIDATION_CHECKLIST_v1.md |
| Status | Must be GOVERNANCE-LOCKED |
| failure_mode | Must be DENY |

**Failure Condition:** Missing or unlocked checklist blocks CI.

---

## 10. Enforcement Mapping

| Invariant ID | CI Workflow | Code Module | Contract Doc |
|--------------|-------------|-------------|--------------|
| INV-GOV-SCOPE-001 | scope-guard.yml | atlas_scope.py | ATLAS_SCOPE_LOCK_v1.yaml |
| INV-GOV-SCOPE-002 | forbidden_regions_check.yml | — | ATLAS_MOVE_MATRIX.json |
| INV-GOV-SCOPE-003 | — | — | SENSITIVE_DOMAIN_GATEWAY.md |
| INV-GOV-SCOPE-004 | scope-guard.yml | — | REPO_SCOPE_MANIFEST.md |
| INV-GOV-ALEX-001 | — | — | ALEX_RULES.json |
| INV-GOV-ALEX-002 | governance_check.yml | — | ALEX_RULES.json |
| INV-GOV-ALEX-003 | — | — | ALEX_RULES.json |
| INV-GOV-ALEX-004 | governance_check.yml | — | ALEX_RULES.json |
| INV-GOV-ALEX-005 | — | — | ALEX_RULES.json |
| INV-GOV-ALEX-006 | governance_check.yml | — | ALEX_RULES.json |
| INV-GOV-COC-001 | — | drcp.py | — |
| INV-GOV-COC-002 | — | drcp.py | — |
| INV-GOV-COC-003 | governance_check.yml | — | GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml |
| INV-GOV-DENY-001 | — | denial_registry.py | — |
| INV-GOV-DENY-002 | — | denial_registry.py | — |
| INV-GOV-DENY-003 | — | denial_registry.py, audit_exporter.py | — |
| INV-GOV-FP-001 | — | governance_fingerprint.py | — |
| INV-GOV-FP-002 | — | governance_fingerprint.py | — |
| INV-GOV-FP-003 | artifact-integrity.yml | — | — |
| INV-GOV-REPO-001 | scope-guard.yml | — | REPO_SCOPE_MANIFEST.md |
| INV-GOV-REPO-002 | scope-guard.yml | — | REPO_SCOPE_LOCK.md |
| INV-GOV-REPO-003 | scope-guard.yml | — | REPO_SCOPE_LOCK.md |
| INV-GOV-BOOT-001 | — | boot_checks.py | — |
| INV-GOV-BOOT-002 | — | boot_checks.py | — |
| INV-GOV-BOOT-003 | governance_check.yml | — | GOVERNANCE_VALIDATION_CHECKLIST_v1.yaml |

---

## 11. Unenforced or Ambiguous Rules

| Issue ID | Description | Gap |
|----------|-------------|-----|
| GAP-GOV-001 | INV-GOV-SCOPE-003 sensitive domain detection | No CI enforcement; relies on manual review |
| GAP-GOV-002 | INV-GOV-ALEX-003 proof-over-performance | RUNTIME_CHECK stated but no unit test coverage visible |
| GAP-GOV-003 | INV-GOV-ALEX-005 zero silent failures | Enforcement is WARNING not BLOCK_PR |
| GAP-GOV-004 | INV-GOV-COC-002 Diggy forbidden verbs | No explicit CI gate; relies on runtime DRCP |
| GAP-GOV-005 | Color-lock validation | pac_color_check.yml exists but only triggers on docs/** paths |

---

## 12. Change Authority

This contract can only be modified by:

1. **BENSON (GID-00)** with new PAC reference
2. **ALEX (GID-08)** for governance rule updates
3. **ATLAS (GID-11)** for structural/scaffolding updates ONLY

All changes require:
- PAC with explicit rationale
- CI validation passing
- No regression to invariant coverage

---

## 13. Governance Integrity Statement

> This document captures the state of ChainBridge governance as observed in
> ChainBridge-exec-snapshot_2025-12-18.zip. Every invariant listed here has
> been traced to code, CI workflow, or contract document within that snapshot.
>
> Invariants without full CI enforcement are documented in Section 11.
>
> This contract supersedes any informal governance statements elsewhere.
> When in conflict, this document is authoritative.

---

## 14. Recommended Next PAC

**PAC-BENSON-GOVERNANCE-GAP-CLOSE-01:**
- Add CI enforcement for sensitive domain detection (GAP-GOV-001)
- Add test coverage for proof-over-performance runtime check (GAP-GOV-002)
- Escalate zero-silent-failures from WARNING to BLOCK_PR (GAP-GOV-003)
- Add CI gate for Diggy forbidden verbs validation (GAP-GOV-004)
- Expand pac_color_check.yml path triggers (GAP-GOV-005)

---

**Document Hash:** `[To be computed on commit]`
**Last Verified:** 2025-12-18
