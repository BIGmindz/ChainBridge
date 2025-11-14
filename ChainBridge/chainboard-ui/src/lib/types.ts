/**
 * Core domain types for ChainBoard UI
 * These models intentionally mirror the backend split between ChainFreight, ChainIQ, and ChainPay.
 * They are shared across UI pages, API clients, and tests to keep the contract strict and explicit.
 */

export type ISODateString = string;

export type RiskCategory = "low" | "medium" | "high";

export type PaymentState =
  | "not_started"
  | "in_progress"
  | "partially_paid"
  | "blocked"
  | "completed";

export type ShipmentStatus =
  | "pickup"
  | "in_transit"
  | "delivery"
  | "delayed"
  | "blocked"
  | "completed";

export type FreightMode = "ocean" | "air" | "ground";

export type ExceptionCode =
  | "late_pickup"
  | "late_delivery"
  | "no_update"
  | "payment_blocked"
  | "risk_spike";

export interface ShipmentEvent {
  code: string;
  description: string;
  at: ISODateString;
  location: string;
}

export interface RiskProfile {
  score: number; // 0-100
  category: RiskCategory;
  drivers: string[];
  assessedAt: ISODateString;
  watchlisted?: boolean;
}

export interface PaymentMilestone {
  label: string;
  percentage: number; // 0-100
  state: "pending" | "released" | "blocked";
  releasedAt?: ISODateString;
}

export interface PaymentProfile {
  state: PaymentState;
  totalValueUsd: number;
  releasedPercentage: number;
  holdsUsd: number;
  milestones: PaymentMilestone[];
  updatedAt: ISODateString;
}

export interface GovernanceSnapshot {
  proofpackStatus: "VERIFIED" | "FAILED" | "PENDING";
  lastAudit: ISODateString;
  exceptions: ExceptionCode[];
}

export interface FreightDetail {
  mode: FreightMode;
  incoterm: string;
  vessel?: string;
  container?: string;
  lane: string; // e.g., "Shanghai → Los Angeles"
  departure: ISODateString | null;
  eta: ISODateString | null;
  events: ShipmentEvent[];
}

export interface Shipment {
  id: string;
  reference: string;
  status: ShipmentStatus;
  origin: string;
  destination: string;
  carrier: string;
  customer: string;
  freight: FreightDetail;
  risk: RiskProfile;
  payment: PaymentProfile;
  governance: GovernanceSnapshot;
}

export type PaymentRailId = "bank_wire" | "ach" | "swift" | "blockchain";

export interface PaymentRailMetrics {
  id: PaymentRailId;
  label: string;
  description: string;
  avg_settlement_hours: number;
  avg_fee_usd: number;
  avg_fx_spread_bps: number;
  fail_rate_bps: number;
  capital_locked_hours: number;
}

export type IoTSensorType = "temperature" | "humidity" | "door" | "shock" | "gps" | "custom";

export type Severity = "info" | "warn" | "critical";

export interface IoTSensorReading {
  sensor_type: IoTSensorType;
  value: number | string;
  unit?: string | null;
  timestamp: ISODateString;
  status: Severity;
}

export interface IoTHealthSummary {
  shipments_with_iot: number;
  active_sensors: number;
  alerts_last_24h: number;
  critical_alerts_last_24h: number;
  coverage_percent: number;
}

export interface ShipmentIoTSnapshot {
  shipment_id: string;
  latest_readings: IoTSensorReading[];
  alert_count_24h: number;
  critical_alerts_24h: number;
}
