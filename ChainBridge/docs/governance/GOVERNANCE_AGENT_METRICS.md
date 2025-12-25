# GOVERNANCE_AGENT_METRICS.md

> **Version:** 1.0.0  
> **Authority:** PAC-BENSON-P37-AGENT-PERFORMANCE-METRICS-BASELINE-AND-ENFORCEMENT-01  
> **Status:** ACTIVE  
> **Last Updated:** 2025-06-16

---

## 1. Purpose

This document establishes **baseline performance metrics** for all ChainBridge agents by execution lane. These baselines enable:

1. **Regression detection** — Identify performance degradation across versions
2. **Quality assurance** — Ensure agents meet minimum quality standards
3. **Comparative analysis** — Benchmark new implementations against established agents
4. **Capacity planning** — Predict execution costs and resource requirements

---

## 2. Execution Lane Definitions

### 2.1 GOVERNANCE

Agents operating in the GOVERNANCE lane enforce compliance, validate artifacts, and manage system integrity.

**Agents:** ATLAS (GID-001), BENSON (GID-002)

**Baseline Metrics:**
| Metric | Target | Acceptable Range | Hard Floor |
|--------|--------|------------------|------------|
| `execution_time_ms` | ≤5000 | 3000–7000 | 10000 |
| `quality_score` | ≥0.95 | 0.90–1.00 | 0.85 |
| `scope_compliance` | 100% | 98–100% | 95% |
| `task_completion_rate` | 100% | 95–100% | 90% |

**Characteristic Workloads:**
- PAC validation (10–50 validation checks per artifact)
- Schema enforcement (5–20 schema matches)
- Error code emission (0–5 errors typical)

---

### 2.2 DEVELOPMENT

Agents operating in the DEVELOPMENT lane implement features, modify code, and create artifacts.

**Agents:** DANA (GID-004) — NON-EXECUTING

**Baseline Metrics:**
| Metric | Target | Acceptable Range | Hard Floor |
|--------|--------|------------------|------------|
| `execution_time_ms` | ≤30000 | 15000–45000 | 60000 |
| `quality_score` | ≥0.85 | 0.80–1.00 | 0.75 |
| `scope_compliance` | 100% | 95–100% | 90% |
| `task_completion_rate` | ≥95% | 90–100% | 80% |

**Characteristic Workloads:**
- File creation (1–20 files per task)
- Code modification (10–500 lines changed)
- Test generation (5–30 test cases)

---

### 2.3 ANALYSIS

Agents operating in the ANALYSIS lane perform research, gather context, and produce reports.

**Agents:** PAX (GID-003) — NON-EXECUTING

**Baseline Metrics:**
| Metric | Target | Acceptable Range | Hard Floor |
|--------|--------|------------------|------------|
| `execution_time_ms` | ≤20000 | 10000–35000 | 50000 |
| `quality_score` | ≥0.90 | 0.85–1.00 | 0.80 |
| `scope_compliance` | 100% | 95–100% | 90% |
| `task_completion_rate` | ≥95% | 90–100% | 85% |

**Characteristic Workloads:**
- File reads (10–100 files per analysis)
- Search operations (5–50 queries)
- Report generation (500–2000 words)

---

### 2.4 OPERATIONS

Agents operating in the OPERATIONS lane manage deployments, infrastructure, and system health.

**Agents:** (Reserved for future assignment)

**Baseline Metrics:**
| Metric | Target | Acceptable Range | Hard Floor |
|--------|--------|------------------|------------|
| `execution_time_ms` | ≤15000 | 8000–25000 | 40000 |
| `quality_score` | ≥0.92 | 0.88–1.00 | 0.82 |
| `scope_compliance` | 100% | 98–100% | 95% |
| `task_completion_rate` | ≥98% | 95–100% | 90% |

**Characteristic Workloads:**
- CI/CD operations (1–10 pipeline stages)
- Container management (1–20 container operations)
- Health checks (5–50 endpoints)

---

## 3. Per-Agent Baselines

### 3.1 ATLAS (GID-001)

**Role:** Governance Enforcer  
**Execution Lane:** GOVERNANCE  
**Status:** ACTIVE

**Performance Profile:**
```yaml
AGENT_BASELINE:
  agent_gid: GID-001
  agent_name: ATLAS
  execution_lane: GOVERNANCE
  
  metrics:
    avg_execution_time_ms: 3500
    avg_quality_score: 0.97
    scope_compliance_rate: 1.0
    task_completion_rate: 1.0
    
  workload_profile:
    typical_pacs_per_session: 5-15
    validation_depth: DEEP
    error_tolerance: STRICT
```

---

### 3.2 BENSON (GID-002)

**Role:** Governance Architect  
**Execution Lane:** GOVERNANCE  
**Status:** ACTIVE

**Performance Profile:**
```yaml
AGENT_BASELINE:
  agent_gid: GID-002
  agent_name: BENSON
  execution_lane: GOVERNANCE
  
  metrics:
    avg_execution_time_ms: 4200
    avg_quality_score: 0.96
    scope_compliance_rate: 1.0
    task_completion_rate: 0.98
    
  workload_profile:
    typical_pacs_per_session: 3-10
    validation_depth: DEEP
    error_tolerance: STRICT
```

---

### 3.3 PAX (GID-003)

**Role:** Strategic Analyst  
**Execution Lane:** ANALYSIS  
**Status:** NON-EXECUTING (Advisory Only)

**Performance Profile:**
```yaml
AGENT_BASELINE:
  agent_gid: GID-003
  agent_name: PAX
  execution_lane: ANALYSIS
  
  metrics:
    avg_execution_time_ms: null  # NON-EXECUTING
    avg_quality_score: null
    scope_compliance_rate: null
    task_completion_rate: null
    
  workload_profile:
    role: ADVISORY
    execution_rights: NONE
    output_type: RECOMMENDATIONS_ONLY
```

---

### 3.4 DANA (GID-004)

**Role:** Implementation Specialist  
**Execution Lane:** DEVELOPMENT  
**Status:** NON-EXECUTING (Reserved)

**Performance Profile:**
```yaml
AGENT_BASELINE:
  agent_gid: GID-004
  agent_name: DANA
  execution_lane: DEVELOPMENT
  
  metrics:
    avg_execution_time_ms: null  # NON-EXECUTING
    avg_quality_score: null
    scope_compliance_rate: null
    task_completion_rate: null
    
  workload_profile:
    role: RESERVED
    execution_rights: NONE
    output_type: NONE
```

---

## 4. Quality Score Rubric

Quality scores are computed using the following weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Schema Compliance | 30% | Artifact matches required schema |
| Scope Adherence | 25% | Tasks stayed within defined scope |
| Error Rate | 20% | Inverse of errors encountered |
| Completeness | 15% | All required fields present |
| Documentation | 10% | Adequate inline documentation |

**Calculation:**
```
quality_score = (
    0.30 * schema_compliance +
    0.25 * scope_adherence +
    0.20 * (1.0 - error_rate) +
    0.15 * completeness +
    0.10 * documentation
)
```

---

## 5. Compliance Thresholds

### 5.1 Hard Gates

Artifacts failing these thresholds are REJECTED:

| Condition | Error Code | Action |
|-----------|------------|--------|
| Missing METRICS block | GS_080 | REJECT |
| `quality_score` < 0.75 | GS_084 | REJECT |
| `scope_compliance` = false | GS_085 | REJECT |
| `execution_time_ms` > lane hard floor | WARNING | WARN |

### 5.2 Soft Gates

Artifacts failing these thresholds receive WARNINGS:

| Condition | Warning | Action |
|-----------|---------|--------|
| `quality_score` < lane target | WARN | LOG |
| `execution_time_ms` > lane target | WARN | LOG |
| `task_completion_rate` < 95% | WARN | LOG |

---

## 6. Metrics Collection Protocol

### 6.1 Automatic Collection

All EXECUTABLE artifacts must include a METRICS block that is:

1. **Populated by the executing agent** — Not pre-filled by templates
2. **Accurate to observed execution** — Measured, not estimated
3. **Complete for all required fields** — No null values for required fields

### 6.2 Ledger Recording

Metrics are recorded to the governance ledger via `metrics_extractor.py`:

```bash
python tools/governance/metrics_extractor.py ./docs/governance/wraps/ --baseline GID-001
```

### 6.3 Aggregation Windows

| Window | Use Case |
|--------|----------|
| Per-execution | Immediate validation |
| Per-session | Session rollup reporting |
| Per-day | Daily performance trending |
| Per-week | Weekly baseline recalibration |

---

## 7. Baseline Recalibration

### 7.1 Trigger Conditions

Baselines are recalibrated when:

1. **10+ executions** accumulated since last calibration
2. **Schema changes** affect measurement methodology
3. **Agent upgrades** materially change performance characteristics
4. **Manual override** by ATLAS/BENSON governance directive

### 7.2 Recalibration Process

1. Extract all metrics since last calibration
2. Compute updated averages per lane and agent
3. Validate new baselines against hard floors
4. Update this document via PAC
5. Publish new baselines to ledger

---

## 8. Enforcement Timeline

| Phase | Date | Scope |
|-------|------|-------|
| SOFT | 2025-06-16 | Warnings only, no rejections |
| HARD | 2025-07-01 | Full enforcement, rejections enabled |
| STRICT | 2025-08-01 | Elevated thresholds, tighter ranges |

---

## 9. References

- [GOVERNANCE_METRICS_SCHEMA.md](./GOVERNANCE_METRICS_SCHEMA.md) — Schema definition
- [AGENT_REGISTRY.md](./AGENT_REGISTRY.md) — Agent definitions
- [GOVERNANCE_NAMING_CANON.md](./GOVERNANCE_NAMING_CANON.md) — Naming conventions
- [gate_pack.py](../../tools/governance/gate_pack.py) — Enforcement engine
- [metrics_extractor.py](../../tools/governance/metrics_extractor.py) — Extraction utility

---

**END OF DOCUMENT**
