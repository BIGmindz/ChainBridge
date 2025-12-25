# ADVERSARIAL TEST: WRAP with forbidden PAC control block
# Expected: HARD_FAIL with WRP_004

WRAP_INGESTION_PREAMBLE:
  artifact_type: "WRAP"
  schema: "CHAINBRIDGE_CANONICAL_WRAP_SCHEMA"
  schema_version: "1.1.0"
  pac_gates_disabled: true
  mode: "REPORT_ONLY"

WRAP_HEADER:
  wrap_id: "WRAP-SAM-G32-ADVERSARIAL-TEST-01"
  agent: "Sam"
  gid: "GID-06"

# FORBIDDEN BLOCK - BSRG should not appear in WRAP
BENSON_SELF_REVIEW_GATE:
  gate_id: "BSRG-01"
  reviewer: "BENSON"
  reviewer_gid: "GID-00"
  issuance_policy: "FAIL_CLOSED"

BENSON_TRAINING_SIGNAL:
  signal_type: "POSITIVE_REINFORCEMENT"
  lesson: "Test adversarial input"

FINAL_STATE:
  status: "COMPLETE"
