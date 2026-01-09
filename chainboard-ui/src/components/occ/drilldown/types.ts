/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Agent Drilldown Types — Agent History & Evidence Display
 * PAC-BENSON-P22-C: OCC + Control Plane Deepening
 * 
 * Type definitions for agent drilldown components:
 * - Agent execution history
 * - Failure records
 * - Evidence artifacts
 * - Performance metrics
 * 
 * INVARIANTS:
 * - INV-OCC-005: Evidence immutability
 * - INV-OCC-006: No hidden transitions
 * 
 * Author: SONNY (GID-02) — Frontend Lead
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT EXECUTION HISTORY
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Agent execution status
 */
export type AgentExecutionStatus = 
  | 'success'
  | 'partial_success'
  | 'failed'
  | 'blocked'
  | 'cancelled';

/**
 * Single execution record
 */
export interface AgentExecutionRecord {
  executionId: string;
  pacId: string;
  pacTitle: string;
  status: AgentExecutionStatus;
  startedAt: string;
  completedAt?: string;
  durationMs?: number;
  tasksAssigned: number;
  tasksCompleted: number;
  tasksFailed: number;
  failureReason?: string;
  evidenceHash: string;
}

/**
 * Agent failure record
 */
export interface AgentFailureRecord {
  failureId: string;
  executionId: string;
  pacId: string;
  timestamp: string;
  failureType: 'task_error' | 'timeout' | 'governance_block' | 'dependency_failure' | 'unknown';
  errorMessage: string;
  stackTrace?: string;
  context?: Record<string, unknown>;
  resolved: boolean;
  resolvedAt?: string;
  resolution?: string;
}

/**
 * Agent evidence artifact
 */
export interface AgentEvidenceArtifact {
  artifactId: string;
  executionId: string;
  pacId: string;
  artifactType: 'pdo' | 'file_change' | 'api_call' | 'command' | 'ack' | 'wrap' | 'ber' | 'other';
  title: string;
  description: string;
  timestamp: string;
  evidenceHash: string;
  size?: number;
  path?: string;
  metadata?: Record<string, unknown>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT PERFORMANCE METRICS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Agent performance metrics
 */
export interface AgentPerformanceMetrics {
  agentId: string;
  agentName: string;
  /** Total PACs participated in */
  totalPacsParticipated: number;
  /** Total tasks completed */
  totalTasksCompleted: number;
  /** Total tasks failed */
  totalTasksFailed: number;
  /** Success rate (0-100) */
  successRate: number;
  /** Average task duration in ms */
  avgTaskDurationMs: number;
  /** Average ACK latency in ms */
  avgAckLatencyMs: number;
  /** Last active timestamp */
  lastActiveAt: string;
  /** Uptime percentage (0-100) */
  uptimePercent: number;
  /** Current execution streak (consecutive successes) */
  currentStreak: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT DRILLDOWN STATE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Complete agent drilldown state
 */
export interface AgentDrilldownState {
  /** Agent GID */
  agentId: string;
  /** Agent name */
  agentName: string;
  /** Agent lane */
  lane: string;
  /** Current health state */
  health: 'healthy' | 'degraded' | 'critical' | 'unknown';
  /** Current execution state */
  executionState: 'idle' | 'executing' | 'blocked' | 'completed' | 'failed';
  /** Current PAC (if executing) */
  currentPacId?: string;
  /** Performance metrics */
  metrics: AgentPerformanceMetrics;
  /** Recent executions (paginated) */
  recentExecutions: AgentExecutionRecord[];
  /** Recent failures (paginated) */
  recentFailures: AgentFailureRecord[];
  /** Recent evidence artifacts (paginated) */
  recentArtifacts: AgentEvidenceArtifact[];
  /** Last updated timestamp */
  lastUpdated: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// DRILLDOWN VIEW PROPS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Tab options for agent drilldown
 */
export type AgentDrilldownTab = 'overview' | 'executions' | 'failures' | 'evidence' | 'metrics';

/**
 * Agent drilldown component props
 */
export interface AgentDrilldownProps {
  /** Agent ID to drill down on */
  agentId: string;
  /** Drilldown state (from API) */
  state?: AgentDrilldownState;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: string | null;
  /** Active tab */
  activeTab?: AgentDrilldownTab;
  /** Callback when tab changes */
  onTabChange?: (tab: AgentDrilldownTab) => void;
  /** Callback to close drilldown */
  onClose?: () => void;
  /** Callback when execution is selected */
  onExecutionSelect?: (execution: AgentExecutionRecord) => void;
  /** Callback when artifact is selected */
  onArtifactSelect?: (artifact: AgentEvidenceArtifact) => void;
}
