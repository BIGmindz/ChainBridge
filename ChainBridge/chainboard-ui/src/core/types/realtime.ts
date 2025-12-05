// chainboard-ui/src/core/types/realtime.ts
/**
 * Real-Time Event Types
 * =====================
 *
 * TypeScript types for Server-Sent Events (SSE) from the Control Tower.
 * Matches backend schema in api/schemas/chainboard.py
 */

export type ControlTowerEventType =
  | "alert_created"
  | "alert_updated"
  | "alert_status_changed"
  | "alert_note_added"
  | "iot_reading"
  | "shipment_event"
  | "payment_state_changed";

export interface ControlTowerEvent {
  id: string;
  type: ControlTowerEventType;
  timestamp: string;
  source: string;
  key: string;
  payload: Record<string, unknown>;
}

/**
 * Payment Event Types
 */

export type PaymentEventKind =
  | "milestone_became_eligible"
  | "milestone_released"
  | "milestone_settled"
  | "milestone_blocked"
  | "milestone_unblocked";

export interface PaymentSettlementEventPayload {
  event_kind: PaymentEventKind;
  shipment_reference: string;
  milestone_id: string;
  milestone_name: string;
  from_state: string;
  to_state: string;
  amount: number;
  currency: string;
  reason?: string;
  freight_token_id?: number;
  proofpack_hint?: {
    milestone_id: string;
    has_proofpack: boolean;
    version: string;
  };
}
