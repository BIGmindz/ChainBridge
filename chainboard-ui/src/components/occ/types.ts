/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * OCC (Operator Control Center) Types
 * PAC-BENSON-P21-C: OCC Intensive Multi-Agent Execution
 * 
 * State-first, governed, operator-grade type definitions.
 * 
 * INVARIANTS:
 * - INV-OCC-001: All state is read-only from backend
 * - INV-OCC-002: No optimistic state rendering
 * - INV-OCC-003: All actions require explicit backend confirmation
 * 
 * Author: SONNY (GID-02) — Frontend
 * Accessibility: LIRA (GID-09)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type AgentHealthState = 
  | 'HEALTHY'
  | 'DEGRADED'
  | 'UNHEALTHY'
  | 'OFFLINE'
  | 'UNKNOWN';

export type AgentExecutionState =
  | 'IDLE'
  | 'EXECUTING'
  | 'BLOCKED'
  | 'COMPLETED'
  | 'FAILED'
  | 'AWAITING_ACK';

export interface AgentLaneTile {
  /** Agent GID (e.g., "GID-00") */
  gid: string;
  /** Agent name (e.g., "BENSON") */
  name: string;
  /** Agent lane (e.g., "orchestration", "backend") */
  lane: string;
  /** Current health state */
  healthState: AgentHealthState;
  /** Current execution state */
  executionState: AgentExecutionState;
  /** Active PAC ID if executing */
  activePacId: string | null;
  /** Last heartbeat timestamp (ISO 8601) */
  lastHeartbeat: string | null;
  /** Number of pending ACKs */
  pendingAcks: number;
  /** Number of completed tasks in session */
  completedTasks: number;
  /** Agent color for visual distinction */
  color: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DECISION STREAM TYPES (PDO + BER)
// ═══════════════════════════════════════════════════════════════════════════════

export type PDOOutcome = 'APPROVED' | 'REJECTED' | 'PENDING';
export type BERClassification = 'PROVISIONAL' | 'FINAL' | 'BINDING';
export type BERState = 'PENDING' | 'ISSUED' | 'SETTLED' | 'BLOCKED';

export interface PDOCard {
  /** PDO ID */
  pdoId: string;
  /** Associated PAC ID */
  pacId: string;
  /** Decision outcome */
  outcome: PDOOutcome;
  /** Amount (if applicable) */
  amount: number | null;
  /** Currency (if applicable) */
  currency: string | null;
  /** Creation timestamp */
  createdAt: string;
  /** Issuing agent GID */
  issuedBy: string;
  /** PDO hash for verification */
  pdoHash: string;
  /** Settlement ID (if linked) */
  settlementId: string | null;
  /** Reasons for decision */
  reasons: string[];
}

export interface BERCard {
  /** BER ID */
  berId: string;
  /** Associated PAC ID */
  pacId: string;
  /** BER classification */
  classification: BERClassification;
  /** Current state */
  state: BERState;
  /** Execution binding status */
  executionBinding: boolean;
  /** Ledger commit hash (if committed) */
  ledgerCommitHash: string | null;
  /** Settlement effect */
  settlementEffect: 'NONE' | 'BINDING';
  /** Issuance timestamp */
  issuedAt: string;
  /** Issuing agent GID */
  issuedBy: string;
  /** Training signals count */
  trainingSignalsCount: number;
  /** WRAPs collected count */
  wrapsCollected: number;
  /** WRAPs required count */
  wrapsRequired: number;
}

export interface DecisionStreamItem {
  /** Unique item ID */
  id: string;
  /** Item type */
  type: 'PDO' | 'BER';
  /** Timestamp for ordering */
  timestamp: string;
  /** PDO data (if type is PDO) */
  pdo?: PDOCard;
  /** BER data (if type is BER) */
  ber?: BERCard;
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOVERNANCE RAIL TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type InvariantStatus = 'PASSING' | 'FAILING' | 'NOT_EVALUATED';
export type InvariantClass = 
  | 'S-INV'  // Structural
  | 'M-INV'  // Semantic
  | 'X-INV'  // Cross-Artifact
  | 'T-INV'  // Temporal
  | 'A-INV'  // Authority
  | 'F-INV'  // Finality
  | 'C-INV'; // Training

export interface InvariantDisplay {
  /** Invariant ID (e.g., "INV-CP-001") */
  invariantId: string;
  /** Invariant class */
  invariantClass: InvariantClass;
  /** Human-readable name */
  name: string;
  /** Description */
  description: string;
  /** Current status */
  status: InvariantStatus;
  /** Enforcement points */
  enforcementPoints: string[];
  /** Last evaluated timestamp */
  lastEvaluated: string | null;
  /** Violation message (if failing) */
  violationMessage: string | null;
}

export interface GovernanceRailState {
  /** Active PAC ID */
  activePacId: string | null;
  /** Lint v2 status */
  lintV2Active: boolean;
  /** Schema registry locked */
  schemaRegistryLocked: boolean;
  /** Fail-closed mode enabled */
  failClosedEnabled: boolean;
  /** Active invariants */
  invariants: InvariantDisplay[];
  /** Invariants passing count */
  passingCount: number;
  /** Invariants failing count */
  failingCount: number;
  /** Total invariants */
  totalCount: number;
  /** Last sync timestamp */
  lastSync: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// KILL SWITCH TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type KillSwitchState = 
  | 'DISARMED'    // Normal operation
  | 'ARMED'       // Ready to engage
  | 'ENGAGED'     // All execution halted
  | 'COOLDOWN';   // Recently disengaged

export type KillSwitchAuthLevel =
  | 'UNAUTHORIZED'  // Cannot arm/engage
  | 'ARM_ONLY'      // Can arm but not engage
  | 'FULL_ACCESS';  // Can arm and engage

export interface KillSwitchStatus {
  /** Current state */
  state: KillSwitchState;
  /** Current user's authorization level */
  authLevel: KillSwitchAuthLevel;
  /** Who engaged (if engaged) */
  engagedBy: string | null;
  /** When engaged (if engaged) */
  engagedAt: string | null;
  /** Reason for engagement */
  engagementReason: string | null;
  /** Affected PAC IDs */
  affectedPacs: string[];
  /** Cooldown remaining (ms) */
  cooldownRemaining: number | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// OCC DASHBOARD STATE
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCCDashboardState {
  /** Agent lane grid data */
  agents: AgentLaneTile[];
  /** Decision stream items */
  decisionStream: DecisionStreamItem[];
  /** Governance rail state */
  governanceRail: GovernanceRailState;
  /** Kill switch status */
  killSwitch: KillSwitchStatus;
  /** Dashboard loading state */
  loading: boolean;
  /** Dashboard error state */
  error: string | null;
  /** Last refresh timestamp */
  lastRefresh: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API RESPONSE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCCApiResponse<T> {
  data: T;
  timestamp: string;
  apiVersion: string;
}

export interface OCCAgentsResponse {
  agents: AgentLaneTile[];
  totalCount: number;
}

export interface OCCDecisionStreamResponse {
  items: DecisionStreamItem[];
  totalCount: number;
  hasMore: boolean;
}

export interface OCCGovernanceResponse {
  rail: GovernanceRailState;
}

export interface OCCKillSwitchResponse {
  status: KillSwitchStatus;
}
