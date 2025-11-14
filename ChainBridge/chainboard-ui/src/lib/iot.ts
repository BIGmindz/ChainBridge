/**
 * Frontend IoT contracts shared between components and API clients.
 * These re-export the canonical domain types defined in src/lib/types.ts.
 */
export type {
  IoTSensorType,
  Severity,
  IoTSensorReading,
  IoTHealthSummary,
  ShipmentIoTSnapshot,
} from "./types";
