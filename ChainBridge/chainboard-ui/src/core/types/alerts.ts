// chainboard-ui/src/core/types/alerts.ts
/**
 * Alert & Triage Types
 * Unified alert system across risk, IoT, payment, and customs domains.
 */

export type AlertSeverity = "info" | "warning" | "critical";
export type AlertSource = "risk" | "iot" | "payment" | "customs";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface ControlTowerAlert {
  id: string;
  shipment_reference: string;
  title: string;
  description: string;
  source: AlertSource;
  severity: AlertSeverity;
  status: AlertStatus;
  createdAt: string;
  updatedAt: string;
  tags: string[];
}

export interface AlertsEnvelope {
  alerts: ControlTowerAlert[];
  total: number;
  generatedAt: string;
}

// ============================================================================
// TRIAGE & WORK QUEUE TYPES
// ============================================================================

export interface AlertOwner {
  id: string;
  name: string;
  email?: string;
  team?: string;
}

export interface AlertNote {
  id: string;
  alert_id: string;
  author: AlertOwner;
  message: string;
  createdAt: string;
}

export type AlertActionType =
  | "assign"
  | "acknowledge"
  | "resolve"
  | "comment"
  | "escalate"
  | "hold_payment"
  | "release_payment"
  | "customs_expedite";

export interface AlertActionRecord {
  id: string;
  alert_id: string;
  type: AlertActionType;
  actor: AlertOwner;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface AlertWorkItem {
  alert: ControlTowerAlert;
  owner?: AlertOwner | null;
  notes: AlertNote[];
  actions: AlertActionRecord[];
}

export interface AlertWorkQueueResponse {
  items: AlertWorkItem[];
  total: number;
}
