/**
 * Dashboard-level metrics contracts for ChainBoard UI.
 * These types intentionally mirror the backend (FastAPI + Pydantic) models.
 * Any changes here must be coordinated with the backend since it will conform to this contract.
 */

import type { IoTHealthSummary } from "./iot";

/**
 * Overall threat posture for the watch floor.
 * Mirrors the badge you show in the top chrome: Normal / Elevated / Critical.
 */
export type ThreatLevel = "normal" | "elevated" | "critical";

/**
 * Shipment KPIs used by the Overview KPI strip.
 */
export interface ShipmentKpiSummary {
  /** Total shipments in the current watch window */
  total_shipments: number;
  /** Non-completed shipments */
  active_shipments: number;
  /** On-time percentage, 0–100 */
  on_time_percent: number;
  /** Count of shipments currently considered "exceptions" */
  exception_count: number;
  /** Count of shipments with high ChainIQ risk */
  high_risk_count: number;
  /** Count of shipments in delayed or blocked status */
  delayed_or_blocked_count: number;
}

/**
 * Aggregated payment health for the network.
 */
export interface PaymentHealthSummary {
  blocked_payments: number;
  partially_paid: number;
  completed: number;
  not_started: number;
  in_progress: number;
  /** 0–100 score summarizing payment posture */
  payment_health_score: number;
  /** Estimated hours of capital stuck in limbo (Nostro/Vostro style) */
  capital_locked_hours: number;
}

/**
 * Governance / compliance posture for the network.
 */
export interface GovernanceHealthSummary {
  /** Percent of shipments with valid, verified proofpacks */
  proofpack_ok_percent: number;
  /** Active audits / investigations */
  open_audits: number;
  /** Shipments on a governance watchlist */
  watchlisted_shipments: number;
}

/**
 * Directional risk trend for a lane / corridor.
 */
export type CorridorTrend = "rising" | "stable" | "improving";

/**
 * Corridor-level metrics backing the Corridor Intel panel and drilldowns.
 */
export interface CorridorMetrics {
  corridor_id: string; // e.g. "asia-us-west"
  label: string; // e.g. "Asia → US West"
  shipment_count: number;
  active_count: number;
  high_risk_count: number;
  blocked_payments: number;
  avg_risk_score: number;
  trend: CorridorTrend;
}

/**
 * GlobalSummary is the primary object the Overview page will hydrate from the backend.
 * It captures the high-level posture across shipments, payments, governance, corridors, and IoT.
 */
export interface GlobalSummary {
  threat_level: ThreatLevel;
  shipments: ShipmentKpiSummary;
  payments: PaymentHealthSummary;
  governance: GovernanceHealthSummary;
  /** Highest-priority corridor to look at (may be null if no shipments). */
  top_corridor: CorridorMetrics | null;
  /** Optional IoT health posture (null/undefined until backend supports it). */
  iot?: IoTHealthSummary | null;
}
