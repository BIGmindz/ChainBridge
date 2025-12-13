/**
 * Shipment Domain Types
 *
 * Core types for ChainFreight shipment tracking and manifest intelligence.
 * Aligned with backend Pydantic schemas.
 */

import type {
  Shipment,
  ShipmentStatus,
  RiskCategory,
  PaymentState,
  FreightMode,
} from "../../lib/types";

// Re-export core types for convenience
export type {
  Shipment,
  ShipmentStatus,
  RiskCategory,
  PaymentState,
  FreightMode,
};

/**
 * Shipment filtering criteria
 */
export interface ShipmentFilter {
  corridor?: string;
  risk?: RiskCategory | RiskCategory[];
  status?: ShipmentStatus | ShipmentStatus[];
  search?: string;
  hasIoT?: boolean;
}

/**
 * Shipments API envelope response
 */
export interface ShipmentEnvelope {
  shipments: Shipment[];
  total: number;
  filtered: boolean;
}

/**
 * Type guards
 */
export function isRiskCategory(value: unknown): value is RiskCategory {
  return typeof value === "string" && ["low", "medium", "high"].includes(value);
}

export function isShipmentStatus(value: unknown): value is ShipmentStatus {
  return (
    typeof value === "string" &&
    ["pickup", "in_transit", "delivery", "delayed", "blocked", "completed"].includes(value)
  );
}
