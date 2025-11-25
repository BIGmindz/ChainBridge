/**
 * Event & Activity Types
 *
 * Manifest events, shipment activity tracking, and audit trail.
 */

import type { ISODateString } from "../../lib/types";

/**
 * Manifest event from ChainFreight activity stream
 */
export interface ManifestEvent {
  code: string;
  description: string;
  at: ISODateString;
  location: string;
  metadata?: Record<string, unknown>;
}

/**
 * Shipment event envelope response
 */
export interface ShipmentEventEnvelope {
  events: ManifestEvent[];
  shipmentId: string;
  total_count: number;
}

/**
 * Event filter criteria
 */
export interface EventFilter {
  shipmentId?: string;
  startDate?: ISODateString;
  endDate?: ISODateString;
  eventCode?: string;
}

/**
 * Timeline Event Types (ChainBoard Timeline System)
 */
export type ShipmentEventType =
  | "created"
  | "booked"
  | "picked_up"
  | "departed_port"
  | "arrived_port"
  | "customs_hold"
  | "customs_released"
  | "delivered"
  | "payment_release"
  | "iot_alert";

/**
 * Timeline event from shipment lifecycle
 */
export interface TimelineEvent {
  shipmentId: string;
  reference: string;
  corridor: string;
  eventType: ShipmentEventType;
  description: string;
  occurredAt: string; // ISO timestamp from backend
  source: string;
  severity?: string | null;
}

/**
 * Timeline event envelope response
 */
export interface TimelineEventEnvelope {
  events: TimelineEvent[];
  total: number;
  generatedAt: string;
}
