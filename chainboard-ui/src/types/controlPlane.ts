/**
 * ChainBridge Control Plane Types
 * PAC-JEFFREY-P06R: Lint v2 Runtime Enforcement · Gold Standard
 * Supersedes: PAC-JEFFREY-P05R (Law), PAC-JEFFREY-P04
 * GOLD STANDARD · FAIL_CLOSED
 *
 * GOVERNANCE INVARIANTS (CANONICAL):
 * - INV-CP-001: No execution without explicit ACK
 * - INV-CP-002: Missing ACK blocks execution AND settlement
 * - INV-CP-003: All state transitions are deterministic and auditable
 * - INV-CP-004: FAIL_CLOSED on any governance violation
 * - INV-CP-005: BER requires valid WRAP; WRAP requires all ACKs
 * - INV-CP-006: Multi-agent WRAPs required before BER
 * - INV-CP-007: Ledger commit attestation required for finality
 * - INV-CP-008: ACK latency bound to settlement eligibility
 * - INV-CP-009: execution_mode REQUIRED on all BERs (PAC-JEFFREY-P02R)
 * - INV-CP-010: ber_finality REQUIRED (FINAL | PROVISIONAL)
 * - INV-CP-011: Training Signals MANDATORY per agent
 * - INV-CP-012: Positive Closure MANDATORY per agent
 * - INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs (PAC-JEFFREY-P03)
 * - INV-CP-014: Cross-lane execution FORBIDDEN (PAC-JEFFREY-P03)
 * - INV-CP-015: Implicit agent activation FORBIDDEN (PAC-JEFFREY-P03)
 * - INV-CP-016: PACK immutability ENFORCED (PAC-JEFFREY-P03)
 * - INV-CP-017: SettlementReadinessVerdict REQUIRED before BER FINAL (PAC-JEFFREY-P04)
 * - INV-CP-018: Settlement eligibility is BINARY (PAC-JEFFREY-P04)
 * - INV-CP-019: No human override on settlement verdict (PAC-JEFFREY-P04)
 * - INV-CP-020: Verdict must be machine-computed (PAC-JEFFREY-P04)
 *
 * LINT v2 INVARIANT CLASSES (PAC-JEFFREY-P05R LAW):
 * - S-INV: Structural — Schema validation, required fields
 * - M-INV: Semantic — Meaning/intent validation
 * - X-INV: Cross-Artifact — Inter-document consistency
 * - T-INV: Temporal — Ordering, timestamps, sequences
 * - A-INV: Authority — GID/lane authorization
 * - F-INV: Finality — BER/settlement eligibility
 * - C-INV: Training — Signal emission compliance
 *
 * SCHEMA REFERENCES (EXPLICIT PINNING):
 * - PAC Schema: CHAINBRIDGE_CANONICAL_PAC_SCHEMA@v1.0.0
 * - WRAP Schema: CHAINBRIDGE_CANONICAL_WRAP_SCHEMA@v1.0.0
 * - BER Schema: CHAINBRIDGE_CANONICAL_BER_SCHEMA@v1.0.0
 * - RG-01 Schema: RG01_SCHEMA@v1.0.0
 * - BSRG-01 Schema: BSRG01_SCHEMA@v1.0.0
 * - ACK Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
 * - Training Signal Schema: GOVERNANCE_TRAINING_SIGNAL_SCHEMA@v1.0.0
 * - Positive Closure Schema: POSITIVE_CLOSURE_SCHEMA@v1.0.0
 * - Settlement Verdict Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
 * - Lint v2 Schema: CHAINBRIDGE_LINT_V2_INVARIANT_SCHEMA@v1.0.0
 *
 * Author: Benson Execution Orchestrator (GID-00)
 * Frontend Lane: SONNY (GID-02)
 */

// ═══════════════════════════════════════════════════════════════════════════════
// PAC LIFECYCLE STATES
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Deterministic PAC lifecycle states.
 * 
 * State transitions are strictly ordered:
 * DRAFT → ACK_PENDING → EXECUTING → WRAP_PENDING → WRAP_SUBMITTED → BER_ISSUED → SETTLED
 */
export type PACLifecycleState =
  | 'DRAFT'               // PAC created, not yet dispatched
  | 'ACK_PENDING'         // Awaiting agent ACK
  | 'EXECUTING'           // Agent(s) actively executing
  | 'WRAP_PENDING'        // Execution complete, awaiting WRAP
  | 'WRAP_SUBMITTED'      // WRAP submitted, pending validation
  | 'WRAP_VALIDATED'      // WRAP validated, BER eligible
  | 'BER_ISSUED'          // BER generated
  | 'SETTLED'             // Settlement complete
  // Fail states (terminal)
  | 'ACK_TIMEOUT'         // ACK deadline expired
  | 'ACK_REJECTED'        // Agent explicitly rejected ACK
  | 'EXECUTION_FAILED'    // Execution failed
  | 'WRAP_REJECTED'       // WRAP validation failed
  | 'SETTLEMENT_BLOCKED'; // Governance violation

/**
 * Agent acknowledgment states.
 */
export type AgentACKState =
  | 'PENDING'      // ACK requested, awaiting response
  | 'ACKNOWLEDGED' // Agent explicitly ACKed
  | 'REJECTED'     // Agent explicitly rejected
  | 'TIMEOUT';     // ACK deadline expired

/**
 * WRAP validation states.
 */
export type WRAPValidationState =
  | 'PENDING'      // WRAP not yet submitted
  | 'SUBMITTED'    // WRAP submitted, validation in progress
  | 'VALID'        // WRAP passed all validation checks
  | 'INVALID'      // WRAP failed validation
  | 'SCHEMA_ERROR' // WRAP failed schema validation
  | 'MISSING_ACK'; // WRAP rejected due to missing ACK

/**
 * BER generation states.
 */
export type BERState =
  | 'NOT_ELIGIBLE' // Prerequisites not met
  | 'ELIGIBLE'     // Ready for BER generation
  | 'PENDING'      // BER generation in progress
  | 'ISSUED'       // BER successfully issued
  | 'CHALLENGED'   // BER under challenge
  | 'REVOKED';     // BER revoked

/**
 * Settlement eligibility states.
 */
export type SettlementEligibility =
  | 'BLOCKED'  // Cannot settle - governance violation
  | 'PENDING'  // Prerequisites incomplete
  | 'ELIGIBLE' // Ready for settlement
  | 'SETTLED'; // Settlement complete

// ═══════════════════════════════════════════════════════════════════════════════
// DATA TRANSFER OBJECTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Agent ACK record.
 */
export interface AgentACKDTO {
  ack_id: string;
  pac_id: string;
  agent_gid: string;
  agent_name: string;
  order_id: string;
  state: AgentACKState;
  requested_at: string;
  deadline_at: string;
  acknowledged_at: string | null;
  rejection_reason: string | null;
  latency_ms: number | null;
  ack_hash: string;
}

/**
 * WRAP artifact record.
 */
export interface WRAPArtifactDTO {
  wrap_id: string;
  pac_id: string;
  agent_gid: string;
  submitted_at: string;
  validation_state: WRAPValidationState;
  validated_at: string | null;
  artifact_refs: string[];
  validation_errors: string[];
  wrap_hash: string;
}

/**
 * BER record per PAC-JEFFREY-P02R Section 9.
 * 
 * MANDATORY FIELDS:
 * - execution_mode: EXECUTING | NON_EXECUTING
 * - execution_barrier: ALL_WRAPS_BEFORE_RG01 | NONE
 * - ber_finality: FINAL | PROVISIONAL
 * - ledger_commit_status: PENDING | COMMITTED
 * - ledger_commit_hash (if FINAL)
 */
export interface BERRecordDTO {
  ber_id: string;
  pac_id: string;
  wrap_id: string;
  state: BERState;
  
  // PAC-JEFFREY-P02R: Execution mode (MANDATORY)
  execution_mode: 'EXECUTING' | 'NON_EXECUTING';
  execution_barrier: 'ALL_WRAPS_BEFORE_RG01' | 'NONE';
  
  // PAC-JEFFREY-P02R: BER finality (MANDATORY)
  ber_finality: 'FINAL' | 'PROVISIONAL';
  ledger_commit_status: 'PENDING' | 'COMMITTED';
  ledger_commit_hash: string | null;
  
  // PAC-JEFFREY-P02R: WRAP hash set (MANDATORY)
  wrap_hash_set: string[];
  
  // PAC-JEFFREY-P02R: Review gate results (MANDATORY)
  rg01_result: 'PASS' | 'FAIL' | null;
  bsrg01_result: 'PASS' | 'FAIL' | null;
  
  // PAC-JEFFREY-P02R: Training/Closure digests (MANDATORY)
  training_signal_digest: string | null;
  positive_closure_digest: string | null;
  
  issued_at: string | null;
  issuer_gid: string;
  settlement_eligible: boolean;
  ber_hash: string;
}

/**
 * Full ACK evidence record per PAC-JEFFREY-P02R Section 1.
 * 
 * Schema: AGENT_ACK_EVIDENCE_SCHEMA@v1.0.0
 */
export interface AgentACKEvidenceDTO {
  agent_id: string;
  gid: string;
  lane: 'orchestration' | 'backend' | 'frontend' | 'ci_cd' | 'security';
  mode: 'EXECUTING' | 'NON_EXECUTING';
  timestamp: string;  // ISO-8601 concrete timestamp
  ack_latency_ms: number;
  authorization_scope: string;
  evidence_hash: string;
}

/**
 * Training Signal per PAC-JEFFREY-P02R Section 11.
 * 
 * REQUIRED FROM ALL AGENTS.
 * Append-only. Immutable.
 */
export interface TrainingSignalDTO {
  signal_id: string;
  pac_id: string;
  agent_gid: string;
  agent_name: string;
  signal_type: 'CORRECTION' | 'LEARNING' | 'CONSTRAINT';
  observation: string;
  constraint_learned: string;
  recommended_enforcement: string;
  emitted_at: string;
  signal_hash: string;
}

/**
 * Positive Closure per PAC-JEFFREY-P02R Section 12.
 * 
 * REQUIRED FROM ALL AGENTS.
 * No Positive Closure → PAC INCOMPLETE.
 */
export interface PositiveClosureDTO {
  closure_id: string;
  pac_id: string;
  agent_gid: string;
  agent_name: string;
  scope_complete: boolean;
  no_violations: boolean;
  ready_for_next_stage: boolean;
  emitted_at: string;
  closure_hash: string;
  is_valid: boolean;
}

/**
 * ACK summary statistics.
 */
export interface ACKSummary {
  total: number;
  acknowledged: number;
  pending: number;
  rejected: number;
  timeout: number;
  latency: {
    min_ms: number | null;
    max_ms: number | null;
    avg_ms: number | null;
  };
}

/**
 * State transition record.
 */
export interface StateTransitionRecord {
  from_state: PACLifecycleState;
  to_state: PACLifecycleState;
  timestamp: string;
  reason: string;
  actor: string;
}

/**
 * Complete Control Plane state.
 */
export interface ControlPlaneStateDTO {
  pac_id: string;
  runtime_id: string;
  lifecycle_state: PACLifecycleState;
  agent_acks: Record<string, AgentACKDTO>;
  wraps: Record<string, WRAPArtifactDTO>;
  ber: BERRecordDTO | null;
  settlement_eligibility: SettlementEligibility;
  settlement_block_reason: string | null;
  created_at: string;
  updated_at: string;
  ack_summary: ACKSummary;
  state_transitions: StateTransitionRecord[];
}

// ═══════════════════════════════════════════════════════════════════════════════
// MULTI-AGENT WRAP AGGREGATION (PAC-JEFFREY-P01 SECTION 7)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Multi-agent WRAP set response.
 */
export interface MultiAgentWRAPSetDTO {
  pac_id: string;
  schema_version: string;
  expected_agents: string[];
  is_complete: boolean;
  missing_agents: string[];
  all_valid: boolean;
  aggregation_started_at: string;
  aggregation_completed_at: string | null;
  set_hash: string;
  collected_wraps: {
    wrap_id: string;
    agent_gid: string;
    submitted_at: string;
    validation_state: WRAPValidationState;
    validated_at: string | null;
    artifact_refs: string[];
    wrap_hash: string;
  }[];
  governance_invariant: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// REVIEW GATE RG-01 (PAC-JEFFREY-P01 SECTION 8)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * RG-01 pass condition.
 */
export interface RG01PassCondition {
  condition: 'wrap_schema_valid' | 'all_mandatory_blocks' | 'no_forbidden_actions';
  status: boolean | null;
}

/**
 * RG-01 Review Gate response.
 */
export interface ReviewGateRG01DTO {
  pac_id: string;
  gate_id: string;
  gate_type: 'RG-01';
  reviewer: string;
  result: 'PASS' | 'FAIL' | null;
  evaluated_at: string | null;
  pass_conditions: RG01PassCondition[];
  fail_reasons: string[];
  fail_action: string;
  wrap_set_complete: boolean;
  wrap_set_valid: boolean;
  // PAC-JEFFREY-P02R: Training/Closure validation
  training_signals_present: boolean;
  positive_closures_present: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// BSRG-01 SELF-REVIEW GATE (PAC-JEFFREY-P02R SECTION 8)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * BSRG-01 Benson Self-Review Gate response per PAC-JEFFREY-P02R.
 * 
 * MANDATORY ATTESTATIONS:
 * - No override
 * - No drift
 * - Parallel semantics respected
 * - Training + Closure verified
 */
export interface BSRG01DTO {
  pac_id: string;
  gate_id: string;
  gate_type: 'BSRG-01';
  self_attestation: boolean;
  self_attestation_required: boolean;
  violations: 'NONE' | string[];
  training_signals: Record<string, unknown>[];
  training_signal_emission_required: boolean;
  attested_at: string | null;
  // PAC-JEFFREY-P02R: Mandatory attestations
  no_override: boolean;
  no_drift: boolean;
  parallel_semantics_respected: boolean;
  training_closure_verified: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACK LATENCY SETTLEMENT BINDING (PAC-JEFFREY-P02R SECTION 6)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ACK latency eligibility response.
 */
export interface ACKLatencyEligibilityDTO {
  pac_id: string;
  latency_eligible: boolean;
  latency_reason: string | null;
  threshold_ms: number;
  max_latency_ms: number | null;
  latency_summary: {
    min_ms: number | null;
    max_ms: number | null;
    avg_ms: number | null;
  };
  agent_latencies: Record<string, number | null>;
  governance_invariant: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEDGER COMMIT ATTESTATION (PAC-JEFFREY-P02R SECTION 10)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Ledger attestation response.
 */
export interface LedgerAttestationDTO {
  pac_id: string;
  attestation_status: 'PENDING' | 'COMMITTED';
  attestation_id: string | null;
  committed: boolean;
  committed_at?: string;
  ledger_block: string | null;
  wrap_hashes?: string[];
  ber_hash?: string;
  attestation_hash?: string;
  governance_invariant: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TRAINING SIGNALS RESPONSE (PAC-JEFFREY-P02R SECTION 11)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Training Signals response.
 */
export interface TrainingSignalsResponseDTO {
  pac_id: string;
  schema_version: string;
  total_signals: number;
  signals: TrainingSignalDTO[];
  digest: string | null;
  governance_invariant: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// POSITIVE CLOSURES RESPONSE (PAC-JEFFREY-P02R SECTION 12)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Positive Closures response.
 */
export interface PositiveClosuresResponseDTO {
  pac_id: string;
  schema_version: string;
  total_closures: number;
  all_valid: boolean;
  closures: PositiveClosureDTO[];
  digest: string | null;
  governance_invariant: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACK EVIDENCE RESPONSE (PAC-JEFFREY-P02R SECTION 1)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * ACK Evidence response.
 */
export interface ACKEvidenceResponseDTO {
  pac_id: string;
  schema_version: string;
  total_evidence: number;
  evidence: AgentACKEvidenceDTO[];
  governance_invariant: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE SUMMARY (PAC-JEFFREY-P02R)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Gate status in governance summary.
 */
export type GateStatus = 'PASS' | 'FAIL' | 'PENDING' | 'BLOCKED' | 'COMMITTED';

/**
 * Individual gate summary.
 */
export interface GateSummary {
  name: string;
  status: GateStatus;
  [key: string]: unknown;
}

/**
 * Positive closure conditions per PAC-JEFFREY-P02R.
 */
export interface PositiveClosureConditions {
  all_wraps_pass_rg01: boolean;
  bsrg01_attested: boolean;
  ber_issued: boolean;
  ledger_committed: boolean;
  // PAC-JEFFREY-P02R additions
  training_signals_complete: boolean;
  positive_closures_complete: boolean;
}

/**
 * Schema references with explicit pinning.
 */
export interface SchemaReferences {
  pac: string;
  wrap: string;
  ber: string;
  rg01: string;
  bsrg01: string;
  ack: string;
}

/**
 * Complete governance summary response per PAC-JEFFREY-P02R.
 */
export interface GovernanceSummaryDTO {
  pac_id: string;
  pac_title: string;
  governance_tier: string;
  fail_mode: string;
  // PAC-JEFFREY-P02R additions
  execution_mode: string;
  execution_barrier: string;
  lifecycle_state: PACLifecycleState;
  gates: {
    ack_gate: GateSummary;
    wrap_gate: GateSummary;
    rg01_gate: GateSummary & {
      training_signals_present: boolean;
      positive_closures_present: boolean;
    };
    bsrg01_gate: GateSummary & {
      no_override: boolean;
      no_drift: boolean;
      parallel_semantics: boolean;
    };
    latency_gate: GateSummary;
    ledger_gate: GateSummary;
    // PAC-JEFFREY-P02R additions
    training_gate: GateSummary & { count: number };
    closure_gate: GateSummary & { count: number };
  };
  settlement_eligibility: SettlementEligibility;
  positive_closure: PositiveClosureConditions;
  schema_references: SchemaReferences;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DISPLAY CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Lifecycle state display configuration.
 */
export const LIFECYCLE_STATE_CONFIG: Record<PACLifecycleState, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
  isTerminal: boolean;
  isFailed: boolean;
}> = {
  DRAFT: {
    label: 'Draft',
    color: 'text-gray-400',
    bgColor: 'bg-gray-700',
    icon: '📝',
    isTerminal: false,
    isFailed: false,
  },
  ACK_PENDING: {
    label: 'ACK Pending',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/50',
    icon: '⏳',
    isTerminal: false,
    isFailed: false,
  },
  EXECUTING: {
    label: 'Executing',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    icon: '⚙️',
    isTerminal: false,
    isFailed: false,
  },
  WRAP_PENDING: {
    label: 'WRAP Pending',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/50',
    icon: '📦',
    isTerminal: false,
    isFailed: false,
  },
  WRAP_SUBMITTED: {
    label: 'WRAP Submitted',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-900/50',
    icon: '📨',
    isTerminal: false,
    isFailed: false,
  },
  WRAP_VALIDATED: {
    label: 'WRAP Validated',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/50',
    icon: '✅',
    isTerminal: false,
    isFailed: false,
  },
  BER_ISSUED: {
    label: 'BER Issued',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '📜',
    isTerminal: false,
    isFailed: false,
  },
  SETTLED: {
    label: 'Settled',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-900/50',
    icon: '💰',
    isTerminal: true,
    isFailed: false,
  },
  ACK_TIMEOUT: {
    label: 'ACK Timeout',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '⏰',
    isTerminal: true,
    isFailed: true,
  },
  ACK_REJECTED: {
    label: 'ACK Rejected',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '❌',
    isTerminal: true,
    isFailed: true,
  },
  EXECUTION_FAILED: {
    label: 'Execution Failed',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '💥',
    isTerminal: true,
    isFailed: true,
  },
  WRAP_REJECTED: {
    label: 'WRAP Rejected',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '🚫',
    isTerminal: true,
    isFailed: true,
  },
  SETTLEMENT_BLOCKED: {
    label: 'Settlement Blocked',
    color: 'text-red-500',
    bgColor: 'bg-red-900/70',
    icon: '🛑',
    isTerminal: true,
    isFailed: true,
  },
};

/**
 * ACK state display configuration.
 */
export const ACK_STATE_CONFIG: Record<AgentACKState, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  PENDING: {
    label: 'Pending',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/50',
    icon: '⏳',
  },
  ACKNOWLEDGED: {
    label: 'Acknowledged',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '✅',
  },
  REJECTED: {
    label: 'Rejected',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '❌',
  },
  TIMEOUT: {
    label: 'Timeout',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '⏰',
  },
};

/**
 * WRAP validation state display configuration.
 */
export const WRAP_STATE_CONFIG: Record<WRAPValidationState, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  PENDING: {
    label: 'Pending',
    color: 'text-gray-400',
    bgColor: 'bg-gray-700',
    icon: '📦',
  },
  SUBMITTED: {
    label: 'Validating',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    icon: '🔍',
  },
  VALID: {
    label: 'Valid',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '✅',
  },
  INVALID: {
    label: 'Invalid',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '❌',
  },
  SCHEMA_ERROR: {
    label: 'Schema Error',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '⚠️',
  },
  MISSING_ACK: {
    label: 'Missing ACK',
    color: 'text-red-500',
    bgColor: 'bg-red-900/70',
    icon: '🚫',
  },
};

/**
 * BER state display configuration.
 */
export const BER_STATE_CONFIG: Record<BERState, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  NOT_ELIGIBLE: {
    label: 'Not Eligible',
    color: 'text-gray-400',
    bgColor: 'bg-gray-700',
    icon: '⏸️',
  },
  ELIGIBLE: {
    label: 'Eligible',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/50',
    icon: '🎯',
  },
  PENDING: {
    label: 'Generating',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/50',
    icon: '⚙️',
  },
  ISSUED: {
    label: 'Issued',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '📜',
  },
  CHALLENGED: {
    label: 'Challenged',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/50',
    icon: '⚔️',
  },
  REVOKED: {
    label: 'Revoked',
    color: 'text-red-400',
    bgColor: 'bg-red-900/50',
    icon: '🗑️',
  },
};

/**
 * Settlement eligibility display configuration.
 */
export const SETTLEMENT_CONFIG: Record<SettlementEligibility, {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  BLOCKED: {
    label: 'Blocked',
    color: 'text-red-500',
    bgColor: 'bg-red-900/70',
    icon: '🛑',
  },
  PENDING: {
    label: 'Pending',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/50',
    icon: '⏳',
  },
  ELIGIBLE: {
    label: 'Eligible',
    color: 'text-green-400',
    bgColor: 'bg-green-900/50',
    icon: '✅',
  },
  SETTLED: {
    label: 'Settled',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-900/50',
    icon: '💰',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// PAC-JEFFREY-P03 TYPES — CONTROL PLANE HARDENING
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Execution mode per PAC-JEFFREY-P03 Section 2.
 */
export type ExecutionMode = 'PARALLEL' | 'SEQUENTIAL';

/**
 * Execution barrier type per PAC-JEFFREY-P03 Section 2.
 */
export type ExecutionBarrierType = 'AGENT_ACK_BARRIER' | 'WRAP_COMPLETE_BARRIER' | 'NONE';

/**
 * Barrier release condition per PAC-JEFFREY-P03 Section 2.
 */
export type BarrierReleaseCondition = 
  | 'ALL_REQUIRED_AGENT_ACKS_PRESENT'
  | 'ALL_WRAPS_COLLECTED'
  | 'MANUAL_RELEASE';

/**
 * Agent lane assignments per PAC-JEFFREY-P03 Section 3.
 * INV-CP-014: Cross-lane execution FORBIDDEN
 */
export type AgentLane = 'orchestration' | 'backend' | 'frontend' | 'ci_cd' | 'security';

/**
 * Execution Barrier per PAC-JEFFREY-P03 Section 2.
 * 
 * INV-CP-013: AGENT_ACK_BARRIER release requires ALL agent ACKs
 */
export interface ExecutionBarrierDTO {
  barrier_id: string;
  pac_id: string;
  execution_mode: ExecutionMode;
  barrier_type: ExecutionBarrierType;
  release_condition: BarrierReleaseCondition;
  required_agents: string[];
  received_acks: Record<string, AgentACKEvidenceDTO>;
  missing_acks: string[];
  released: boolean;
  released_at: string | null;
  created_at: string;
  barrier_hash: string;
}

/**
 * PACK Immutability Attestation per PAC-JEFFREY-P03 Section 11.
 * 
 * INV-CP-016: PACK_IMMUTABLE = true
 */
export interface PackImmutabilityDTO {
  attestation_id: string;
  pac_id: string;
  pack_hash: string;
  ordering_verified: boolean;
  immutable: boolean;
  attested_at: string;
  attester_gid: string;
  component_hashes: Record<string, string>;
  attestation_hash: string;
}

/**
 * Positive Closure Checklist per PAC-JEFFREY-P03 Section 10.
 * 
 * All items must PASS for valid closure.
 */
export interface PositiveClosureChecklistDTO {
  checklist_id: string;
  pac_id: string;
  items: {
    'PAG-01_ACKS_COMPLETE': 'PASS' | 'FAIL';
    'ALL_REQUIRED_WRAPS': 'PASS' | 'FAIL';
    'RG-01': 'PASS' | 'FAIL';
    'BSRG-01': 'PASS' | 'FAIL';
    'BER_ISSUED': 'PASS' | 'FAIL';
    'LEDGER_COMMIT': 'PASS' | 'PROVISIONAL' | 'PENDING';
  };
  overall_status: 'PASS' | 'FAIL' | 'PENDING';
  evaluated_at: string | null;
}

/**
 * Agent Lane Assignment per PAC-JEFFREY-P03 Section 3.
 */
export interface AgentLaneAssignment {
  agent: string;
  gid: string;
  lane: AgentLane;
  mode: 'EXECUTING' | 'NON_EXECUTING';
}

/**
 * Required WRAP obligation per PAC-JEFFREY-P03 Section 6.
 */
export interface RequiredWRAPDTO {
  wrap_id: string;
  agent: string;
  gid: string;
  status: WRAPValidationState | 'PENDING';
  wrap_hash?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT READINESS VERDICT (PAC-JEFFREY-P04)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Settlement readiness status per PAC-JEFFREY-P04.
 * 
 * INV-CP-018: Settlement eligibility is BINARY - ELIGIBLE or BLOCKED
 */
export type SettlementReadinessStatus = 'ELIGIBLE' | 'BLOCKED';

/**
 * Blocking reason types per PAC-JEFFREY-P04.
 */
export type SettlementBlockingReason =
  | 'MISSING_ACK'
  | 'ACK_TIMEOUT'
  | 'ACK_REJECTED'
  | 'ACK_LATENCY_EXCEEDED'
  | 'MISSING_WRAP'
  | 'WRAP_VALIDATION_FAILED'
  | 'RG01_FAILED'
  | 'RG01_NOT_EVALUATED'
  | 'BSRG01_FAILED'
  | 'BSRG01_NOT_ATTESTED'
  | 'BER_NOT_ISSUED'
  | 'BER_FINALITY_PROVISIONAL'
  | 'LEDGER_COMMIT_PENDING'
  | 'TRAINING_SIGNALS_MISSING'
  | 'POSITIVE_CLOSURE_MISSING'
  | 'POSITIVE_CLOSURE_INVALID'
  | 'GOVERNANCE_VIOLATION';

/**
 * Evidence for a specific blocking reason.
 */
export interface BlockingReasonEvidenceDTO {
  reason: SettlementBlockingReason;
  description: string;
  source_type: 'WRAP' | 'BER' | 'RG01' | 'BSRG01' | 'ACK' | 'LEDGER';
  source_ref: string | null;
  detected_at: string;
}

/**
 * Settlement Readiness Verdict per PAC-JEFFREY-P04 Section 4.
 * 
 * Schema: SETTLEMENT_READINESS_VERDICT_SCHEMA@v1.0.0
 * 
 * INVARIANTS:
 * - INV-CP-017: Required before BER FINAL
 * - INV-CP-018: Binary - ELIGIBLE or BLOCKED
 * - INV-CP-019: No human override allowed
 * - INV-CP-020: Must be machine-computed
 */
export interface SettlementReadinessVerdictDTO {
  verdict_id: string;
  pac_id: string;
  status: SettlementReadinessStatus;
  is_eligible: boolean;
  blocking_reasons: BlockingReasonEvidenceDTO[];
  blocking_count: number;
  source_evidence: {
    wrap_refs: string[];
    ber_ref: string | null;
    rg01_ref: string | null;
    bsrg01_ref: string | null;
  };
  computation: {
    computed_at: string;
    computed_by: string;
    method: 'DETERMINISTIC';
  };
  verdict_hash: string;
}

/**
 * Display configuration for blocking reasons.
 */
export const BLOCKING_REASON_CONFIG: Record<SettlementBlockingReason, {
  label: string;
  severity: 'critical' | 'high' | 'medium';
  icon: string;
  color: string;
}> = {
  MISSING_ACK: {
    label: 'Missing ACK',
    severity: 'critical',
    icon: '❌',
    color: 'text-red-500',
  },
  ACK_TIMEOUT: {
    label: 'ACK Timeout',
    severity: 'critical',
    icon: '⏱️',
    color: 'text-red-500',
  },
  ACK_REJECTED: {
    label: 'ACK Rejected',
    severity: 'critical',
    icon: '🚫',
    color: 'text-red-500',
  },
  ACK_LATENCY_EXCEEDED: {
    label: 'ACK Latency Exceeded',
    severity: 'high',
    icon: '⚠️',
    color: 'text-orange-500',
  },
  MISSING_WRAP: {
    label: 'Missing WRAP',
    severity: 'critical',
    icon: '📦',
    color: 'text-red-500',
  },
  WRAP_VALIDATION_FAILED: {
    label: 'WRAP Validation Failed',
    severity: 'critical',
    icon: '❌',
    color: 'text-red-500',
  },
  RG01_FAILED: {
    label: 'RG-01 Failed',
    severity: 'critical',
    icon: '🚨',
    color: 'text-red-500',
  },
  RG01_NOT_EVALUATED: {
    label: 'RG-01 Not Evaluated',
    severity: 'high',
    icon: '⏳',
    color: 'text-orange-500',
  },
  BSRG01_FAILED: {
    label: 'BSRG-01 Failed',
    severity: 'critical',
    icon: '🚨',
    color: 'text-red-500',
  },
  BSRG01_NOT_ATTESTED: {
    label: 'BSRG-01 Not Attested',
    severity: 'high',
    icon: '⏳',
    color: 'text-orange-500',
  },
  BER_NOT_ISSUED: {
    label: 'BER Not Issued',
    severity: 'high',
    icon: '📄',
    color: 'text-orange-500',
  },
  BER_FINALITY_PROVISIONAL: {
    label: 'BER Provisional',
    severity: 'high',
    icon: '⚠️',
    color: 'text-yellow-500',
  },
  LEDGER_COMMIT_PENDING: {
    label: 'Ledger Commit Pending',
    severity: 'medium',
    icon: '📒',
    color: 'text-yellow-500',
  },
  TRAINING_SIGNALS_MISSING: {
    label: 'Training Signals Missing',
    severity: 'high',
    icon: '📡',
    color: 'text-orange-500',
  },
  POSITIVE_CLOSURE_MISSING: {
    label: 'Positive Closure Missing',
    severity: 'high',
    icon: '✅',
    color: 'text-orange-500',
  },
  POSITIVE_CLOSURE_INVALID: {
    label: 'Positive Closure Invalid',
    severity: 'critical',
    icon: '❌',
    color: 'text-red-500',
  },
  GOVERNANCE_VIOLATION: {
    label: 'Governance Violation',
    severity: 'critical',
    icon: '⛔',
    color: 'text-red-600',
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Format timestamp to human-readable string.
 */
export function formatTimestamp(iso: string | null): string {
  if (!iso) return '—';
  try {
    const date = new Date(iso);
    return date.toLocaleString();
  } catch {
    return '—';
  }
}

/**
 * Format latency in milliseconds.
 */
export function formatLatency(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

/**
 * Check if ACK is overdue.
 */
export function isACKOverdue(ack: AgentACKDTO): boolean {
  if (ack.state !== 'PENDING') return false;
  const deadline = new Date(ack.deadline_at);
  return new Date() > deadline;
}

/**
 * Get time remaining until ACK deadline.
 */
export function getACKTimeRemaining(ack: AgentACKDTO): string {
  if (ack.state !== 'PENDING') return '—';
  const deadline = new Date(ack.deadline_at);
  const now = new Date();
  const diff = deadline.getTime() - now.getTime();
  
  if (diff <= 0) return 'OVERDUE';
  
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LINT V2 INVARIANT TYPES (PAC-JEFFREY-P06R)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Lint v2 Invariant Class
 * 7 canonical classes per PAC-JEFFREY-P05R law
 */
export type LintV2InvariantClass =
  | 'S-INV'  // Structural — Schema validation, required fields
  | 'M-INV'  // Semantic — Meaning/intent validation
  | 'X-INV'  // Cross-Artifact — Inter-document consistency
  | 'T-INV'  // Temporal — Ordering, timestamps, sequences
  | 'A-INV'  // Authority — GID/lane authorization
  | 'F-INV'  // Finality — BER/settlement eligibility
  | 'C-INV'; // Training — Signal emission compliance

/**
 * Lint v2 Enforcement Points
 * 5 runtime enforcement checkpoints
 */
export type LintV2EnforcementPoint =
  | 'PAC_ADMISSION'       // PAC intake validation
  | 'WRAP_INGESTION'      // WRAP artifact validation
  | 'RG01_EVALUATION'     // Review gate compliance
  | 'BER_ELIGIBILITY'     // BER generation prereqs
  | 'SETTLEMENT_READINESS'; // Final settlement gate

/**
 * Lint v2 Evaluation Result
 * Binary only — NO WARNINGS in production
 */
export type LintV2EvaluationResult = 'PASS' | 'FAIL';

/**
 * Lint v2 Severity
 * All invariants are CRITICAL — binary enforcement
 */
export type LintV2Severity = 'CRITICAL';

/**
 * Individual invariant definition
 */
export interface LintV2InvariantDTO {
  invariant_id: string;
  invariant_class: LintV2InvariantClass;
  name: string;
  description: string;
  enforcement_points: LintV2EnforcementPoint[];
  severity: LintV2Severity;
  schema_version: string;
}

/**
 * Invariant violation record
 */
export interface LintV2ViolationDTO {
  violation_id: string;
  invariant_id: string;
  invariant_class: LintV2InvariantClass;
  enforcement_point: LintV2EnforcementPoint;
  artifact_id: string;
  artifact_type: string;
  description: string;
  context: Record<string, unknown>;
  detected_at: string;
  violation_hash: string;
}

/**
 * Lint v2 Evaluation Report
 */
export interface LintV2EvaluationReportDTO {
  report_id: string;
  enforcement_point: LintV2EnforcementPoint;
  artifact_id: string;
  artifact_type: string;
  result: LintV2EvaluationResult;
  is_pass: boolean;
  violations: LintV2ViolationDTO[];
  violation_count: number;
  invariants_evaluated: string[];
  invariants_count: number;
  evaluation_started_at: string;
  evaluation_completed_at: string | null;
  evaluation_duration_ms: number | null;
  report_hash: string;
}

/**
 * Complete invariant registry
 */
export interface LintV2RegistryDTO {
  schema_version: string;
  total_invariants: number;
  by_class: Record<LintV2InvariantClass, number>;
  by_enforcement_point: Record<LintV2EnforcementPoint, number>;
  invariants: LintV2InvariantDTO[];
}

/**
 * Lint v2 Training Signal
 */
export interface LintV2TrainingSignalDTO {
  signal_id: string;
  signal_type: string;
  pac_id: string;
  agent_gid: string;
  enforcement_point: LintV2EnforcementPoint;
  invariants_evaluated: string[];
  violations_detected: string[];
  result: LintV2EvaluationResult;
  timestamp: string;
}

/**
 * Lint v2 Engine Status
 */
export interface LintV2EngineStatusDTO {
  engine_version: string;
  schema_version: string;
  mode: string;
  fail_mode: string;
  warnings_enabled: boolean;
  total_invariants: number;
  enforcement_points: LintV2EnforcementPoint[];
  active: boolean;
}

/**
 * Lint v2 Invariant class configuration for UI
 */
export const LINT_V2_CLASS_CONFIG: Record<LintV2InvariantClass, {
  label: string;
  description: string;
  color: string;
  bgColor: string;
  icon: string;
}> = {
  'S-INV': {
    label: 'Structural',
    description: 'Schema validation, required fields',
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/30',
    icon: '🏗️',
  },
  'M-INV': {
    label: 'Semantic',
    description: 'Meaning/intent validation',
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/30',
    icon: '🧠',
  },
  'X-INV': {
    label: 'Cross-Artifact',
    description: 'Inter-document consistency',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-900/30',
    icon: '🔗',
  },
  'T-INV': {
    label: 'Temporal',
    description: 'Ordering, timestamps, sequences',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-900/30',
    icon: '⏱️',
  },
  'A-INV': {
    label: 'Authority',
    description: 'GID/lane authorization',
    color: 'text-orange-400',
    bgColor: 'bg-orange-900/30',
    icon: '🔐',
  },
  'F-INV': {
    label: 'Finality',
    description: 'BER/settlement eligibility',
    color: 'text-green-400',
    bgColor: 'bg-green-900/30',
    icon: '✅',
  },
  'C-INV': {
    label: 'Training',
    description: 'Signal emission compliance',
    color: 'text-pink-400',
    bgColor: 'bg-pink-900/30',
    icon: '📡',
  },
};

/**
 * Lint v2 Enforcement point configuration for UI
 */
export const LINT_V2_ENFORCEMENT_POINT_CONFIG: Record<LintV2EnforcementPoint, {
  label: string;
  icon: string;
  order: number;
}> = {
  'PAC_ADMISSION': {
    label: 'PAC Admission',
    icon: '📥',
    order: 1,
  },
  'WRAP_INGESTION': {
    label: 'WRAP Ingestion',
    icon: '📦',
    order: 2,
  },
  'RG01_EVALUATION': {
    label: 'RG-01 Evaluation',
    icon: '🔍',
    order: 3,
  },
  'BER_ELIGIBILITY': {
    label: 'BER Eligibility',
    icon: '📄',
    order: 4,
  },
  'SETTLEMENT_READINESS': {
    label: 'Settlement Readiness',
    icon: '💰',
    order: 5,
  },
};
