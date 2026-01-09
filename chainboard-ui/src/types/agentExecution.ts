/**
 * ChainBridge Agent Execution Types
 * PAC-008: Agent Execution Visibility — ORDER 3 (Sonny GID-02)
 * 
 * TypeScript interfaces for agent execution visibility in OC.
 * 
 * INVARIANTS:
 * - INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
 * - INV-AGENT-004: OC is read-only; no agent control actions
 * - INV-AGENT-005: Missing state must be explicit (no inference)
 */

/**
 * Agent execution states — INV-AGENT-003
 */
export type AgentState = 'QUEUED' | 'ACTIVE' | 'COMPLETE' | 'FAILED';

/**
 * Agent execution modes
 */
export type AgentExecutionMode = 'EXECUTION' | 'REVIEW';

/**
 * UNAVAILABLE marker for missing data — INV-AGENT-005
 */
export const UNAVAILABLE_MARKER = 'UNAVAILABLE';

/**
 * Agent execution view for OC display
 */
export interface AgentExecutionView {
  agent_gid: string;
  agent_name: string;
  agent_role: string;
  agent_color: string;
  current_state: AgentState;
  pac_id: string;
  execution_mode: AgentExecutionMode;
  execution_order: number | null;
  order_description: string;
  activated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  artifacts_created: string[];
  error_message: string | null;
  ledger_entry_hash: string;
}

/**
 * Timeline event for agent execution
 */
export interface AgentTimelineEvent {
  event_id: string;
  event_type: 'ACTIVATION' | 'STATE_CHANGE' | 'ARTIFACT_CREATED';
  timestamp: string;
  agent_gid: string;
  agent_name: string;
  description: string;
  previous_state: AgentState | null;
  new_state: AgentState | null;
  ledger_entry_hash: string;
}

/**
 * PAC execution view with all agents
 */
export interface PACExecutionView {
  pac_id: string;
  agents: AgentExecutionView[];
  timeline: AgentTimelineEvent[];
  total_agents: number;
  agents_queued: number;
  agents_active: number;
  agents_complete: number;
  agents_failed: number;
  execution_started_at: string | null;
  execution_completed_at: string | null;
  execution_status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETE' | 'FAILED';
}

/**
 * Response for agent list endpoints
 */
export interface AgentListResponse {
  items: AgentExecutionView[];
  count: number;
  total: number;
  limit: number;
  offset: number;
}

/**
 * Response for PAC list endpoint
 */
export interface PACListResponse {
  items: PACListItem[];
  count: number;
  total: number;
}

/**
 * PAC list item summary
 */
export interface PACListItem {
  pac_id: string;
  total_agents: number;
  agents_complete: number;
  agents_failed: number;
  execution_status: string;
  execution_started_at: string | null;
}

/**
 * State badge colors
 */
export const STATE_COLORS: Record<AgentState, string> = {
  QUEUED: 'bg-gray-500',
  ACTIVE: 'bg-blue-500',
  COMPLETE: 'bg-green-500',
  FAILED: 'bg-red-500',
};

/**
 * State badge labels
 */
export const STATE_LABELS: Record<AgentState, string> = {
  QUEUED: 'Queued',
  ACTIVE: 'Active',
  COMPLETE: 'Complete',
  FAILED: 'Failed',
};

/**
 * Agent color mappings for display
 */
export const AGENT_COLOR_MAP: Record<string, string> = {
  TEAL: 'bg-teal-500',
  BLUE: 'bg-blue-500',
  YELLOW: 'bg-yellow-500',
  PURPLE: 'bg-purple-500',
  ORANGE: 'bg-orange-500',
  'DARK RED': 'bg-red-800',
  GREEN: 'bg-green-500',
  WHITE: 'bg-gray-200',
  PINK: 'bg-pink-500',
};

/**
 * Format duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number | null): string {
  if (ms === null) return UNAVAILABLE_MARKER;
  
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
}

/**
 * Format timestamp to human-readable string
 */
export function formatTimestamp(iso: string | null): string {
  if (!iso) return UNAVAILABLE_MARKER;
  
  try {
    const date = new Date(iso);
    return date.toLocaleString();
  } catch {
    return UNAVAILABLE_MARKER;
  }
}
