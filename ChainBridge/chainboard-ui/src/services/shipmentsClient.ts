/**
 * Shipments & Exceptions Client
 *
 * This module provides a centralized, strongly-typed client for fetching
 * shipment and exception data. It follows the same facade pattern as
 * metricsClient, switching between the real API and mock data based on the
 * VITE_API_BASE_URL environment variable.
 *
 * This abstraction is critical for decoupling UI components from the data
 * source, enabling parallel development and robust testing.
 */

import { config } from "../config/env";
import {
  toCanonicalShipment,
  toCanonicalShipments,
  filterShipments,
  filterExceptionsBySeverity,
  type ShipmentsFilter,
  type ExceptionsFilter,
} from "../lib/shipments";
import type { Shipment, ExceptionRow } from "../lib/types";

import { mockApiClient } from "./api";
import {
  fetchShipments as realFetchShipments,
  fetchShipmentById as realFetchShipmentById,
  fetchExceptions as realFetchExceptions,
} from "./realApiClient";

const HAS_REAL_API = Boolean(config.apiBaseUrl);
const USE_REAL_API = !config.useMocks && HAS_REAL_API;

if (import.meta.env.DEV) {
  console.log(
    `[shipmentsClient] Using ${
      USE_REAL_API ? "real" : "mock"
    } API for shipments and exceptions.`
  );
}

export type { ShipmentsFilter, ExceptionsFilter } from "../lib/shipments";

export interface ShipmentsResult {
  shipments: Shipment[];
  total: number;
  filtered: number;
}

export const shipmentsClient = {
  /**
   * Fetches a list of shipments, with optional filtering.
   * @param filters - The filter criteria to apply.
   * @returns A promise that resolves to an array of Shipments.
   */
  async listShipments(filters?: ShipmentsFilter): Promise<ShipmentsResult> {
    if (USE_REAL_API) {
      try {
        if (config.isDevelopment) {
          console.log("[shipmentsClient] Fetching from real API with filters:", filters);
        }

        const envelope = await realFetchShipments(filters ?? {});

        if (config.isDevelopment) {
          console.log(`[shipmentsClient] Received ${envelope.shipments.length} shipments from backend`);
        }

        // Backend already filtered; trust the envelope
        return {
          shipments: envelope.shipments,
          total: envelope.total ?? envelope.shipments.length,
          filtered: envelope.shipments.length,
        };
      } catch (error) {
        if (config.isDevelopment) {
          console.warn("[shipmentsClient] Falling back to mock shipments:", error);
        }
      }
    }

    // Mock path: apply client-side filtering
    const legacy = await mockApiClient.getShipments();
    const canonical = toCanonicalShipments(legacy);
    const filteredShipments = filterShipments(canonical, filters);
    return {
      shipments: filteredShipments,
      total: canonical.length,
      filtered: filteredShipments.length,
    };
  },

  /**
   * Fetches a single shipment by its unique ID.
   * @param id - The ID of the shipment to retrieve.
   * @returns A promise that resolves to the Shipment, or null if not found.
   */
  async getShipmentById(id: string): Promise<Shipment> {
    if (USE_REAL_API) {
      try {
        return await realFetchShipmentById(id);
      } catch (error) {
        if (config.isDevelopment) {
          console.warn(
            `[shipmentsClient] Falling back to mock shipment detail for ${id}:`,
            error
          );
        }
      }
    }

    const legacy = await mockApiClient.getShipmentDetail(id);
    if (!legacy) {
      throw new Error(`Shipment with ID "${id}" not found.`);
    }
    return toCanonicalShipment(legacy);
  },

  /**
   * Fetches a list of all shipments with active exceptions.
   * @param filters - The filter criteria to apply.
   * @returns A promise that resolves to an array of ExceptionRows.
   */
  async listExceptions(filters?: ExceptionsFilter): Promise<ExceptionRow[]> {
    if (USE_REAL_API) {
      try {
        const exceptions = await realFetchExceptions(filters);
        return filterExceptionsBySeverity(exceptions, filters);
      } catch (error) {
        if (config.isDevelopment) {
          console.warn("[shipmentsClient] Falling back to mock exceptions:", error);
        }
      }
    }

    const exceptions = await mockApiClient.getExceptions();
    return filterExceptionsBySeverity(exceptions, filters);
  },
};
