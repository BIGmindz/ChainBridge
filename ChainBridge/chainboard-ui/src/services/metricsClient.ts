/**
 * Metrics Client
 *
 * This module acts as a facade for fetching dashboard metrics. It determines
 * whether to use the real API client or mock data based on the presence of
 * the VITE_API_BASE_URL environment variable.
 */

import { config } from "../config/env";
import type { IoTHealthSummary } from "../lib/iot";
import type { GlobalSummary, CorridorMetrics } from "../lib/metrics";

import { mockApiClient } from "./api";
import {
  fetchGlobalSummary as realFetchGlobalSummary,
  fetchCorridorMetrics as realFetchCorridorMetrics,
  fetchIoTHealthSummary as realFetchIoTHealthSummary,
} from "./realApiClient";

const HAS_REAL_API = Boolean(config.apiBaseUrl);
const USE_REAL_API = !config.useMocks && HAS_REAL_API;

function withMetricsFallback<T>(action: () => Promise<T>, fallback: () => Promise<T>): Promise<T> {
  if (!USE_REAL_API) {
    return fallback();
  }

  return action().catch((error) => {
    if (config.isDevelopment) {
      console.warn("[metricsClient] Falling back to mock metrics:", error);
    }
    return fallback();
  });
}

/**
 * A unified client for fetching all dashboard-related metrics.
 * It abstracts away the decision to use mock or real data sources.
 */
export const metricsClient = {
  /**
   * Fetches the global summary of all network metrics.
   * @returns A promise that resolves to the GlobalSummary object.
   */
  getGlobalSummary(): Promise<GlobalSummary> {
    return withMetricsFallback(
      () => realFetchGlobalSummary(),
      () => mockApiClient.getMockGlobalSummary()
    );
  },

  /**
   * Fetches metrics for all major trade corridors.
   * @returns A promise that resolves to an array of CorridorMetrics.
   */
  getCorridorMetrics(): Promise<CorridorMetrics[]> {
    return withMetricsFallback(
      () => realFetchCorridorMetrics(),
      () => mockApiClient.getMockCorridorMetrics()
    );
  },

  /**
   * Fetches the health summary of the IoT sensor network.
   * @returns A promise that resolves to the IoTHealthSummary object.
   */
  getIoTHealthSummary(): Promise<IoTHealthSummary> {
    return withMetricsFallback(
      () => realFetchIoTHealthSummary(),
      () => mockApiClient.getMockIoTHealthSummary()
    );
  },
};
