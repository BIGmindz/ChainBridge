/**
 * IoT Client
 *
 * Facade responsible for fetching ChainSense IoT telemetry. It mirrors the
 * pattern used by metricsClient/shipmentsClient by choosing between the real
 * FastAPI backend and mock data generators at runtime.
 */

import { config } from "../config/env";
import type { IoTHealthSummary, ShipmentIoTSnapshot } from "../lib/iot";

import { mockApiClient } from "./api";
import {
  fetchIoTHealthSummary as realFetchIoTHealthSummary,
  fetchShipmentIoTSnapshot as realFetchShipmentIoTSnapshot,
} from "./realApiClient";

const HAS_REAL_API = Boolean(import.meta.env.VITE_API_BASE_URL);
const USE_REAL_API = !config.useMocks && HAS_REAL_API;

if (import.meta.env.DEV) {
  console.log(
    `[iotClient] Using ${USE_REAL_API ? "real" : "mock"} API for IoT telemetry.`
  );
}

async function withMockFallback<T>(action: () => Promise<T>, fallback: () => Promise<T>): Promise<T> {
  if (!USE_REAL_API) {
    return fallback();
  }

  try {
    return await action();
  } catch (error) {
    if (config.isDevelopment) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`[iotClient] Falling back to mock data: ${message}`);
    }
    return fallback();
  }
}

export const iotClient = {
  async getHealthSummary(): Promise<IoTHealthSummary> {
    return withMockFallback(
      () => realFetchIoTHealthSummary(),
      () => mockApiClient.getMockIoTHealthSummary()
    );
  },

  async getShipmentSnapshot(shipmentId: string): Promise<ShipmentIoTSnapshot | null> {
    return withMockFallback<ShipmentIoTSnapshot | null>(
      () => realFetchShipmentIoTSnapshot(shipmentId),
      () => mockApiClient.getMockShipmentIoTSnapshot(shipmentId)
    );
  },
};
