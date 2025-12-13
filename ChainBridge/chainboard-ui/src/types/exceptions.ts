/**
 * Exception Domain Types
 *
 * Types for the Exception Cockpit (The OC V0.1)
 * These match the backend API models for exceptions, playbooks, and decision records.
 */

// =============================================================================
// EXCEPTION TYPES
// =============================================================================

/**
 * Exception severity levels
 */
export type ExceptionSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

/**
 * Exception status lifecycle
 */
export type ExceptionStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "DISMISSED";

/**
 * Exception type categories
 */
export type ExceptionType =
  | "RISK_THRESHOLD"
  | "PAYMENT_HOLD"
  | "ETA_BREACH"
  | "COMPLIANCE_FLAG"
  | "DOCUMENT_MISSING"
  | "IOT_ALERT"
  | "CARRIER_ISSUE"
  | "CUSTOMS_DELAY"
  | "ESG_VIOLATION"
  | "MANUAL";

/**
 * Core Exception entity
 */
export interface Exception {
  id: string;
  type: ExceptionType;
  severity: ExceptionSeverity;
  status: ExceptionStatus;
  summary: string;
  description?: string;
  shipment_id: string;
  shipment_reference?: string;
  playbook_id?: string;
  owner_id?: string;
  owner_name?: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  metadata?: Record<string, unknown>;
}

// =============================================================================
// PLAYBOOK TYPES
// =============================================================================

/**
 * Playbook step status
 */
export type PlaybookStepStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "SKIPPED";

/**
 * Individual playbook step
 */
export interface PlaybookStep {
  id: string;
  order: number;
  title: string;
  description: string;
  status: PlaybookStepStatus;
  completed_at?: string;
  completed_by?: string;
}

/**
 * Playbook entity - runbook for handling specific exception types
 */
export interface Playbook {
  id: string;
  name: string;
  description: string;
  exception_type: ExceptionType;
  steps: PlaybookStep[];
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

// =============================================================================
// SETTLEMENT POLICY TYPES
// =============================================================================

/**
 * Settlement milestone configuration
 */
export interface SettlementMilestone {
  id: string;
  name: string;
  percentage: number;
  trigger_event: string;
  order: number;
}

/**
 * Settlement policy entity
 */
export interface SettlementPolicy {
  id: string;
  name: string;
  description?: string;
  milestones: SettlementMilestone[];
  default_currency: string;
  conditions?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

// =============================================================================
// DECISION RECORD TYPES
// =============================================================================

/**
 * Decision record type categories
 */
export type DecisionType =
  | "RISK_DECISION"
  | "SETTLEMENT_DECISION"
  | "EXCEPTION_RESOLUTION"
  | "PLAYBOOK_STEP"
  | "MANUAL_OVERRIDE"
  | "AUTOMATED_ACTION";

/**
 * Decision record - audit trail for all decisions
 */
export interface DecisionRecord {
  id: string;
  type: DecisionType;
  actor: string;
  actor_type: "SYSTEM" | "OPERATOR" | "API";
  policy_id?: string;
  policy_name?: string;
  exception_id?: string;
  shipment_id?: string;
  summary: string;
  details?: Record<string, unknown>;
  created_at: string;
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

/**
 * Exceptions list response
 */
export interface ExceptionsListResponse {
  exceptions: Exception[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Exception detail response with related data
 */
export interface ExceptionDetailResponse {
  exception: Exception;
  playbook?: Playbook;
  recent_decisions: DecisionRecord[];
}

/**
 * Playbooks list response
 */
export interface PlaybooksListResponse {
  playbooks: Playbook[];
  total: number;
}

/**
 * Decision records list response
 */
export interface DecisionRecordsListResponse {
  records: DecisionRecord[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// KPI/SUMMARY TYPES
// =============================================================================

/**
 * Exception summary statistics for KPI display
 */
export interface ExceptionStats {
  total_open: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  resolved_today: number;
  avg_resolution_time_hours?: number;
}

/**
 * Risk summary for a shipment (ChainIQ stub)
 */
export interface ShipmentRiskSummary {
  shipment_id: string;
  risk_score: number;
  resilience_score?: number;
  esg_score?: number;
  risk_factors: Array<{
    factor: string;
    impact: number;
    description?: string;
  }>;
  last_updated: string;
}

/**
 * Settlement summary for a shipment (ChainPay stub)
 */
export interface ShipmentSettlementSummary {
  shipment_id: string;
  policy_id?: string;
  policy_name?: string;
  total_amount: number;
  released_amount: number;
  held_amount: number;
  currency: string;
  milestones: Array<{
    name: string;
    percentage: number;
    status: "COMPLETED" | "PENDING" | "HELD";
    completed_at?: string;
  }>;
  last_updated: string;
}
