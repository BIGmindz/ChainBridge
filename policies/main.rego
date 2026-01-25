# OPA Policy: main.rego
# ChainBridge Digital Inspector General (GID-12)
# PAC-INFRA-P1502: IG Node Infrastructure Build & Deployment
#
# CLASSIFICATION: LAW-tier (Constitutional Enforcement)
# AUTHORITY: SAM [GID-06] + ALEX [GID-08]
# VERSION: 1.0.0
# DATE: 2026-01-25
#
# PURPOSE: Default Deny policy for IG Node
# PATTERN: Fail-closed (uncertainty → block action)
# DOCTRINE: "Every action is guilty until proven compliant."

package chainbridge.ig

import future.keywords.if
import future.keywords.in

# ============================================================================
# DEFAULT POLICY: DENY ALL
# ============================================================================
# Constitutional Principle: "Every action is guilty until proven compliant."
# This is the fail-closed foundation. Specific allow rules must be defined
# in other policy files (constitutional/, agent_specific/, data_access/).

default allow := false

# ============================================================================
# DECISION LOG
# ============================================================================
# Every decision (allow or deny) is logged to OPA decision log
# This ensures full audit trail for Constitutional accountability

decision_log := {
    "decision": allow,
    "timestamp": time.now_ns(),
    "input": input,
    "policy": "main.rego",
    "gid": "GID-12"
}

# ============================================================================
# DENY REASONS (for transparency)
# ============================================================================
# When an action is denied, provide reasoning (Constitutional transparency)

deny[msg] if {
    # No specific allow rule matched
    not allow
    msg := sprintf("DEFAULT DENY: No policy explicitly allows this action. Actor: %v, Action: %v", [input.actor, input.action])
}

# ============================================================================
# BASIC HEALTH CHECK ALLOW (so IG Node itself can function)
# ============================================================================
# Allow health checks from Kubernetes probes
# This is the ONLY allow in main.rego (all other allows are in specific policy files)

allow if {
    input.path == "/health"
    input.method == "GET"
}

allow if {
    input.path == "/ready"
    input.method == "GET"
}

allow if {
    input.path == "/metrics"
    input.method == "GET"
}

# ============================================================================
# IG SELF-LIMIT (Negative Constitution enforcement)
# ============================================================================
# GID-12 CANNOT initiate actions (judicial restraint)

deny[msg] if {
    input.actor == "GID-12"
    input.action_type == "INITIATE"
    msg := "I-GOV-008 VIOLATION: IG cannot initiate actions. Judicial restraint required."
}

# GID-12 CANNOT suggest optimizations (compliance only)
deny[msg] if {
    input.actor == "GID-12"
    contains(lower(input.message), "suggest")
    msg := "I-GOV-010 VIOLATION: IG detected suggesting improvements. ONLY compliance enforcement allowed."
}

deny[msg] if {
    input.actor == "GID-12"
    contains(lower(input.message), "recommend")
    msg := "I-GOV-010 VIOLATION: IG detected making recommendations. ONLY compliance enforcement allowed."
}

deny[msg] if {
    input.actor == "GID-12"
    contains(lower(input.message), "optimize")
    msg := "I-GOV-010 VIOLATION: IG detected optimization attempt. ONLY compliance enforcement allowed."
}

# ============================================================================
# PLACEHOLDER FOR ADDITIONAL POLICIES
# ============================================================================
# Additional allow/deny rules should be defined in:
#
# - policies/constitutional/invariants.rego (I-GOV-001 through I-GOV-010)
# - policies/constitutional/scram_enforcement.rego (I-SCRAM-001 through I-SCRAM-003)
# - policies/constitutional/tgl_enforcement.rego (I-TGL-001 through I-TGL-003)
# - policies/agent_specific/benson_limits.rego (GID-00 execution constraints)
# - policies/agent_specific/alex_governance.rego (GID-08 governance audits)
# - policies/data_access/read_policies.rego (epistemic independence queries)
# - policies/data_access/write_policies.rego (database mutation controls)
# - policies/meta/ig_self_limits.rego (GID-12 Negative Constitution)
#
# This file (main.rego) serves as the DEFAULT DENY foundation.
# All specific permissions must be explicitly granted in other policy files.

# ============================================================================
# LOGGING AND OBSERVABILITY
# ============================================================================
# OPA decision logs are written to /var/log/opa/decisions.log
# Format: JSON (one decision per line)
# Fields: input, result, timestamp, policy_id, bundles

# ============================================================================
# CONSTITUTIONAL ATTESTATION
# ============================================================================
# "This policy IS the Law. Default deny. Fail-closed. No action proceeds
# without explicit Constitutional permission. Uncertainty is non-compliance.
# The IG enforces this mechanically, without discretion or optimization.
# Math > Tests. Logic > Code. Law > Algorithm."
#
# — SAM [GID-06], Security Specialist (Default Deny configuration)
# — ALEX [GID-08], Governance and Compliance AI (Policy framework)
# — JEFFREY [GID-CONST-01], Constitutional Architect (Final approval)
# ============================================================================
