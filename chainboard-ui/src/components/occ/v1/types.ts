/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC v1.0 Types — Operator Control Center Backend Integration
 * PAC-JEFFREY-P03: OCC UI Execution
 * 
 * Type definitions for OCC v1.0 backend services:
 *   - OCC Queue (occ_queue.py)
 *   - PDO State Machine (pdo_state_machine.py)
 *   - OCC Audit Log (occ_audit_log.py)
 *   - PDO Replay Engine (pdo_replay_engine.py)
 * 
 * INVARIANTS:
 * - INV-OCC-UI-001: All state is read-only from backend
 * - INV-OCC-UI-002: No mutation operations in UI
 * - INV-OCC-UI-003: Display-only, observer pattern
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// QUEUE TYPES (occ_queue.py)
// ═══════════════════════════════════════════════════════════════════════════════

export type QueuePriority = 
  | 'EMERGENCY'   // 0 - T5/T6 emergency actions
  | 'CRITICAL'    // 1 - T4+ override actions
  | 'HIGH'        // 2 - Time-sensitive operations
  | 'NORMAL'      // 3 - Standard operator actions
  | 'LOW'         // 4 - Background/batch operations
  | 'DEFERRED';   // 5 - Can wait indefinitely

export type OperatorTier = 'T1' | 'T2' | 'T3' | 'T4' | 'T5' | 'T6';

export interface QueueOperatorIdentity {
  /** Operator ID (e.g., "OP-00001") */
  operatorId: string;
  /** Operator tier */
  tier: OperatorTier;
  /** Session ID */
  sessionId: string;
  /** Verification status */
  verified: boolean;
}

export interface QueueItem {
  /** Queue item ID */
  id: string;
  /** Action type */
  actionType: string;
  /** Action payload (read-only display) */
  payload: Record<string, unknown>;
  /** Operator who queued the action */
  operator: QueueOperatorIdentity;
  /** Queue priority */
  priority: QueuePriority;
  /** When item was created */
  createdAt: string;
  /** Sequence number for FIFO ordering */
  sequenceNumber: number;
  /** Hash of previous item in chain */
  hashPrevious: string | null;
  /** Hash of this item */
  hashCurrent: string;
}

export interface QueueMetrics {
  /** Current queue size */
  currentSize: number;
  /** Maximum queue capacity */
  maxSize: number;
  /** Total items enqueued */
  enqueueCount: number;
  /** Total items dequeued */
  dequeueCount: number;
  /** Total items rejected */
  rejectCount: number;
  /** Current sequence counter */
  sequenceCounter: number;
}

export interface QueueState {
  /** Queue items (ordered by priority + sequence) */
  items: QueueItem[];
  /** Queue metrics */
  metrics: QueueMetrics;
  /** Whether queue is closed (fail-closed) */
  isClosed: boolean;
  /** Last refresh timestamp */
  lastRefresh: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PDO STATE MACHINE TYPES (pdo_state_machine.py)
// ═══════════════════════════════════════════════════════════════════════════════

export type PDOState =
  // Initial states
  | 'PENDING'
  | 'SUBMITTED'
  // Agent decision states
  | 'AGENT_APPROVED'
  | 'AGENT_BLOCKED'
  | 'AGENT_FLAGGED'
  // Policy decision states
  | 'POLICY_APPROVED'
  | 'POLICY_BLOCKED'
  // Operator decision states (override)
  | 'OPERATOR_APPROVED'
  | 'OPERATOR_BLOCKED'
  | 'OPERATOR_MODIFIED'
  // Processing states
  | 'IN_REVIEW'
  | 'ESCALATED'
  // Terminal states
  | 'SETTLED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'EXPIRED';

export type TransitionType = 'AGENT' | 'POLICY' | 'OPERATOR' | 'SYSTEM';

export interface PDOTransition {
  /** Transition ID */
  id: string;
  /** PDO ID */
  pdoId: string;
  /** From state */
  fromState: PDOState;
  /** To state */
  toState: PDOState;
  /** Transition type */
  transitionType: TransitionType;
  /** Actor ID (operator, agent GID, or "SYSTEM") */
  actorId: string;
  /** Transition timestamp */
  timestamp: string;
  /** Reason for transition */
  reason: string;
  /** Is this an override transition */
  isOverride: boolean;
  /** Override record ID (if override) */
  overrideId: string | null;
  /** Hash of previous transition */
  hashPrevious: string | null;
  /** Hash of this transition */
  hashCurrent: string;
}

export interface PDORecord {
  /** PDO ID */
  id: string;
  /** PDO value */
  value: number;
  /** Currency */
  currency: string;
  /** Current state */
  currentState: PDOState;
  /** When created */
  createdAt: string;
  /** When last updated */
  updatedAt: string;
  /** Has been overridden */
  isOverridden: boolean;
  /** Override ID (if overridden) */
  overrideId: string | null;
  /** Override timestamp (if overridden) */
  overrideTimestamp: string | null;
  /** Original decision before override */
  originalDecision: PDOState | null;
  /** Original operator (for self-override check) */
  originalOperatorId: string | null;
  /** Additional metadata */
  metadata: Record<string, unknown>;
}

export interface StateMachineMetrics {
  /** Total PDOs */
  pdoCount: number;
  /** Total transitions */
  transitionCount: number;
  /** Total overrides */
  overrideCount: number;
  /** Rejected transitions */
  rejectionCount: number;
}

export interface PDOStateMachineState {
  /** PDOs */
  pdos: PDORecord[];
  /** Selected PDO transitions (when viewing detail) */
  selectedPdoTransitions: PDOTransition[];
  /** Metrics */
  metrics: StateMachineMetrics;
  /** Last refresh timestamp */
  lastRefresh: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT LOG TYPES (occ_audit_log.py)
// ═══════════════════════════════════════════════════════════════════════════════

export type AuditRecordType =
  // Queue operations
  | 'QUEUE_ENQUEUE'
  | 'QUEUE_DEQUEUE'
  | 'QUEUE_ESCALATE'
  // Action operations
  | 'ACTION_SUBMITTED'
  | 'ACTION_VALIDATED'
  | 'ACTION_EXECUTED'
  | 'ACTION_BLOCKED'
  // Override operations
  | 'OVERRIDE_REQUESTED'
  | 'OVERRIDE_VALIDATED'
  | 'OVERRIDE_EXECUTED'
  | 'OVERRIDE_BLOCKED'
  // State machine operations
  | 'PDO_TRANSITION'
  | 'PDO_OVERRIDE_APPLIED'
  // System events
  | 'SYSTEM_STARTUP'
  | 'SYSTEM_SHUTDOWN'
  | 'SYSTEM_FAIL_CLOSED'
  // Authentication events
  | 'OPERATOR_LOGIN'
  | 'OPERATOR_LOGOUT'
  | 'MFA_VERIFIED'
  // Error events
  | 'INVARIANT_VIOLATION'
  | 'UNAUTHORIZED_ACCESS';

export type AuditResult = 'SUCCESS' | 'BLOCKED' | 'ERROR';

export interface AuditRecord {
  /** Audit record ID */
  id: string;
  /** Record type */
  recordType: AuditRecordType;
  /** Timestamp */
  timestamp: string;
  /** Operator ID (null for system events) */
  operatorId: string | null;
  /** Operator tier */
  operatorTier: OperatorTier | null;
  /** Session ID */
  sessionId: string | null;
  /** IP address */
  ipAddress: string | null;
  /** User agent */
  userAgent: string | null;
  /** Target entity ID */
  targetId: string | null;
  /** Action type */
  actionType: string | null;
  /** Additional payload */
  payload: Record<string, unknown>;
  /** Result */
  result: AuditResult;
  /** Human-readable message */
  message: string;
  /** Hash of previous record */
  hashPrevious: string | null;
  /** Hash of this record */
  hashCurrent: string;
}

export interface AuditLogStatistics {
  /** Total records */
  totalRecords: number;
  /** Current sequence counter */
  sequenceCounter: number;
  /** Records by type */
  recordsByType: Record<string, number>;
  /** Records by result */
  recordsByResult: Record<string, number>;
  /** Hash chain valid */
  chainValid: boolean;
}

export interface AuditLogState {
  /** Audit records (most recent first) */
  records: AuditRecord[];
  /** Statistics */
  statistics: AuditLogStatistics;
  /** Filters applied */
  filters: AuditFilters;
  /** Last refresh timestamp */
  lastRefresh: string;
}

/** PAC-BENSON-EXEC-P11: Audit filter options for API queries */
export interface AuditFilters {
  recordType?: AuditRecordType;
  operatorId?: string;
  targetId?: string;
  dateFrom?: string;
  dateTo?: string;
  startTime?: string;
  endTime?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// REPLAY ENGINE TYPES (pdo_replay_engine.py)
// ═══════════════════════════════════════════════════════════════════════════════

export type ReplayMode = 'FULL' | 'POINT_IN_TIME' | 'VALIDATE' | 'FORENSIC';

export interface ReplayState {
  /** PDO ID */
  pdoId: string;
  /** State at this point */
  state: PDOState;
  /** Timestamp */
  timestamp: string;
  /** Transition index */
  transitionIndex: number;
  /** Was overridden at this point */
  isOverridden: boolean;
  /** Override count at this point */
  overrideCount: number;
  /** Hash at this state */
  hashAtState: string;
}

export interface ReplayResult {
  /** PDO ID */
  pdoId: string;
  /** Replay mode */
  mode: ReplayMode;
  /** Success status */
  success: boolean;
  /** Final state */
  finalState: PDOState;
  /** Transition count */
  transitionCount: number;
  /** Override count */
  overrideCount: number;
  /** Hash chain valid */
  hashChainValid: boolean;
  /** State consistent */
  stateConsistent: boolean;
  /** Errors */
  errors: string[];
  /** Intermediate states (forensic mode) */
  intermediateStates: ReplayState[];
  /** Target timestamp (point-in-time mode) */
  targetTimestamp: string | null;
  /** State at timestamp (point-in-time mode) */
  stateAtTimestamp: PDOState | null;
  /** Replay started */
  replayStartedAt: string;
  /** Replay completed */
  replayCompletedAt: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AGGREGATE OCC V1 STATE
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCCv1DashboardState {
  /** Queue state */
  queue: QueueState;
  /** PDO state machine state */
  stateMachine: PDOStateMachineState;
  /** Audit log state */
  auditLog: AuditLogState;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: string | null;
  /** Last refresh */
  lastRefresh: string;
}
