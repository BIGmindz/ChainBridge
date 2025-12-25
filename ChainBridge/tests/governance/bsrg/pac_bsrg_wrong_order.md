# ═══════════════════════════════════════════════════════════════════════════════
# 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
# PAC-TEST-BSRG-WRONG-ORDER-01 — Test Fixture (BSRG Not Before Checklist)
# 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
# ═══════════════════════════════════════════════════════════════════════════════

## 0) Gateway Checks

This PAC is a test fixture for BSRG validation.
It has BSRG placed AFTER the GOLD_STANDARD_CHECKLIST (wrong order).

---

## 1) Explicit Agent Activation

RUNTIME_ACTIVATION_ACK:
  runtime: "test_runtime"
  mode: "CTO_EXECUTION"
  gid: "N/A"
  authority: "DELEGATED"
  execution_lane: "TEST"
  executes_for_agent: "GID-05"

AGENT_ACTIVATION_ACK:
  agent: "ATLAS"
  agent_name: "ATLAS"
  gid: "GID-05"
  role: "Test Agent"
  color: "BLUE"
  icon: "🟦"
  execution_lane: "TEST"
  mode: "CTO_EXECUTION"

---

## 2) Context & Goal

This is a test PAC with BSRG in wrong position (after checklist).

---

## 3) Tasks

- Test task 1

---

## 4) FORBIDDEN_ACTIONS

- Do not bypass validation

---

TRAINING_SIGNAL:
  signal_type: TEST_SIGNAL
  pattern: TEST_PATTERN
  learning:
    - "This is a test fixture"

---

GOLD_STANDARD_CHECKLIST:
  identity_correct: true
  agent_color_correct: true
  execution_lane_correct: true
  canonical_headers_present: true
  block_order_correct: true
  scope_lock_present: true
  forbidden_actions_present: true
  runtime_activation_ack_present: true
  agent_activation_ack_present: true
  review_gate_declared: true
  training_signal_present: true
  self_certification_present: true
  final_state_declared: true
  checklist_at_end: true
  checklist_all_items_checked: true
  return_permitted: true

BENSON_SELF_REVIEW_GATE:
  gate_id: "BSRG-01"
  reviewer: "BENSON"
  reviewer_gid: "GID-00"
  issuance_policy: "FAIL_CLOSED"
  checklist_results:
    identity_correct: "PASS"
    agent_color_correct: "PASS"
    execution_lane_correct: "PASS"
    canonical_headers_present: "PASS"
    block_order_correct: "PASS"
    scope_lock_present: "PASS"
    forbidden_actions_present: "PASS"
    runtime_activation_ack_present: "PASS"
    agent_activation_ack_present: "PASS"
    review_gate_declared: "PASS"
    training_signal_present: "PASS"
    self_certification_present: "PASS"
    final_state_declared: "PASS"
    checklist_at_end: "PASS"
    checklist_all_items_checked: "PASS"
    return_permitted: "PASS"
  failed_items: []
  override_used: false

═══════════════════════════════════════════════════════════════════════════════
🟦 END — PAC-TEST-BSRG-WRONG-ORDER-01
═══════════════════════════════════════════════════════════════════════════════
