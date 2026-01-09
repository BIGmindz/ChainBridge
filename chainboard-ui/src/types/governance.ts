// ═══════════════════════════════════════════════════════════════════════════════
// ChainBridge Governance Types
// PAC-012: Governance Hardening — ORDER 3 (Sonny GID-05)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Acknowledgment status enum.
 */
export type AcknowledgmentStatus = 
  | 'PENDING'
  | 'ACKNOWLEDGED'
  | 'REJECTED'
  | 'TIMEOUT'
  | 'NOT_REQUIRED';

/**
 * Acknowledgment type enum.
 */
export type AcknowledgmentType =
  | 'ACK_REQUIRED'
  | 'ACK_OPTIONAL'
  | 'ACK_IMPLICIT';

/**
 * Dependency type enum.
 */
export type DependencyType = 'HARD' | 'SOFT';

/**
 * Dependency status enum.
 */
export type DependencyStatus = 'PENDING' | 'SATISFIED' | 'FAILED' | 'SKIPPED';

/**
 * Capability category enum.
 */
export type CapabilityCategory =
  | 'DATA_ACCESS'
  | 'DATA_MUTATION'
  | 'EXTERNAL_API'
  | 'FINANCIAL_ACTION'
  | 'USER_IMPERSONATION'
  | 'SYSTEM_CONTROL'
  | 'TRAINING_FEEDBACK';

/**
 * Failure mode enum.
 */
export type FailureMode =
  | 'FAIL_CLOSED'
  | 'FAIL_OPEN'
  | 'FAIL_RETRY'
  | 'FAIL_COMPENSATE';

/**
 * Rollback strategy enum.
 */
export type RollbackStrategy =
  | 'NONE'
  | 'COMPENSATING'
  | 'CHECKPOINT'
  | 'FULL_REVERT';

/**
 * Failure propagation mode enum.
 */
export type FailurePropagationMode =
  | 'IMMEDIATE'
  | 'CASCADING'
  | 'CONTAINED'
  | 'ISOLATED';

/**
 * Human intervention type enum.
 */
export type HumanInterventionType =
  | 'APPROVAL_REQUIRED'
  | 'REVIEW_REQUIRED'
  | 'NOTIFICATION_ONLY'
  | 'OVERRIDE'
  | 'ESCALATION';

/**
 * Human boundary status enum.
 */
export type HumanBoundaryStatus =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'TIMEOUT'
  | 'BYPASSED';

// ═══════════════════════════════════════════════════════════════════════════════
// DATA TRANSFER OBJECTS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Agent acknowledgment DTO.
 */
export interface AcknowledgmentDTO {
  ack_id: string;
  pac_id: string;
  order_id: string;
  agent_gid: string;
  agent_name: string;
  ack_type: AcknowledgmentType;
  status: AcknowledgmentStatus;
  requested_at: string;
  acknowledged_at?: string;
  timeout_at?: string;
  response_message?: string;
  rejection_reason?: string;
  ack_hash: string;
}

/**
 * Acknowledgment list DTO.
 */
export interface AcknowledgmentListDTO {
  pac_id: string;
  acknowledgments: AcknowledgmentDTO[];
  total: number;
  pending_count: number;
  acknowledged_count: number;
  rejected_count: number;
}

/**
 * Execution dependency DTO.
 */
export interface DependencyDTO {
  dependency_id: string;
  pac_id: string;
  dependent_order_id: string;
  dependent_agent_gid: string;
  source_order_id: string;
  source_agent_gid: string;
  dependency_type: DependencyType;
  description: string;
  status: DependencyStatus;
  declared_at: string;
  resolved_at?: string;
  on_failure_action: string;
  is_blocking: boolean;
}

/**
 * Dependency graph DTO.
 */
export interface DependencyGraphDTO {
  pac_id: string;
  dependencies: DependencyDTO[];
  execution_order: string[];
  total_dependencies: number;
  satisfied_count: number;
  pending_count: number;
  failed_count: number;
}

/**
 * Causality link DTO.
 */
export interface CausalityLinkDTO {
  link_id: string;
  pac_id: string;
  order_id: string;
  agent_gid: string;
  artifact_id: string;
  artifact_type: string;
  artifact_location: string;
  caused_by_order_ids: string[];
  created_at: string;
  link_hash: string;
}

/**
 * Non-capability DTO.
 */
export interface NonCapabilityDTO {
  capability_id: string;
  category: CapabilityCategory;
  description: string;
  reason: string;
  applies_to_agents: string[];
  applies_to_pacs: string[];
  enforced: boolean;
  violation_action: string;
}

/**
 * Non-capabilities list DTO.
 */
export interface NonCapabilitiesListDTO {
  non_capabilities: NonCapabilityDTO[];
  total: number;
  categories: string[];
}

/**
 * Failure semantics DTO.
 */
export interface FailureSemanticsDTO {
  failure_modes: FailureMode[];
  rollback_strategies: RollbackStrategy[];
  propagation_modes: FailurePropagationMode[];
  human_intervention_types: HumanInterventionType[];
  human_boundary_statuses: HumanBoundaryStatus[];
}

/**
 * Governance invariant definition.
 */
export interface GovernanceInvariant {
  name: string;
  description: string;
  enforcement: string;
}

/**
 * Governance invariants map.
 */
export interface GovernanceInvariantsDTO {
  invariants: Record<string, GovernanceInvariant>;
  total: number;
}

/**
 * Governance summary DTO.
 */
export interface GovernanceSummaryDTO {
  total_acknowledgments: number;
  total_dependencies: number;
  total_causality_links: number;
  total_non_capabilities: number;
  pending_acknowledgments: number;
  pending_dependencies: number;
  governance_invariants: string[];
}

/**
 * Causality trace result.
 */
export interface CausalityTraceDTO {
  artifact_id: string;
  causality_chain: string[];
  chain_length: number;
}
