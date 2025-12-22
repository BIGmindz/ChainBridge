/**
 * ChainSense IoT Telemetry Types
 *
 * Real-time sensor data, environmental monitoring, and device health.
 * Aligned with backend api/schemas/chainboard.py IoT models.
 */

import type { ISODateString } from "../../lib/types";

// ============================================================================
// ENUMS
// ============================================================================

/**
 * IoT sensor hardware types
 * Matches backend IoTSensorType enum
 */
export type IoTSensorType =
  | "temperature"
  | "humidity"
  | "door"
  | "shock"
  | "gps"
  | "custom";

/**
 * IoT alert severity levels
 * Matches backend IoTSeverity enum
 */
export type IoTSeverity = "info" | "warn" | "critical";

export type IoTAnomalySeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

// ============================================================================
// CORE MODELS
// ============================================================================

/**
 * Individual sensor reading
 * Matches backend IoTSensorReading Pydantic model
 */
export interface IoTSensorReading {
  sensor_type: IoTSensorType;
  value: number | string; // numeric or string depending on sensor
  unit?: string | null; // e.g., 'C', '%', 'G'
  timestamp: ISODateString;
  status: IoTSeverity;
}

/**
 * IoT telemetry snapshot for a single shipment
 * Matches backend ShipmentIoTSnapshot Pydantic model
 */
export interface ShipmentIoTSnapshot {
  shipmentId: string;
  latest_readings: IoTSensorReading[];
  alert_count_24h: number;
  critical_alerts_24h: number;
}

/**
 * Network-wide IoT health metrics
 * Matches backend IoTHealthSummary Pydantic model
 */
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

// ============================================================================
// RESPONSE ENVELOPES
// ============================================================================

/**
 * Response envelope for GET /api/chainboard/iot/health
 * Matches backend IoTHealthSummaryResponse
 */
export interface IoTHealthEnvelope {
  summary: IoTHealthSummary;
}

/**
 * Response envelope for GET /api/chainboard/metrics/iot/shipments/{id}
 * Matches backend ShipmentIoTSnapshotResponse
 */
export interface ShipmentIoTSnapshotEnvelope {
  snapshot: ShipmentIoTSnapshot;
  retrieved_at: ISODateString;
}

/**
 * Response envelope for GET /api/chainboard/metrics/iot/shipments
 * Matches backend ShipmentIoTSnapshotsResponse
 */
export interface ShipmentIoTSnapshotsEnvelope {
  snapshots: ShipmentIoTSnapshot[];
  total: number;
  available: number;
  filtered: boolean;
  generatedAt: ISODateString;
}

// ============================================================================
// TYPE GUARDS
// ============================================================================

export function isIoTSeverity(value: unknown): value is IoTSeverity {
  return typeof value === "string" && ["info", "warn", "critical"].includes(value);
}

export function isIoTSensorType(value: unknown): value is IoTSensorType {
  return typeof value === "string" &&
    ["temperature", "humidity", "door", "shock", "gps", "custom"].includes(value);
}
