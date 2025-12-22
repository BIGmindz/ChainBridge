# TRAINING_SIGNAL_PROTOCOL.md
## Agent University — Training Signal Protocol v1

| Field | Value |
|-------|-------|
| **Protocol Version** | 1.0.0 |
| **Status** | LOCKED |
| **Authority** | ALEX (GID-08) — Governance & Alignment Engine |
| **Effective Date** | 2025-12-22 |
| **Enforcement** | MANDATORY — All PACs |

---

## 1. PURPOSE

This protocol establishes the canonical standard for embedding, tagging, and extracting training signals from PAC artifacts. Training signals enable:

- **Measurement** — Quantify training effectiveness
- **Drift Detection** — Identify cognitive drift in agents
- **Curriculum Building** — Feed Agent University with structured learning data
- **Auditability** — Governance can inspect how agents are being shaped

---

## 2. TRAINING SIGNAL BLOCK (TSB) — SPECIFICATION

### 2.1 Required Section Header

Every PAC **MUST** contain a section with this exact header:

```markdown
## 🚨 TRAINING SIGNAL — EMBEDDED
```

**Machine Detection Pattern (Regex):**
```regex
^##\s*🚨?\s*TRAINING SIGNAL\s*[—–-]\s*EMBEDDED
```

### 2.2 Placement

The TSB must appear:
- **After** all execution tasks
- **Before** the OUTPUT / HANDOFF section
- As a **standalone section** (not nested)

---

## 3. TSB SCHEMA — CANONICAL

Every Training Signal Block must include these fields:

| Field | Required | Description | Valid Values |
|-------|----------|-------------|--------------|
| **Training Type** | ✔ | Competency being trained | Free text — action-oriented |
| **Agent Role** | ✔ | Target agent identifier | `GID-XX` + role name |
| **Curriculum Level** | ✔ | Depth of training | `L0`, `L1`, `L2` |
| **Curriculum Tags** | ✔ | Structured taxonomy tags | See `CURRICULUM_TAXONOMY.md` |
| **Behavioral Objectives** | ✔ | What behavior should change | Numbered list, 1–5 items |
| **Drift Risks Addressed** | ✔ | Failure modes prevented | Bulleted list |
| **Evaluation Metrics** | ✔ | How success is measured | Quantifiable where possible |

### 3.1 Schema Template

```markdown
## 🚨 TRAINING SIGNAL — EMBEDDED

**TRAINING SIGNAL — AGENT: {AGENT_NAME} (GID-{XX})**

| Field | Value |
|-------|-------|
| **Training Type** | {competency description} |
| **Curriculum Level** | Agent University — {L0/L1/L2} |
| **Curriculum Tags** | `AGENT-U / {DOMAIN} / {SUBTOPIC} / {LEVEL}` |

**Behavioral Objectives**
1. {objective_1}
2. {objective_2}
3. {objective_3}

**Drift Risks Addressed**
- {risk_1}
- {risk_2}

**Evaluation Metrics**
- {metric_1}
- {metric_2}
```

---

## 4. CURRICULUM LEVEL CLASSIFICATION

| Level | Code | Description | PAC Types |
|-------|------|-------------|-----------|
| **Experimental** | `L0` | Unvalidated patterns, exploratory work | Prototypes, spikes, research |
| **Execution** | `L1` | Standard operational competencies | Implementation, integration, testing |
| **Doctrine** | `L2` | Governance, security, enforcement patterns | Policy, security, enforcement, architecture |

### 4.1 Classification Rules

| PAC Type | Assigned Level |
|----------|----------------|
| Pure execution (code, tests, docs) | `L1` |
| Enforcement / Security | `L2` |
| Doctrine / Governance | `L2` |
| Experimental / Spike | `L0` |
| Mixed (execution + governance) | Highest applicable level |

---

## 5. VALIDATION RULES

### 5.1 PAC is VALID if:

```
✔ TSB section header exists
✔ All required schema fields present
✔ Curriculum Level is valid (L0/L1/L2)
✔ At least 1 Behavioral Objective declared
✔ At least 1 Drift Risk declared
✔ At least 1 Evaluation Metric declared
✔ Curriculum Tags follow taxonomy
```

### 5.2 PAC is INVALID if:

```
✘ No Training Signal block exists
✘ Schema is incomplete (missing required fields)
✘ Training is implied but not declared
✘ Curriculum Level missing or invalid
✘ Zero Behavioral Objectives
```

---

## 6. GOVERNANCE ENFORCEMENT

### 6.1 On Invalid PAC Detection

1. **REJECT** — PAC cannot proceed
2. **LOG** — Record violation type and PAC ID
3. **REQUIRE RE-ISSUANCE** — Author must fix and resubmit

### 6.2 Enforcement Responsibility

| Agent | Responsibility |
|-------|----------------|
| **ALEX (GID-08)** | Primary enforcement authority |
| **All Agents** | Self-validate before submission |
| **Human Operators** | May override with explicit governance waiver |

### 6.3 No Exceptions

- No grace periods
- No "will add later"
- No implicit training signals
- Partial compliance = non-compliance

---

## 7. EXTRACTION & CURRICULUM INTEGRATION

### 7.1 Extraction Pattern

TSBs are designed for automated extraction:

```python
import re

TSB_PATTERN = r'## 🚨?\s*TRAINING SIGNAL\s*[—–-]\s*EMBEDDED\s*\n([\s\S]*?)(?=\n## |\n---|\Z)'

def extract_training_signal(pac_content: str) -> str | None:
    match = re.search(TSB_PATTERN, pac_content)
    return match.group(1).strip() if match else None
```

### 7.2 Curriculum Feed

Extracted TSBs feed into:
- `docs/agent-university/curriculum/` — Per-agent learning records
- Agent onboarding packs (Ruby, Tina, future agents)
- Drift analysis pipelines

---

## 8. VERSIONING

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2025-12-22 | Initial protocol — LOCKED |

---

## 9. COMPLIANCE CHECKLIST

For every PAC submission:

```
□ TSB section exists with correct header
□ Agent Role declared (GID + name)
□ Training Type specified
□ Curriculum Level assigned (L0/L1/L2)
□ Curriculum Tags present and valid
□ Behavioral Objectives listed (1-5 items)
□ Drift Risks identified
□ Evaluation Metrics defined
□ TSB placed after tasks, before handoff
```

---

*Protocol Authority: ALEX (GID-08) — Governance & Alignment Engine*
*Status: LOCKED — No modifications without governance PAC*
