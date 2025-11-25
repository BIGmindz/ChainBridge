/**
 * Query Keys Registry
 *
 * Stable cache keys for the Control Tower data layer.
 * Prevents cache key collisions and ensures predictable invalidation.
 */

import type { PaymentFilter, ShipmentFilter } from "../types";

// Simple exception filter type (can be expanded later)
interface ExceptionFilter {
  corridor?: string;
  severity?: string;
  acknowledged?: boolean;
}

/**
 * Stable query key generators for all Control Tower modules.
 * Keys are arrays to enable partial matching and granular invalidation.
 */
export const QUERY_KEYS = {
  // -------------------------------------------------------------------------
  // Shipments & Manifest
  // -------------------------------------------------------------------------

  shipments: (filters?: ShipmentFilter) => {
    const key = JSON.stringify(filters ?? {});
    return ["shipments", key] as const;
  },

  shipmentById: (id: string) => ["shipments", "detail", id] as const,

  // -------------------------------------------------------------------------
  // Events & Activity
  // -------------------------------------------------------------------------

  events: (shipmentId?: string) => {
    return shipmentId ? ["events", shipmentId] as const : ["events"] as const;
  },

  // -------------------------------------------------------------------------
  // Exceptions & Alerts
  // -------------------------------------------------------------------------

  exceptions: (filters?: ExceptionFilter) => {
    const key = JSON.stringify(filters ?? {});
    return ["exceptions", key] as const;
  },

  // -------------------------------------------------------------------------
  // ChainIQ Risk Intelligence
  // -------------------------------------------------------------------------

  iq: (shipmentId: string) => ["iq", shipmentId] as const,

  riskOverview: () => ["risk", "overview"] as const,

  riskStories: (limit?: number) => {
    const key = limit ? String(limit) : "default";
    return ["risk", "stories", key] as const;
  },

  // -------------------------------------------------------------------------
  // ChainPay Payment Intelligence
  // -------------------------------------------------------------------------

  payments: (shipmentId: string, filters?: PaymentFilter) => {
    const key = JSON.stringify(filters ?? {});
    return ["payments", shipmentId, key] as const;
  },

  paymentQueue: (limit?: number) => {
    const key = limit ? String(limit) : "default";
    return ["payments", "queue", key] as const;
  },

  // -------------------------------------------------------------------------
  // ChainSense IoT Telemetry
  // -------------------------------------------------------------------------

  iot: (shipmentId: string) => ["iot", shipmentId] as const,

  iotHealth: () => ["iot", "health"] as const,

  // -------------------------------------------------------------------------
  // Agent Health
  // -------------------------------------------------------------------------

  agentHealth: () => ["agents", "health", "summary"] as const,

  // -------------------------------------------------------------------------
  // Metrics & Overview
  // -------------------------------------------------------------------------

  globalSummary: () => ["metrics", "summary"] as const,

  corridorMetrics: () => ["metrics", "corridors"] as const,

  // -------------------------------------------------------------------------
  // Timeline Events
  // -------------------------------------------------------------------------

  timelineEvents: (limit: number) => ["timeline", "events", String(limit)] as const,

  shipmentEvents: (reference: string, limit: number) =>
    ["timeline", "shipment", reference, String(limit)] as const,

  // -------------------------------------------------------------------------
  // Alerts & Triage
  // -------------------------------------------------------------------------

  alerts: (filters?: { source?: string; severity?: string; status?: string }) => {
    const key = JSON.stringify(filters ?? {});
    return ["alerts", key] as const;
  },

  shipmentAlerts: (shipmentRef: string) => ["alerts", "shipment", shipmentRef] as const,

  alertWorkQueue: (params?: {
    ownerId?: string;
    status?: string;
    source?: string;
    severity?: string;
  }) => {
    const key = JSON.stringify(params ?? {});
    return ["alerts", "work-queue", key] as const;
  },
} as const;

/**
 * Helper to serialize query keys to string for storage/comparison
 */
export function serializeKey(key: readonly unknown[]): string {
  return JSON.stringify(key);
}

/**
 * Helper to check if two keys match (for partial invalidation)
 */
export function keysMatch(key1: readonly unknown[], key2: readonly unknown[]): boolean {
  if (key1.length > key2.length) return false;
  return key1.every((part, i) => part === key2[i]);
}
