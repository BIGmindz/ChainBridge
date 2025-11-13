/**
 * Core domain types for ChainBridge Control Tower
 * These types mirror the backend data models from ChainFreight, ChainIQ, and ChainPay
 */

export type ShipmentStatus =
  | "pickup"
  | "in_transit"
  | "delivery"
  | "delayed"
  | "blocked"
  | "completed";

export type PaymentState =
  | "not_started"
  | "in_progress"
  | "partially_paid"
  | "blocked"
  | "completed";

export type RiskCategory = "low" | "medium" | "high";

export type IssueType =
  | "high_risk"
  | "late_pickup"
  | "late_delivery"
  | "no_update"
  | "payment_blocked";

export type ProofSignatureStatus = "VERIFIED" | "FAILED" | "PENDING";

/**
 * ChainFreight Event - immutable shipment event from ProofPack manifest
 */
export interface ShipmentEvent {
  event_type: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

/**
 * ChainIQ Risk Assessment - risk scoring result
 */
export interface RiskAssessment {
  risk_score: number; // 0-100
  risk_category: RiskCategory;
  recommended_action: string;
  confidence: number; // 0-100
}

/**
 * ChainPay Milestone - payment release schedule
 */
export interface PaymentMilestone {
  milestone: string;
  percentage: number; // 0-100
  status: "pending" | "released" | "blocked";
  amount_usd?: number;
  released_at?: string;
}

/**
 * ProofPack Summary - governance and audit proof
 */
export interface ProofPackSummary {
  pack_id: string;
  manifest_hash: string;
  signature_status: ProofSignatureStatus;
  created_at: string;
}

/**
 * Shipment - core domain entity combining freight, risk, and payment data
 */
export interface Shipment {
  shipment_id: string;
  token_id: string;
  carrier: string;
  customer: string;
  origin: string;
  destination: string;
  current_status: ShipmentStatus;
  current_event?: string;
  last_update_timestamp: string;
  created_at: string;

  // ChainFreight data
  events: ShipmentEvent[];

  // ChainIQ risk data
  risk: RiskAssessment;

  // ChainPay payment data
  payment_state: PaymentState;
  payment_schedule: PaymentMilestone[];
  total_value_usd: number;

  // Governance & audit
  proofpack: ProofPackSummary;
}

/**
 * Exception Row - simplified shipment view for exception reporting
 */
export interface ExceptionRow {
  shipment_id: string;
  lane: string; // "origin → destination"
  current_status: ShipmentStatus;
  risk_score: number;
  payment_state: PaymentState;
  age_of_issue: string; // human-readable, e.g. "3h"
  issue_types: IssueType[];
  last_update: string;
}

/**
 * Network Vitals - KPI data for dashboard
 */
export interface NetworkVitals {
  active_shipments: number;
  on_time_percent: number;
  at_risk_shipments: number;
  open_payment_holds: number;
}

/**
 * Filter State for Exceptions
 */
export interface ExceptionFilters {
  issue_types: Set<IssueType>;
  risk_min: number;
  risk_max: number;
  time_window: "2h" | "24h" | "7d";
}

/**
 * Saved View - user-defined exception view
 */
export interface SavedView {
  id: string;
  name: string;
  filters: ExceptionFilters;
  created_at: string;
}
