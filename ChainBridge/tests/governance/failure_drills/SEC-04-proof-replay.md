````markdown
# SEC-04: Proof Replay Attack Test

> **Test Case:** Attacker replays previously valid proof
> **Expected:** RUNTIME_BLOCK / HARD FAIL
> **Security Surface:** Replay Detection

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
  type: "PROOF_REPLAY"
  method: "Resubmit previously consumed proof"
  payload:
    proof_id: "proof-replay-001"
    original_timestamp: "2025-12-22T10:00:00Z"
    replay_timestamp: "2025-12-23T10:00:00Z"
    nonce: "nonce-already-used-xyz"
  expected_outcome: "RUNTIME_BLOCK"
```

---

## 3. REPLAY_ATTEMPT

```yaml
REPLAY_ATTEMPT:
  proof_id: "proof-replay-001"
  first_submission: "2025-12-22T10:00:00Z"
  second_submission: "2025-12-23T10:00:00Z"
  nonce: "nonce-already-used-xyz"
  status: "ALREADY_CONSUMED"
```

---

## 4. SECURITY_INVARIANT_VIOLATED

```yaml
SECURITY_INVARIANT:
  rule: "Each proof can only be submitted once"
  enforcement: "ProofIntegrityChecker._check_duplicate()"
  exception: "PDOReplayError"
```

---

## 5. FINAL_STATE

```yaml
FINAL_STATE:
  pac_id: "SEC-04-PROOF-REPLAY"
  status: "MUST_FAIL"
  security_outcome: "BLOCKED"
```

---

**END — SECURITY FAILURE DRILL SEC-04**

````
