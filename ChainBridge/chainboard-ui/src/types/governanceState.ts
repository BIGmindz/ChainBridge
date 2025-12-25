/**
 * Governance State Types — PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 *
 * Defines the UI state model for governance visibility.
 * All types mirror backend governance state exactly — NO frontend reinterpretation.
 *
 * State Model:
 * - OPEN: Normal operation, actions enabled
 * - BLOCKED: Governance gate blocked action, UI must disable
 * - CORRECTION_REQUIRED: PAC requires correction before proceeding
 * - RESUBMITTED: PAC resubmitted, awaiting re-evaluation
 * - RATIFIED: Authority ratified, unblock pending
 * - UNBLOCKED: System unblocked, normal operation resumed
 * - REJECTED: PAC rejected, archive only
 *
 * CONSTRAINTS:
 * - UI CANNOT bypass governance state
 * - All state transitions come from backend
 * - No optimistic UI state mutation
 * - State is always visible to operator
 *
 * @see PAC-SONNY-G1-PHASE-2-OPERATOR-VISIBILITY-AND-GOVERNANCE-UX-LOCK-01
 */

/**
 * Governance UI State — mirrors backend exactly.
 */
export type GovernanceUIState =
  | 'OPEN'
  | 'BLOCKED'
  | 'CORRECTION_REQUIRED'
  | 'RESUBMITTED'
  | 'RATIFIED'
  | 'UNBLOCKED'
  | 'REJECTED';

/**
 * Governance escalation level.
 */
export type EscalationLevel =
  | 'NONE'
  | 'L1_AGENT'
  | 'L2_GUARDIAN'
  | 'L3_HUMAN';

/**
 * Governance block reason — verbatim from backend.
 */
export interface GovernanceBlockReason {
  /** Rule code that triggered the block */
  rule_code: string;
  /** Human-readable reason — rendered verbatim */
  reason: string;
  /** Agent GID that triggered the block */
  triggered_by_gid: string;
  /** Timestamp of the block */
  blocked_at: string;
  /** Correlation ID for audit trail */
  correlation_id: string;
}

/**
 * Governance escalation event — verbatim from backend.
 */
export interface GovernanceEscalation {
  /** Escalation ID */
  escalation_id: string;
  /** Timestamp */
  escalated_at: string;
  /** Escalation level */
  level: EscalationLevel;
  /** Source agent GID */
  from_gid: string;
  /** Target agent/authority GID */
  to_gid: string;
  /** Reason for escalation */
  reason: string;
  /** Current status */
  status: 'PENDING' | 'ACKNOWLEDGED' | 'RESOLVED' | 'REJECTED';
  /** Resolution timestamp if resolved */
  resolved_at?: string;
  /** Resolution notes if resolved */
  resolution_notes?: string;
}

/**
 * PAC status for governance visibility.
 */
export interface PACStatus {
  /** PAC identifier */
  pac_id: string;
  /** Current state */
  state: GovernanceUIState;
  /** Owning agent GID */
  owner_gid: string;
  /** Created timestamp */
  created_at: string;
  /** Last updated timestamp */
  updated_at: string;
  /** Block reason if blocked */
  block_reason?: GovernanceBlockReason;
  /** Ratification authority if required */
  ratification_authority?: string;
  /** Ratification status */
  ratification_status?: 'PENDING' | 'APPROVED' | 'DENIED';
  /** Ratification timestamp */
  ratified_at?: string;
}

/**
 * WRAP status for governance visibility.
 */
export interface WRAPStatus {
  /** WRAP identifier */
  wrap_id: string;
  /** Associated PAC ID */
  pac_id: string;
  /** Submission timestamp */
  submitted_at: string;
  /** Validation status */
  validation_status: 'VALID' | 'INVALID' | 'PENDING';
  /** Validation errors if any */
  validation_errors?: string[];
  /** Artifacts count */
  artifacts_count: number;
}

/**
 * Full governance context for UI display.
 */
export interface GovernanceContext {
  /** Current governance state */
  state: GovernanceUIState;
  /** Current escalation level */
  escalation_level: EscalationLevel;
  /** Active blocks */
  active_blocks: GovernanceBlockReason[];
  /** Pending escalations */
  pending_escalations: GovernanceEscalation[];
  /** Active PACs */
  active_pacs: PACStatus[];
  /** Recent WRAPs */
  recent_wraps: WRAPStatus[];
  /** System health */
  system_healthy: boolean;
  /** Last sync timestamp */
  last_sync: string;
}

/**
 * UI enforcement rules based on governance state.
 */
export const GOVERNANCE_UI_RULES: Record<GovernanceUIState, {
  actions_enabled: boolean;
  banner_required: boolean;
  banner_severity: 'info' | 'warning' | 'error' | 'critical';
  allowed_action: string | null;
}> = {
  OPEN: {
    actions_enabled: true,
    banner_required: false,
    banner_severity: 'info',
    allowed_action: null,
  },
  BLOCKED: {
    actions_enabled: false,
    banner_required: true,
    banner_severity: 'critical',
    allowed_action: null,
  },
  CORRECTION_REQUIRED: {
    actions_enabled: false,
    banner_required: true,
    banner_severity: 'error',
    allowed_action: 'RESUBMIT_PAC',
  },
  RESUBMITTED: {
    actions_enabled: false,
    banner_required: true,
    banner_severity: 'warning',
    allowed_action: null,
  },
  RATIFIED: {
    actions_enabled: false,
    banner_required: true,
    banner_severity: 'info',
    allowed_action: 'UNBLOCK_SYSTEM',
  },
  UNBLOCKED: {
    actions_enabled: true,
    banner_required: false,
    banner_severity: 'info',
    allowed_action: null,
  },
  REJECTED: {
    actions_enabled: false,
    banner_required: true,
    banner_severity: 'error',
    allowed_action: 'ARCHIVE',
  },
};

/**
 * Check if actions are enabled for a given governance state.
 */
export function areActionsEnabled(state: GovernanceUIState): boolean {
  return GOVERNANCE_UI_RULES[state].actions_enabled;
}

/**
 * Check if banner is required for a given governance state.
 */
export function isBannerRequired(state: GovernanceUIState): boolean {
  return GOVERNANCE_UI_RULES[state].banner_required;
}

/**
 * Get the allowed action for a given governance state.
 */
export function getAllowedAction(state: GovernanceUIState): string | null {
  return GOVERNANCE_UI_RULES[state].allowed_action;
}
