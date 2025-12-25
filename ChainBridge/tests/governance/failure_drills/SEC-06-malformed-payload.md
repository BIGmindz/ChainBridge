````markdown
# SEC-06: Malformed Payload Injection Test

> **Test Case:** Attacker injects malformed/malicious payloads
> **Expected:** RUNTIME_BLOCK / HARD FAIL
> **Security Surface:** Input Validation & Sanitization

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
  executes_for_agent: "Sam (GID-06)"
  status: "ACTIVE"
```

---

## 1. AGENT_ACTIVATION_ACK

```yaml
AGENT_ACTIVATION_ACK:
  agent_name: "Sam"
  gid: "GID-06"
  role: "Security & Threat Engineer"
  color: "DARK_RED"
  icon: "🟥"
  authority: "SECURITY"
  execution_lane: "SECURITY"
  mode: "EXECUTABLE"
```

---

## 2. ATTACK_VECTOR

```yaml
ATTACK_VECTOR:
  type: "MALFORMED_PAYLOAD_INJECTION"
  method: "Inject code execution payloads"
  payload:
    injection_attempts:
      - type: "code_injection"
        payload: "__import__('os').system('rm -rf /')"
      - type: "eval_injection"
        payload: "eval('malicious_code()')"
      - type: "template_injection"
        payload: "{{config.__class__.__init__.__globals__}}"
      - type: "mongodb_injection"
        payload: "$where: function() { return true; }"
  expected_outcome: "RUNTIME_BLOCK"
```

---

## 3. INJECTION_PAYLOADS

```yaml
INJECTION_PAYLOADS:
  - id: "INJ-01"
    type: "dunder_method"
    payload: "__class__.__mro__[2].__subclasses__()"
    blocked: true
  - id: "INJ-02"
    type: "eval_exec"
    payload: "eval('__import__(\"os\").system(\"id\")')"
    blocked: true
  - id: "INJ-03"
    type: "subprocess"
    payload: "subprocess.Popen(['cat', '/etc/passwd'])"
    blocked: true
  - id: "INJ-04"
    type: "shell_injection"
    payload: "shell=True; cmd='rm -rf /'"
    blocked: true
```

---

## 4. SECURITY_INVARIANT_VIOLATED

```yaml
SECURITY_INVARIANT:
  rule: "Malformed payloads must be rejected"
  enforcement: "RuntimeThreatGuard._scan_for_injection()"
  exception: "PDOTamperingError"
```

---

## 5. FINAL_STATE

```yaml
FINAL_STATE:
  pac_id: "SEC-06-MALFORMED-PAYLOAD"
  status: "MUST_FAIL"
  security_outcome: "BLOCKED"
```

---

**END — SECURITY FAILURE DRILL SEC-06**

````
