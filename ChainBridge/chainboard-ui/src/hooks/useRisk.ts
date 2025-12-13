/**
 * useRisk Hook
 *
 * React Query hooks for ChainIQ Risk API integration.
 * Provides loading states, error handling, and cache management for risk data.
 */

import { useQuery } from "@tanstack/react-query";

import {
  fetchShipmentRisk,
  fetchBatchShipmentRisk,
  fetchRiskHealth,
} from "../services/riskApi";
import type {
  ShipmentRiskContext,
  ShipmentRiskAssessment,
  RiskHealthResponse,
} from "../types/risk";

// =============================================================================
// QUERY KEYS
// =============================================================================

export const riskQueryKeys = {
  all: ["chainiq-risk"] as const,
  shipment: (shipmentId: string) => [...riskQueryKeys.all, "shipment", shipmentId] as const,
  shipmentWithContext: (context: ShipmentRiskContext) =>
    [...riskQueryKeys.all, "shipment", context.shipmentId, context] as const,
  batch: (shipmentIds: string[]) => [...riskQueryKeys.all, "batch", shipmentIds] as const,
  health: () => [...riskQueryKeys.all, "health"] as const,
};

// =============================================================================
// HOOKS
// =============================================================================

interface UseShipmentRiskOptions {
  enabled?: boolean;
  staleTime?: number;
  refetchOnWindowFocus?: boolean;
}

/**
 * Fetch risk assessment for a single shipment
 *
 * @param context - Shipment context for risk scoring (or undefined to disable)
 * @param options - Query options
 * @returns Query result with risk assessment data, loading state, and error
 *
 * @example
 * ```tsx
 * const { data: risk, isLoading, isError } = useShipmentRisk({
 *   shipmentId: "SHP-001",
 *   origin: "Shanghai",
 *   destination: "Los Angeles",
 *   mode: "OCEAN"
 * });
 * ```
 */
export function useShipmentRisk(
  context: ShipmentRiskContext | undefined,
  options: UseShipmentRiskOptions = {}
) {
  const {
    enabled = true,
    staleTime = 30_000, // 30 seconds
    refetchOnWindowFocus = false,
  } = options;

  return useQuery<ShipmentRiskAssessment, Error>({
    queryKey: context ? riskQueryKeys.shipmentWithContext(context) : riskQueryKeys.shipment(""),
    queryFn: async () => {
      if (!context) {
        throw new Error("ShipmentRiskContext is required");
      }
      return fetchShipmentRisk(context);
    },
    enabled: !!context && enabled,
    staleTime,
    refetchOnWindowFocus,
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
}

/**
 * Fetch risk assessments for multiple shipments in batch
 *
 * @param contexts - Array of shipment contexts
 * @param options - Query options
 * @returns Query result with array of risk assessments
 */
export function useBatchShipmentRisk(
  contexts: ShipmentRiskContext[] | undefined,
  options: UseShipmentRiskOptions = {}
) {
  const {
    enabled = true,
    staleTime = 30_000,
    refetchOnWindowFocus = false,
  } = options;

  const shipmentIds = contexts?.map((c) => c.shipmentId) ?? [];

  return useQuery<ShipmentRiskAssessment[], Error>({
    queryKey: riskQueryKeys.batch(shipmentIds),
    queryFn: async () => {
      if (!contexts || contexts.length === 0) {
        throw new Error("At least one ShipmentRiskContext is required");
      }
      return fetchBatchShipmentRisk(contexts);
    },
    enabled: !!contexts && contexts.length > 0 && enabled,
    staleTime,
    refetchOnWindowFocus,
    retry: 2,
  });
}

/**
 * Fetch ChainIQ Risk API health status
 *
 * @returns Query result with health status
 */
export function useRiskHealth() {
  return useQuery<RiskHealthResponse, Error>({
    queryKey: riskQueryKeys.health(),
    queryFn: fetchRiskHealth,
    staleTime: 60_000, // 1 minute
    refetchInterval: 60_000, // Auto-refresh every minute
    retry: 1,
  });
}
