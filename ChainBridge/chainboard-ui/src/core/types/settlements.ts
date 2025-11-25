/**
 * Settlement Action Types
 *
 * Types for operator actions on payment milestones.
 * Used for settlement workflow operations and audit trail.
 */

export type SettlementActionKind =
  | "escalate_to_risk"
  | "mark_manually_reviewed"
  | "request_documentation";

export interface SettlementActionRequest {
  reason?: string;
  requestedBy?: string;
}

export interface SettlementActionResponse {
  status: string;        // e.g. "accepted"
  milestoneId: string;
  action: SettlementActionKind;
  note?: string;
  requestedBy?: string | null;
  createdAt?: string;    // ISO timestamp if backend returns it
}
