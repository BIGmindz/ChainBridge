/**
 * useFusion - React Query Hooks for Fusion API
 *
 * Hooks for accessing Fusion Intelligence data.
 * Supports auto-refresh and integration with Focus Modes.
 *
 * @module hooks/useFusion
 */

import { useQuery } from "@tanstack/react-query";
import {
  fetchFusionOverview,
  fetchCorridorStress,
  type FusionOverviewResponse,
  type CorridorStressResponse,
} from "../api/fusionApi";

// =============================================================================
// QUERY KEYS
// =============================================================================

export const fusionQueryKeys = {
  all: ["fusion"] as const,
  overview: () => [...fusionQueryKeys.all, "overview"] as const,
  stress: () => [...fusionQueryKeys.all, "stress"] as const,
};

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Fetch Fusion Overview.
 * Refreshes frequently (e.g., 15s) as this is the central intelligence hub.
 */
export function useFusionOverview(refreshInterval = 15000) {
  return useQuery<FusionOverviewResponse, Error>({
    queryKey: fusionQueryKeys.overview(),
    queryFn: fetchFusionOverview,
    refetchInterval: refreshInterval,
    staleTime: 5000, // Data considered fresh for 5s
  });
}

/**
 * Fetch Corridor Stress metrics.
 * Refreshes every 30s.
 */
export function useCorridorStress(refreshInterval = 30000) {
  return useQuery<CorridorStressResponse, Error>({
    queryKey: fusionQueryKeys.stress(),
    queryFn: fetchCorridorStress,
    refetchInterval: refreshInterval,
    staleTime: 10000,
  });
}
