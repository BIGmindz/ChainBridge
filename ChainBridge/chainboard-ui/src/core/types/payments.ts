/**
 * ChainPay Payment Intelligence Types
 *
 * Payment state tracking, milestone management, and hold resolution.
 * Aligned with backend PaymentQueueResponse schema.
 */

import type { ISODateString, PaymentState, RiskCategory } from "../../lib/types";

/**
 * Payment queue item (shipment with payment hold)
 * Matches backend PaymentQueueItem from api/schemas/chainboard.py
 */
export interface PaymentQueueItem {
  shipmentId: string;
  reference: string;
  corridor: string;
  customer: string;
  total_valueUsd: string | number; // Decimal from backend
  holds_usd: string | number; // Decimal from backend
  released_usd: string | number; // Decimal from backend
  aging_days: number;
  riskCategory?: RiskCategory;
  milestone_id: string;
  freight_token_id?: number | null;
  proofpack_hint?: {
    milestone_id: string;
    has_proofpack: boolean;
    version: string;
  } | null;
}

/**
 * Payment queue API response envelope
 * Matches backend PaymentQueueResponse from api/schemas/chainboard.py
 */
export interface PaymentQueueEnvelope {
  items: PaymentQueueItem[];
  total_items: number;
  total_holds_usd: string | number; // Decimal from backend
  generatedAt: ISODateString;
}

/**
 * Payment milestone
 */
export interface PaymentMilestone {
  milestone_id: string;
  label: string;
  percentage: number;
  state: "pending" | "released" | "blocked";
  released_at?: ISODateString;
  freight_token_id?: number | null;
}

/**
 * Payment profile (embedded in shipment)
 */
export interface PaymentProfile {
  state: PaymentState;
  total_valueUsd: number;
  released_usd: number;
  released_percentage: number;
  holds_usd: number;
  milestones: PaymentMilestone[];
  updatedAt: ISODateString;
}

/**
 * Payment filter criteria
 */
export interface PaymentFilter {
  state?: PaymentState | PaymentState[];
  hasHolds?: boolean;
  minValue?: number;
  maxValue?: number;
}

/**
 * Type guards
 */
export function isPaymentState(value: unknown): value is PaymentState {
  return (
    typeof value === "string" &&
    ["not_started", "in_progress", "partially_paid", "blocked", "completed"].includes(value)
  );
}
