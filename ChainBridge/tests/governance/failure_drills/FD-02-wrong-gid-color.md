# FD-02: Wrong GID/Color Test

> **Test Case:** GID and color mismatch with registry
> **Expected:** BLOCK_PRECOMMIT / HARD FAIL

---

## 0. RUNTIME_ACTIVATION_ACK

```yaml
RUNTIME_ACTIVATION_ACK:
  runtime_name: "GitHub Copilot"
  runtime_type: "EXECUTION_RUNTIME"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "EXECUTION"
  mode: "EXECUTABLE"
  executes_for_agent: "Dan (GID-07)"
  status: "ACTIVE"
```

---

## 1. AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "Dan"
  gid: "GID-99"
  role: "DevOps & CI/CD Lead"
  color: "PURPLE"
  icon: "🟣"
  authority: "DEPLOYMENT"
  execution_lane: "DEVOPS"
  mode: "EXECUTABLE"
```

---

## 2. PAC_HEADER

```yaml
PAC_HEADER:
  pac_id: "PAC-DAN-FD02-TEST-01"
  agent: "Dan"
  gid: "GID-99"
  color: "PURPLE"
  icon: "🟣"
  authority: "DevOps"
  execution_lane: "DEVOPS"
  mode: "EXECUTABLE"
  drift_tolerance: "ZERO"
  funnel_stage: "TEST"
```

---

**END — INVALID TEST CASE FD-02**
