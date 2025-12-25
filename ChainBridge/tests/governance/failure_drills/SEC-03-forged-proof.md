````markdown
# SEC-03: Forged Proof Submission Test

> **Test Case:** Attacker submits proof with forged hash
> **Expected:** RUNTIME_BLOCK / HARD FAIL
> **Security Surface:** Proof Integrity Validation

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
  type: "FORGED_PROOF"
  method: "Submit proof with manipulated content hash"
  payload:
    proof_id: "proof-forged-001"
    original_hash: "a1b2c3d4e5f6..."
    forged_hash: "ffffffffffffffff..."
    content_modified: true
  expected_outcome: "RUNTIME_BLOCK"
```

---

## 3. FORGED_PROOF_DATA

```yaml
FORGED_PROOF:
  proof_id: "proof-forged-001"
  event_id: "evt-malicious-001"
  content_hash: "0000000000000000000000000000000000000000000000000000000000000000"
  parent_id: "proof-legitimate-000"
  sequence: 999
  signature: "FORGED_SIGNATURE_DATA"
```

---

## 4. SECURITY_INVARIANT_VIOLATED

```yaml
SECURITY_INVARIANT:
  rule: "Proofs must have valid cryptographic hashes"
  enforcement: "ProofIntegrityChecker.verify_proof()"
  exception: "ProofHashCollisionError"
```

---

## 5. FINAL_STATE

```yaml
FINAL_STATE:
  pac_id: "SEC-03-FORGED-PROOF"
  status: "MUST_FAIL"
  security_outcome: "BLOCKED"
```

---

**END — SECURITY FAILURE DRILL SEC-03**

````
