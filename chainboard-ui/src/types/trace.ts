/**
 * ChainBridge Trace Types
 * PAC-009: Full End-to-End Traceability — ORDER 4 (Sonny GID-02)
 * 
 * TypeScript types for trace visibility in Operator Console.
 * 
 * GOVERNANCE INVARIANTS:
 * - INV-TRACE-004: OC renders full chain without inference
 * - INV-TRACE-005: Missing links are explicit and non-silent
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

export const UNAVAILABLE_MARKER = 'UNAVAILABLE';

// ═══════════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════════

export type TraceDomain = 'DECISION' | 'EXECUTION' | 'SETTLEMENT' | 'LEDGER';

export type TraceLinkType =
  | 'PDO_TO_DECISION'
  | 'DECISION_TO_EXECUTION'
  | 'EXECUTION_TO_SETTLEMENT'
  | 'SETTLEMENT_TO_LEDGER'
  | 'DIRECT_REFERENCE';

export type TraceNodeStatus = 'PRESENT' | 'MISSING' | 'PARTIAL' | 'ERROR';

export type TraceViewStatus = 'COMPLETE' | 'INCOMPLETE' | 'ERROR';

// ═══════════════════════════════════════════════════════════════════════════════
// TRACE LINK
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceLink {
  trace_id: string;
  sequence_number: number;
  source_domain: TraceDomain;
  source_id: string;
  target_domain: TraceDomain;
  target_id: string;
  link_type: TraceLinkType;
  pac_id: string;
  pdo_id: string | null;
  agent_gid: string | null;
  trace_hash: string;
  previous_hash: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TRACE NODES
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceDecisionNode {
  node_id: string;
  domain: 'DECISION';
  status: TraceNodeStatus;
  pdo_id: string;
  decision_id: string;
  rationale_id: string | null;
  summary: string;
  confidence_score: number;
  factor_count: number;
  top_factors: DecisionFactorSummary[];
  timestamp: string;
  trace_hash: string;
}

export interface DecisionFactorSummary {
  factor_id: string;
  factor_type: string;
  factor_name: string;
  factor_value: unknown;
  weight: number;
  confidence: number;
}

export interface TraceExecutionNode {
  node_id: string;
  domain: 'EXECUTION';
  status: TraceNodeStatus;
  execution_id: string;
  pac_id: string;
  agent_gid: string | null;
  agent_name: string;
  agent_state: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  trace_hash: string;
  ledger_entry_hash: string;
}

export interface TraceSettlementNode {
  node_id: string;
  domain: 'SETTLEMENT';
  status: TraceNodeStatus;
  settlement_id: string;
  outcome_id: string | null;
  outcome_status: string;
  pdo_id: string;
  pac_id: string;
  settled_at: string | null;
  trace_hash: string;
}

export interface TraceLedgerNode {
  node_id: string;
  domain: 'LEDGER';
  status: TraceNodeStatus;
  ledger_entry_id: string;
  sequence_number: number;
  entry_type: string;
  entry_hash: string;
  previous_hash: string;
  pac_id: string;
  timestamp: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TRACE GAP (INV-TRACE-005)
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceGap {
  gap_id: string;
  gap_type: 'DOMAIN_NOT_LINKED' | 'LINK_MISSING' | 'DATA_UNAVAILABLE';
  from_domain: TraceDomain | null;
  to_domain: TraceDomain | null;
  missing_entity_id: string | null;
  message: string;
  timestamp: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// OC_TRACE_VIEW DTO
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCTraceView {
  pdo_id: string;
  pac_id: string;
  decision_nodes: TraceDecisionNode[];
  execution_nodes: TraceExecutionNode[];
  settlement_nodes: TraceSettlementNode[];
  ledger_nodes: TraceLedgerNode[];
  trace_links: TraceLink[];
  gaps: TraceGap[];
  status: TraceViewStatus;
  completeness_score: number;
  aggregated_at: string;
  aggregator_version: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceTimelineEvent {
  event_id: string;
  event_type: TraceLinkType;
  source_domain: TraceDomain;
  target_domain: TraceDomain;
  source_id: string;
  target_id: string;
  agent_gid: string | null;
  trace_hash: string;
  timestamp: string;
}

export interface OCTraceTimeline {
  pdo_id: string;
  events: TraceTimelineEvent[];
  event_count: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PAC SUMMARY
// ═══════════════════════════════════════════════════════════════════════════════

export interface PDOTraceSummary {
  pdo_id: string;
  status: TraceViewStatus;
  completeness_score: number;
  total_nodes: number;
  gap_count: number;
}

export interface PACTraceSummary {
  pac_id: string;
  pdo_count: number;
  total_trace_links: number;
  total_gaps: number;
  pdo_summaries: PDOTraceSummary[];
  aggregated_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceNavigation {
  full_trace_url: string;
  timeline_url: string;
  gaps_url: string;
}

export interface TraceNavigationContext {
  domain: TraceDomain;
  entity_id: string;
  pdo_id: string;
  outbound_links: TraceLink[];
  inbound_links: TraceLink[];
  total_links: number;
  navigation?: TraceNavigation;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CHAIN VERIFICATION
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceChainVerification {
  chain_valid: boolean;
  error_message: string | null;
  total_links: number;
  latest_hash?: string;
  latest_timestamp?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API RESPONSE WRAPPERS
// ═══════════════════════════════════════════════════════════════════════════════

export interface TraceGapsResponse {
  pdo_id: string;
  gaps: TraceGap[];
  gap_count: number;
  completeness_score: number;
  status: TraceViewStatus;
}

export interface TraceLinkListResponse {
  pac_id: string;
  links: TraceLink[];
  link_count: number;
  domain_filter: string | null;
}
