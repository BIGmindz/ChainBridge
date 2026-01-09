/**
 * Operator Console Types — TypeScript Interfaces for OC API
 * 
 * PAC Reference: PAC-BENSON-CHAINBRIDGE-PDO-OC-VISIBILITY-EXEC-007C
 * Agent: Sonny (GID-02) — UI
 * Effective Date: 2025-12-30
 * 
 * These types match the OC_PDO_VIEW contract from PAC-007C Section 8.
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

export const OC_API_VERSION = '1.0.0';
export const UNAVAILABLE_MARKER = 'UNAVAILABLE';

// ═══════════════════════════════════════════════════════════════════════════════
// PDO VIEWS
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * OC_PDO_VIEW — Per PAC-007C Section 8 OC JOIN CONTRACT.
 */
export interface OCPDOView {
  pdo_id: string;
  decision_id: string | null;
  outcome_id: string | null;
  settlement_id: string | null;
  ledger_entry_hash: string;
  sequence_number: number;
  timestamp: string;
  
  // Extended fields
  pac_id?: string | null;
  outcome_status?: string | null;
  issuer?: string | null;
}

export interface OCPDOListResponse {
  items: OCPDOView[];
  count: number;
  total: number;
  limit: number;
  offset: number;
  api_version: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETTLEMENT VIEWS
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCMilestone {
  milestone_id: string;
  name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  ledger_hash?: string;
}

/**
 * Settlement view — INV-OC-002: Every settlement links to PDO ID.
 */
export interface OCSettlementView {
  settlement_id: string;
  pdo_id: string; // Required: INV-OC-002
  status: string;
  initiated_at: string;
  completed_at: string | null;
  ledger_entry_hash: string;
  milestones: OCMilestone[];
  current_milestone: string | null;
  trace_log: string[];
}

export interface OCSettlementListResponse {
  items: OCSettlementView[];
  count: number;
  total: number;
  limit: number;
  offset: number;
  api_version: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TIMELINE
// ═══════════════════════════════════════════════════════════════════════════════

export type OCTimelineEventType =
  | 'PDO_CREATED'
  | 'PDO_UPDATED'
  | 'SETTLEMENT_INITIATED'
  | 'MILESTONE_STARTED'
  | 'MILESTONE_COMPLETED'
  | 'SETTLEMENT_COMPLETED'
  | 'SETTLEMENT_LEDGER_ENTRY'
  | 'LEDGER_ENTRY';

export interface OCTimelineEvent {
  event_id: string;
  event_type: OCTimelineEventType | string;
  timestamp: string;
  pdo_id?: string | null;
  settlement_id?: string | null;
  ledger_hash: string;
  details: Record<string, unknown>;
}

export interface OCTimelineResponse {
  events: OCTimelineEvent[];
  pdo_id: string | null;
  settlement_id: string | null;
  span_start: string | null;
  span_end: string | null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LEDGER VIEWS
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCLedgerEntry {
  entry_id: string;
  sequence_number: number;
  timestamp: string;
  entry_hash: string;
  previous_hash: string;
  entry_type: string;
  reference_id: string;
}

export interface OCLedgerVerifyResponse {
  chain_valid: boolean;
  error: string | null;
  entry_count: number;
  verified_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// HEALTH
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCHealthResponse {
  status: 'ok' | 'error';
  api_version: string;
  read_only: boolean;
  timestamp: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// API ERROR
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCAPIError {
  error: string;
  message: string;
  method?: string;
  path?: string;
  invariant?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// FILTER OPTIONS
// ═══════════════════════════════════════════════════════════════════════════════

export interface OCPDOFilters {
  outcome_status?: string;
  pac_id?: string;
  has_settlement?: boolean;
  limit?: number;
  offset?: number;
}

export interface OCSettlementFilters {
  pdo_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// OUTCOME STATUS
// ═══════════════════════════════════════════════════════════════════════════════

export type PDOOutcomeStatus = 'ACCEPTED' | 'CORRECTIVE' | 'REJECTED' | 'PENDING';

export const OUTCOME_STATUS_COLORS: Record<PDOOutcomeStatus, string> = {
  ACCEPTED: '#22c55e',    // green-500
  CORRECTIVE: '#f59e0b',  // amber-500
  REJECTED: '#ef4444',    // red-500
  PENDING: '#6b7280',     // gray-500
};

export const OUTCOME_STATUS_BG_COLORS: Record<PDOOutcomeStatus, string> = {
  ACCEPTED: 'bg-green-100 text-green-800',
  CORRECTIVE: 'bg-amber-100 text-amber-800',
  REJECTED: 'bg-red-100 text-red-800',
  PENDING: 'bg-gray-100 text-gray-800',
};
