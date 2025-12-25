# ADVERSARIAL TEST: WRAP missing preamble
# Expected: HARD_FAIL with WRP_001

# Work Result and Attestation Proof (WRAP)
# Schema: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA v1.1.0

WRAP HEADER:
  wrap_id: "WRAP-SAM-G32-NO-PREAMBLE-01"
  artifact_type: WRAP
  schema_version: "1.1.0"
  agent: "Sam"
  gid: "GID-06"

BENSON_TRAINING_SIGNAL:
  signal_type: "POSITIVE_REINFORCEMENT"
  lesson: "Test missing preamble"

FINAL_STATE:
  status: "COMPLETE"
