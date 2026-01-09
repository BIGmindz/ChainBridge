/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC Timeline Types — PAC → WRAP → BER Lifecycle Visualization
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Type definitions for timeline visualization components:
 * - PAC lifecycle events
 * - WRAP aggregation milestones
 * - BER finalization markers
 * - Agent execution traces
 * 
 * INVARIANTS:
 * - INV-OCC-004: Timeline completeness (all transitions visible)
 * - INV-OCC-005: Evidence immutability (no retroactive edits)
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * Security: SAM (GID-06)
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE EVENT TYPES
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Categories of timeline events in PAC lifecycle
 */
export type TimelineEventCategory =
  | 'pac_lifecycle'      // PAC admission, activation, completion
  | 'agent_activation'   // Agent ACK events
  | 'execution'          // Task execution events
  | 'decision'           // PDO/approval events
  | 'wrap'               // WRAP collection events
  | 'review_gate'        // RG-01, BSRG-01 gates
  | 'ber'                // BER issuance
  | 'governance'         // Invariant checks, lint
  | 'error';             // Failures, blocks

/**
 * Severity levels for timeline events
 */
export type TimelineEventSeverity = 'info' | 'success' | 'warning' | 'error' | 'critical';

/**
 * PAC lifecycle states
 */
export type PACLifecycleState =
  | 'ADMISSION'
  | 'RUNTIME_ACTIVATION'
  | 'AGENT_ACTIVATION'
  | 'EXECUTING'
  | 'WRAP_COLLECTION'
  | 'REVIEW_GATE'
  | 'BER_ISSUED'
  | 'SETTLED'
  | 'FAILED'
  | 'CANCELLED';

/**
 * Single timeline event
 */
export interface TimelineEvent {
  /** Unique event ID */
  eventId: string;
  /** Parent PAC ID */
  pacId: string;
  /** Event category */
  category: TimelineEventCategory;
  /** Event severity */
  severity: TimelineEventSeverity;
  /** Event title (short) */
  title: string;
  /** Event description (detailed) */
  description: string;
  /** Timestamp */
  timestamp: string;
  /** Agent that triggered this event (if applicable) */
  agentId?: string;
  /** Agent name */
  agentName?: string;
  /** Associated artifact IDs */
  artifactIds?: string[];
  /** Evidence hash for immutability */
  evidenceHash?: string;
  /** Duration in milliseconds (for spans) */
  durationMs?: number;
  /** Metadata */
  metadata?: Record<string, unknown>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PAC TIMELINE STATE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Agent ACK record for timeline
 */
export interface AgentACKRecord {
  agentId: string;
  agentName: string;
  ackTimestamp: string;
  ackLatencyMs: number;
  lane: string;
}

/**
 * WRAP milestone in timeline
 */
export interface WRAPMilestone {
  wrapId: string;
  pacId: string;
  status: 'collecting' | 'complete' | 'failed';
  agentsRequired: number;
  agentsApproved: number;
  approvedAgents: AgentACKRecord[];
  pendingAgents: string[];
  startedAt: string;
  completedAt?: string;
}

/**
 * Review gate record
 */
export interface ReviewGateRecord {
  gateId: string;
  gateType: 'RG-01' | 'BSRG-01';
  status: 'pending' | 'passed' | 'failed';
  checkedAt: string;
  checks: {
    completeness: boolean;
    evidence: boolean;
    driftCheck: boolean;
    neutrality: boolean;
  };
  failureReason?: string;
}

/**
 * BER record for timeline
 */
export interface BERTimelineRecord {
  berId: string;
  pacId: string;
  status: 'DRAFT' | 'PENDING_REVIEW' | 'FINAL' | 'SUPERSEDED';
  issuedAt: string;
  issuedBy: string;
  executionMode: string;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  finality: 'FINAL' | 'PROVISIONAL';
  evidenceHash: string;
}

/**
 * Complete PAC timeline state
 */
export interface PACTimelineState {
  /** PAC identifier */
  pacId: string;
  /** Current lifecycle state */
  lifecycleState: PACLifecycleState;
  /** PAC title/description */
  title: string;
  /** PAC issuer */
  issuer: string;
  /** Timeline events (chronological) */
  events: TimelineEvent[];
  /** Agent ACKs */
  agentAcks: AgentACKRecord[];
  /** WRAP milestones */
  wrapMilestones: WRAPMilestone[];
  /** Review gates */
  reviewGates: ReviewGateRecord[];
  /** BER records */
  berRecords: BERTimelineRecord[];
  /** Timeline start */
  startedAt: string;
  /** Timeline end (if complete) */
  completedAt?: string;
  /** Total duration in milliseconds */
  durationMs?: number;
  /** Error state */
  error?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE VIEW STATE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Timeline view filter options
 */
export interface TimelineFilterOptions {
  /** Filter by event categories */
  categories?: TimelineEventCategory[];
  /** Filter by severity */
  severities?: TimelineEventSeverity[];
  /** Filter by agent */
  agentIds?: string[];
  /** Time range start */
  startTime?: string;
  /** Time range end */
  endTime?: string;
  /** Search text */
  searchText?: string;
}

/**
 * Timeline view display options
 */
export interface TimelineDisplayOptions {
  /** Show compact or expanded events */
  density: 'compact' | 'normal' | 'expanded';
  /** Group events by category */
  groupByCategory: boolean;
  /** Show evidence hashes */
  showEvidenceHashes: boolean;
  /** Show artifact links */
  showArtifactLinks: boolean;
  /** Auto-scroll to latest */
  autoScroll: boolean;
}

/**
 * Timeline component props
 */
export interface TimelineViewProps {
  /** PAC ID to display timeline for */
  pacId: string;
  /** Timeline state (from API) */
  state?: PACTimelineState;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string | null;
  /** Filter options */
  filters?: TimelineFilterOptions;
  /** Display options */
  displayOptions?: TimelineDisplayOptions;
  /** Callback when event is selected */
  onEventSelect?: (event: TimelineEvent) => void;
  /** Callback when filters change */
  onFilterChange?: (filters: TimelineFilterOptions) => void;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE SEGMENT TYPES (for visualization)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Timeline segment (phase of PAC lifecycle)
 */
export interface TimelineSegment {
  segmentId: string;
  label: string;
  startTime: string;
  endTime?: string;
  status: 'active' | 'complete' | 'failed' | 'pending';
  events: TimelineEvent[];
  progress: number; // 0-100
}

/**
 * Timeline visualization data
 */
export interface TimelineVisualizationData {
  pacId: string;
  segments: TimelineSegment[];
  totalEvents: number;
  currentPhase: string;
  overallProgress: number;
}
