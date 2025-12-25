/**
 * Governance Ledger Types — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Defines types for the Governance Ledger and PAC Registry.
 * All types are read-only and mirror backend state exactly.
 *
 * GUARANTEES:
 * - append_only: Ledger entries are never modified or deleted
 * - monotonic_sequence: Sequence numbers always increase
 * - closure_type_explicit: Every entry has explicit closure type
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

/**
 * PAC lifecycle state — canonical values from backend.
 */
export type PACLifecycleState =
  | 'READY_FOR_EXECUTION'
  | 'IN_PROGRESS'
  | 'BLOCKED'
  | 'CORRECTION_REQUIRED'
  | 'RESUBMITTED'
  | 'RATIFIED'
  | 'POSITIVE_CLOSURE'
  | 'REJECTED'
  | 'ARCHIVED';

/**
 * Closure type — explicit classification of PAC outcome.
 */
export type ClosureType =
  | 'NONE'
  | 'POSITIVE_CLOSURE'
  | 'NEGATIVE_CLOSURE'
  | 'CORRECTION_CLOSURE'
  | 'ARCHIVED';

/**
 * Ledger entry type — classification of ledger event.
 */
export type LedgerEntryType =
  | 'PAC_CREATED'
  | 'PAC_STARTED'
  | 'PAC_BLOCKED'
  | 'CORRECTION_ISSUED'
  | 'CORRECTION_APPLIED'
  | 'WRAP_SUBMITTED'
  | 'WRAP_VALIDATED'
  | 'WRAP_REJECTED'
  | 'RATIFICATION_REQUESTED'
  | 'RATIFICATION_APPROVED'
  | 'RATIFICATION_DENIED'
  | 'POSITIVE_CLOSURE'
  | 'NEGATIVE_CLOSURE'
  | 'ESCALATION_RAISED'
  | 'ESCALATION_RESOLVED';

/**
 * Violation record — governance violation details.
 */
export interface ViolationRecord {
  /** Violation code (e.g., G0_020) */
  violation_id: string;
  /** Human-readable description */
  description: string;
  /** Resolution status */
  resolved: boolean;
  /** Resolution notes if resolved */
  resolution?: string;
  /** Resolution timestamp */
  resolved_at?: string;
}

/**
 * Correction record — correction PAC details.
 */
export interface CorrectionRecord {
  /** Correction PAC ID */
  correction_pac_id: string;
  /** Correction version (e.g., 1, 2, 3) */
  correction_version: number;
  /** Violations addressed in this correction */
  violations_addressed: ViolationRecord[];
  /** Correction status */
  status: 'ISSUED' | 'APPLIED' | 'SUPERSEDED';
  /** Applied timestamp */
  applied_at?: string;
}

/**
 * Ledger entry — single immutable record in the governance ledger.
 */
export interface LedgerEntry {
  /** Unique entry ID */
  entry_id: string;
  /** Monotonic sequence number */
  sequence: number;
  /** Entry type */
  type: LedgerEntryType;
  /** Timestamp */
  timestamp: string;
  /** Associated PAC ID */
  pac_id: string;
  /** Associated WRAP ID if applicable */
  wrap_id?: string;
  /** Agent GID that triggered this entry */
  agent_gid: string;
  /** Agent name */
  agent_name: string;
  /** Agent color */
  agent_color: string;
  /** Human-readable description */
  description: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Correlation ID for audit trail */
  correlation_id: string;
}

/**
 * PAC registry entry — full PAC record with lineage.
 */
export interface PACRegistryEntry {
  /** PAC ID */
  pac_id: string;
  /** PAC title/objective */
  title: string;
  /** Current lifecycle state */
  state: PACLifecycleState;
  /** Closure type */
  closure_type: ClosureType;
  /** Owning agent GID */
  owner_gid: string;
  /** Owning agent name */
  owner_name: string;
  /** Owning agent color */
  owner_color: string;
  /** Created timestamp */
  created_at: string;
  /** Last updated timestamp */
  updated_at: string;
  /** Closed timestamp if closed */
  closed_at?: string;
  /** Closure authority GID if closed */
  closure_authority_gid?: string;
  /** Closure authority name */
  closure_authority_name?: string;
  /** Associated WRAP IDs */
  wrap_ids: string[];
  /** Correction records */
  corrections: CorrectionRecord[];
  /** Active violations */
  active_violations: ViolationRecord[];
  /** Ledger entries for this PAC */
  ledger_entries: LedgerEntry[];
}

/**
 * Governance ledger — full ledger state.
 */
export interface GovernanceLedger {
  /** All ledger entries (append-only) */
  entries: LedgerEntry[];
  /** Total entry count */
  total_entries: number;
  /** Latest sequence number */
  latest_sequence: number;
  /** Last sync timestamp */
  last_sync: string;
}

/**
 * PAC registry — all PACs with lineage.
 */
export interface PACRegistry {
  /** All PAC entries */
  pacs: PACRegistryEntry[];
  /** Total PAC count */
  total_pacs: number;
  /** Active PAC count */
  active_pacs: number;
  /** Blocked PAC count */
  blocked_pacs: number;
  /** Positive closure count */
  positive_closures: number;
  /** Last sync timestamp */
  last_sync: string;
}

/**
 * Governance summary — high-level stats for dashboard.
 */
export interface GovernanceSummary {
  /** Total PACs */
  total_pacs: number;
  /** Active PACs */
  active_pacs: number;
  /** Blocked PACs */
  blocked_pacs: number;
  /** Correction cycles in progress */
  correction_cycles: number;
  /** Positive closures */
  positive_closures: number;
  /** Pending ratifications */
  pending_ratifications: number;
  /** System health status */
  system_healthy: boolean;
  /** Last ledger entry timestamp */
  last_activity: string;
}

/**
 * Timeline node — for rendering PAC timeline.
 */
export interface TimelineNode {
  /** Node ID */
  id: string;
  /** Node type */
  type: LedgerEntryType;
  /** Display label */
  label: string;
  /** Timestamp */
  timestamp: string;
  /** Agent info */
  agent: {
    gid: string;
    name: string;
    color: string;
  };
  /** Is this a correction node */
  is_correction: boolean;
  /** Is this a closure node */
  is_closure: boolean;
  /** Closure type if closure node */
  closure_type?: ClosureType;
  /** Violations if applicable */
  violations?: ViolationRecord[];
  /** Status indicator */
  status: 'success' | 'warning' | 'error' | 'info' | 'blocked';
}

/**
 * Get status indicator for a PAC lifecycle state.
 */
export function getStateStatus(state: PACLifecycleState): 'success' | 'warning' | 'error' | 'info' | 'blocked' {
  switch (state) {
    case 'POSITIVE_CLOSURE':
    case 'RATIFIED':
      return 'success';
    case 'BLOCKED':
    case 'REJECTED':
      return 'blocked';
    case 'CORRECTION_REQUIRED':
    case 'RESUBMITTED':
      return 'warning';
    case 'IN_PROGRESS':
    case 'READY_FOR_EXECUTION':
      return 'info';
    default:
      return 'info';
  }
}

/**
 * Get human-readable label for closure type.
 */
export function getClosureLabel(closure: ClosureType): string {
  switch (closure) {
    case 'POSITIVE_CLOSURE':
      return 'Positive Closure';
    case 'NEGATIVE_CLOSURE':
      return 'Negative Closure';
    case 'CORRECTION_CLOSURE':
      return 'Correction Closure';
    case 'ARCHIVED':
      return 'Archived';
    case 'NONE':
    default:
      return 'Open';
  }
}

/**
 * Check if a PAC is in a blocked state.
 */
export function isPACBlocked(state: PACLifecycleState): boolean {
  return state === 'BLOCKED' || state === 'REJECTED';
}

/**
 * Check if a PAC has positive closure.
 */
export function hasPositiveClosure(closure: ClosureType): boolean {
  return closure === 'POSITIVE_CLOSURE';
}
