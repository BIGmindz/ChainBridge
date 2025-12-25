# ChainBridge Repository Context

> **Generated**: 2025-12-24
> **Purpose**: Minimal context artifact for external architectural review
> **PAC**: PAC-ATLAS-P23-REPO-CONTEXT-EXTRACTION-AND-TRANSFER-01

---

## 1. System Overview

**ChainBridge** is a multi-agent governance framework implementing deterministic, fail-closed artifact validation with immutable audit trails.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **PAC Validation** | Protocol Artifact Certificates validated at emission, pre-commit, and CI |
| **WRAP Processing** | Work Request Authorization Packets for task delegation |
| **Governance Ledger** | Append-only, hash-chained audit trail for all governance events |
| **Agent Registry** | Canonical identity source for all agents (GID, color, role, lane) |
| **Review Gate** | Terminal validation gate requiring Benson (GID-00) approval |
| **BSRG-01** | Benson Self-Review Gate — mandatory self-review for all PACs |

### Technology Stack

- **Runtime**: Python 3.11+
- **Validation Engine**: `gate_pack.py` (~2400 lines)
- **Ledger System**: `ledger_writer.py` (~1400 lines)
- **CI/CD**: GitHub Actions with governance gates
- **Frontend**: React/TypeScript (chainboard-ui)
- **Services**: FastAPI microservices

---

## 2. Governance Architecture

### Enforcement Chain (5 Gates)

```
GATE 0: TEMPLATE SELECTION
   ↓
GATE 1: PACK EMISSION VALIDATION (gate_pack.py)
   ↓
GATE 2: PRE-COMMIT HOOK (FAIL-CLOSED)
   ↓
GATE 3: CI MERGE BLOCKER
   ↓
GATE 4: WRAP AUTHORIZATION / BENSON REVIEW
```

### Governance Mode

```yaml
mode: FAIL_CLOSED
bypass_paths: 0
override_allowed: false
warning_mode: false
```

### Key Error Code Categories

| Range | Category | Description |
|-------|----------|-------------|
| G0_001-G0_012 | Core Validation | Block order, missing fields, registry mismatch |
| G0_020-G0_024 | Gold Standard | Checklist enforcement, self-certification |
| G0_040-G0_046 | Positive Closure | Closure validation, authority, lineage |
| RG_001-RG_007 | Review Gate | ReviewGate v1.1 compliance |
| BSRG_001-BSRG_012 | Self-Review Gate | BSRG-01 enforcement |
| GS_030-GS_032 | Agent Color | Color enforcement (P25) |

---

## 3. Review / Correction / Closure Flow

### Artifact Lifecycle

```
1. PAC ISSUED
   ↓
2. VALIDATION (gate_pack.py)
   ↓
3. BSRG-01 REVIEW (Benson Self-Review)
   ↓
4. EXECUTION
   ↓
5. WRAP SUBMITTED (if delegated)
   ↓
6. REVIEW GATE (terminal validation)
   ↓
7. POSITIVE CLOSURE (if successful)
   or
7. CORRECTION OPENED (if violations)
   ↓
8. CORRECTION CLOSED
   ↓
9. POSITIVE CLOSURE
```

### Correction Types

| Type | Description |
|------|-------------|
| `STRUCTURE_ONLY` | Formatting, headers, block order |
| `SEMANTIC` | Logic, intent, scope changes |
| `REISSUE` | Full artifact replacement |
| `AMENDMENT` | Targeted fixes to existing artifact |
| `INVALIDATION` | Artifact revocation |

### Positive Closure Requirements

- Explicit `CLOSURE_CLASS: POSITIVE_CLOSURE`
- `CLOSURE_AUTHORITY: BENSON (GID-00)`
- Complete `GOLD_STANDARD_CHECKLIST`
- `TRAINING_SIGNAL.signal_type: POSITIVE_REINFORCEMENT`
- Correction lineage documentation (if applicable)

---

## 4. Ledger & Immutability Model

### Ledger Entry Types

| Type | Description |
|------|-------------|
| `PAC_ISSUED` | New PAC created |
| `PAC_EXECUTED` | PAC work completed |
| `WRAP_SUBMITTED` | WRAP for review |
| `WRAP_ACCEPTED` | WRAP approved |
| `VALIDATION_PASS` | Artifact passed validation |
| `VALIDATION_FAIL` | Artifact failed validation |
| `CORRECTION_OPENED` | Correction cycle started |
| `CORRECTION_CLOSED` | Correction cycle completed |
| `POSITIVE_CLOSURE_ACKNOWLEDGED` | Success recorded |
| `BLOCK_ENFORCED` | Hard block applied |
| `BSRG_REVIEW` | Benson Self-Review recorded |

### Hash Chain Structure

```json
{
  "sequence": 42,
  "timestamp": "2025-12-24T15:00:00Z",
  "entry_type": "BSRG_REVIEW",
  "prev_hash": "a050c90ce3cf9d97...",
  "entry_hash": "dcb248028f2d1a06...",
  "artifact_sha256": "17ee5abf55d83dc1..."
}
```

### Integrity Validation

```bash
python tools/governance/ledger_writer.py validate
```

Output:
```
INTEGRITY_VERIFIED
Hash Chain Validation: ✅ Chain Intact
No Tampering: ✅
```

---

## 5. Agent Model & Color Governance

### Agent Identity Invariants

1. **One Agent, One GID, One Color, One Icon, One Lane**
2. **No Shared GIDs**
3. **Registry is Authority**
4. **Color is Governance-Critical** (not cosmetic)

### Canonical Agent Registry (v4.0.0)

| Agent | GID | Color | Icon | Execution Lane |
|-------|-----|-------|------|----------------|
| BENSON | GID-00 | TEAL | 🟦🟩 | ORCHESTRATION |
| CODY | GID-01 | BLUE | 🔵 | BACKEND |
| SONNY | GID-02 | YELLOW | 🟡 | FRONTEND |
| MIRA | GID-03 | PURPLE | 🟣 | RESEARCH |
| CINDY | GID-04 | CYAN | 🔷 | BACKEND |
| ATLAS | GID-05 | BLUE | 🟦 | SYSTEM_STATE |
| SAM | GID-06 | DARK_RED | 🔴 | SECURITY |
| DAN | GID-07 | GREEN | 🟢 | DEVOPS |
| ALEX | GID-08 | WHITE | ⚪ | GOVERNANCE |
| LIRA | GID-09 | PINK | 🩷 | UX |
| MAGGIE | GID-10 | MAGENTA | 💗 | ML_AI |
| RUBY | GID-12 | CRIMSON | ♦️ | RISK_POLICY |

### Color Enforcement (PAC-ATLAS-P25)

```yaml
GS_030: Agent referenced without agent_color
GS_031: agent_color does not match canonical registry
GS_032: agent_color missing from activation acknowledgements
```

---

## 6. Directory Structure (Key Paths)

```
ChainBridge/
├── tools/governance/
│   ├── gate_pack.py          # Core validation engine
│   ├── ledger_writer.py      # Governance ledger
│   ├── audit_corrections.py  # Correction auditing
│   └── escalation_engine.py  # Escalation handling
├── docs/governance/
│   ├── AGENT_REGISTRY.json   # Canonical agent registry
│   ├── CANONICAL_CORRECTION_PACK_TEMPLATE.md
│   └── pacs/                 # Issued PACs
├── chainboard-ui/            # React frontend
├── chainiq-service/          # ML/AI service
├── app/                      # FastAPI services
│   ├── services/
│   ├── models/
│   └── api/
├── tests/                    # Test suites
│   └── governance/           # Governance tests
└── .github/workflows/        # CI/CD pipelines
```

---

## 7. Key Commands

### Validation

```bash
# Single file validation
python tools/governance/gate_pack.py --file <path>

# CI mode (all governance files)
python tools/governance/gate_pack.py --mode ci

# Pre-commit mode
python tools/governance/gate_pack.py --mode precommit
```

### Ledger Operations

```bash
# Validate ledger integrity
python tools/governance/ledger_writer.py validate

# Generate audit report
python tools/governance/ledger_writer.py report
```

### Testing

```bash
# Run governance tests
python -m pytest tests/governance/ -v

# Run all tests
python -m pytest tests/ -v
```

---

## 8. Bundle Contents

| File | Description | Size |
|------|-------------|------|
| `repo_tree.txt` | Full file listing | ~2500 entries |
| `governance_core_bundle/gate_pack.py` | Validation engine | ~91KB |
| `governance_core_bundle/ledger_writer.py` | Ledger system | ~54KB |
| `governance_core_bundle/AGENT_REGISTRY.json` | Agent registry | ~4KB |
| `governance_core_bundle/CANONICAL_CORRECTION_PACK_TEMPLATE.md` | Correction template | ~8KB |
| `agent_registry_snapshot.yaml` | Agent summary | ~2KB |
| `README_CONTEXT.md` | This document | ~8KB |
| `repo_context_manifest.yaml` | Bundle manifest | ~2KB |

---

## 9. Governance Philosophy

```
Governance is physics, not policy.
Invalid artifacts cannot exist.
Bypass paths: 0.
Override allowed: false.
```

### Core Principles

1. **FAIL_CLOSED** — All validation failures block progression
2. **NO_DISCRETION** — Rules are deterministic, not interpretive
3. **TERMINAL_CHECKLISTS** — Gold Standard Checklist is final gate
4. **IMMUTABLE_AUDIT** — Hash-chained ledger prevents tampering
5. **REGISTRY_IS_AUTHORITY** — Agent identity comes from registry only

---

**END — README_CONTEXT.md**
**Generated by**: ATLAS (GID-05)
**PAC**: PAC-ATLAS-P23-REPO-CONTEXT-EXTRACTION-AND-TRANSFER-01
