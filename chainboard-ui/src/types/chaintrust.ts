// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust Types — External Trust Center
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
//
// READ-ONLY governance visualization types for external auditors and investors.
// All types must map directly to lint_v2 / governance API outputs.
//
// INVARIANTS:
// - INV-UNIFORM-001: No agent executes without uniform
// - INV-UNIFORM-002: Unknown agents forbidden
// - INV-UNIFORM-003: PAC required for all execution
// - INV-UNIFORM-004: BER required for finality
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Runtime activation status from lint_v2 engine.
 */
export interface RuntimeActivationStatus {
  schema_validation_enabled: boolean;
  invariant_registry_loaded: boolean;
  lint_v2_compiler_active: boolean;
  runtime_ack_enforced: boolean;
  agent_ack_enforced: boolean;
  deterministic_execution_order: boolean;
  fail_closed_enabled: boolean;
  is_ready: boolean;
  activated_at: string | null;
}

/**
 * Governance status summary for ChainTrust overview.
 */
export interface GovernanceStatusDTO {
  status: 'PASS' | 'FAIL';
  runtime_activation: RuntimeActivationStatus;
  invariant_count: number;
  uniform_invariant_count: number;
  fail_mode: 'HARD_FAIL' | 'SOFT_FAIL';
  last_validated_at: string;
  validation_hash: string;
}

/**
 * Agent uniform status per agent.
 */
export interface AgentUniformStatus {
  gid: string;
  name: string;
  role: string;
  scope: string;
  uniform_compliant: boolean;
  pac_present: boolean;
  ack_present: boolean;
  wrap_present: boolean;
  ber_eligible: boolean;
  last_execution_at: string | null;
}

/**
 * Agent uniform panel data.
 */
export interface AgentUniformPanelDTO {
  agents: AgentUniformStatus[];
  total_agents: number;
  compliant_agents: number;
  non_compliant_agents: number;
  uniform_invariants: string[];
}

/**
 * PDO checkpoint marker.
 */
export interface PDOCheckpoint {
  checkpoint_id: string;
  checkpoint_name: string;
  invariant_classes: string[];
  status: 'PASS' | 'FAIL' | 'PENDING' | 'SKIPPED';
  evaluated_at: string | null;
  violations: string[];
}

/**
 * PDO lifecycle state.
 */
export type PDOLifecycleState =
  | 'PROOF'
  | 'DECISION'
  | 'OUTCOME'
  | 'FINALIZED'
  | 'REJECTED';

/**
 * BER classification.
 */
export type BERClassification = 'PROVISIONAL' | 'BINDING';

/**
 * PDO lifecycle entry.
 */
export interface PDOLifecycleEntry {
  pdo_id: string;
  pac_id: string;
  state: PDOLifecycleState;
  checkpoints: PDOCheckpoint[];
  ber_classification: BERClassification;
  ber_id: string | null;
  execution_binding: boolean;
  ledger_commit_allowed: boolean;
  settlement_effect: 'NONE' | 'BINDING';
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
}

/**
 * PDO lifecycle viewer data.
 */
export interface PDOLifecycleViewerDTO {
  pdos: PDOLifecycleEntry[];
  total_pdos: number;
  finalized_count: number;
  pending_count: number;
  rejected_count: number;
}

/**
 * Invariant class category.
 */
export type InvariantClassCategory =
  | 'S-INV'  // Structural
  | 'M-INV'  // Semantic
  | 'X-INV'  // Cross-Artifact
  | 'T-INV'  // Temporal
  | 'A-INV'  // Authority
  | 'F-INV'  // Finality
  | 'C-INV'  // Training
  | 'UNIFORM'; // Agent Uniform

/**
 * Invariant definition for display.
 */
export interface InvariantDisplay {
  invariant_id: string;
  name: string;
  description: string;
  invariant_class: InvariantClassCategory;
  enforcement_mode: 'HARD_FAIL' | 'WARN' | 'LOG';
  last_validated_at: string | null;
  validation_count: number;
  violation_count: number;
}

/**
 * Invariant coverage by category.
 */
export interface InvariantCategoryStats {
  category: InvariantClassCategory;
  category_label: string;
  invariant_count: number;
  pass_count: number;
  fail_count: number;
  coverage_percent: number;
}

/**
 * Invariant coverage panel data.
 */
export interface InvariantCoveragePanelDTO {
  categories: InvariantCategoryStats[];
  invariants: InvariantDisplay[];
  total_invariants: number;
  enforcement_mode: 'HARD_FAIL';
  last_full_validation_at: string;
}

/**
 * ChainTrust external audit view data.
 * Shareable, deterministic, read-only.
 */
export interface ChainTrustAuditViewDTO {
  trust_id: string;
  generated_at: string;
  expires_at: string;
  governance_status: GovernanceStatusDTO;
  agent_uniform: AgentUniformPanelDTO;
  pdo_lifecycle: PDOLifecycleViewerDTO;
  invariant_coverage: InvariantCoveragePanelDTO;
  deterministic_hash: string;
  shareable_url: string | null;
}

/**
 * ChainTrust overview for the main dashboard.
 */
export interface ChainTrustOverviewDTO {
  governance_status: GovernanceStatusDTO;
  agent_uniform_summary: {
    total: number;
    compliant: number;
    non_compliant: number;
  };
  pdo_summary: {
    total: number;
    finalized: number;
    pending: number;
  };
  invariant_summary: {
    total: number;
    by_category: Record<InvariantClassCategory, number>;
  };
  last_updated_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// UI CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Status color mapping.
 */
export const STATUS_COLORS = {
  PASS: 'bg-green-500',
  FAIL: 'bg-red-500',
  PENDING: 'bg-yellow-500',
  SKIPPED: 'bg-gray-400',
} as const;

/**
 * Invariant class colors.
 */
export const INVARIANT_CLASS_COLORS: Record<InvariantClassCategory, string> = {
  'S-INV': 'bg-blue-500',
  'M-INV': 'bg-purple-500',
  'X-INV': 'bg-indigo-500',
  'T-INV': 'bg-cyan-500',
  'A-INV': 'bg-orange-500',
  'F-INV': 'bg-green-500',
  'C-INV': 'bg-pink-500',
  'UNIFORM': 'bg-red-500',
} as const;

/**
 * Invariant class labels.
 */
export const INVARIANT_CLASS_LABELS: Record<InvariantClassCategory, string> = {
  'S-INV': 'Structural',
  'M-INV': 'Semantic',
  'X-INV': 'Cross-Artifact',
  'T-INV': 'Temporal',
  'A-INV': 'Authority',
  'F-INV': 'Finality',
  'C-INV': 'Training',
  'UNIFORM': 'Agent Uniform',
} as const;

/**
 * PDO state colors.
 */
export const PDO_STATE_COLORS: Record<PDOLifecycleState, string> = {
  PROOF: 'bg-blue-500',
  DECISION: 'bg-yellow-500',
  OUTCOME: 'bg-purple-500',
  FINALIZED: 'bg-green-500',
  REJECTED: 'bg-red-500',
} as const;

/**
 * BER classification colors.
 */
export const BER_CLASSIFICATION_COLORS: Record<BERClassification, string> = {
  PROVISIONAL: 'bg-yellow-500',
  BINDING: 'bg-green-500',
} as const;
