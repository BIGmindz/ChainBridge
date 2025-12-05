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
  assessed_at: ISODateString;
  watchlisted?: boolean;
}

export interface PaymentMilestone {
  milestone_id: string;
  label: string;
  percentage: number; // 0-100
  state: "pending" | "released" | "blocked";
  released_at?: ISODateString;
  freight_token_id?: number;
}

export interface PaymentProfile {
  state: PaymentState;
  total_valueUsd: number;
  released_usd: number;
  released_percentage: number;
  holds_usd: number;
  milestones: PaymentMilestone[];
  updatedAt: ISODateString;
}

export interface GovernanceSnapshot {
  proofpack_status: "VERIFIED" | "FAILED" | "PENDING";
  last_audit: ISODateString;
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
  corridor: string;
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

export type IoTAnomalySeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface IoTSensorReading {
  sensor_type: IoTSensorType;
  value: number | string;
  unit?: string | null;
  timestamp: ISODateString;
  status: Severity;
}

export interface IoTDeviceAnomaly {
  deviceId: string;
  severity: IoTAnomalySeverity;
  label: string;
  lastSeen: ISODateString;
  shipmentReference?: string;
  lane?: string;
}

export interface IoTHealthSummary {
  fleetId: string;
  asOf: ISODateString;
  deviceCount: number;
  online: number;
  offline: number;
  degraded: number;
  anomalies: IoTDeviceAnomaly[];
  latencySeconds?: number;
}

export interface IoTHealthSummaryResponse {
  summary: IoTHealthSummary;
}

export interface ShipmentIoTSnapshot {
  shipmentId: string;
  latest_readings: IoTSensorReading[];
  alert_count_24h: number;
  critical_alerts_24h: number;
}

export interface ExceptionRow {
  shipmentId: string;
  lane: string;
  current_status: ShipmentStatus;
  riskScore: number;
  payment_state: PaymentState;
  age_of_issue: string;
  issue_types: ExceptionCode[];
  last_update: string;
}

export interface NetworkVitals {
  active_shipments: number;
  on_time_percent: number;
  at_risk_shipments: number;
  open_payment_holds: number;
}
