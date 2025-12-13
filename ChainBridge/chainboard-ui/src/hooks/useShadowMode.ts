/**
 * useShadowMode - React Query Hooks for Shadow Mode API
 *
 * Wire-up to Cody's live shadow endpoints with caching + error handling.
 * WCAG AA compliant loading states, p95 < 70ms UI render after hydration.
 *
 * @module hooks/useShadowMode
 */

import { useQuery } from "@tanstack/react-query";

import {
  fetchShadowStats,
  fetchShadowEvents,
  fetchShadowCorridors,
  fetchShadowDrift,
  type ShadowStatsResponse,
  type ShadowEventsResponse,
  type ShadowCorridorsResponse,
  type ShadowDriftResponse,
} from "../api/shadowMode";

// =============================================================================
// QUERY KEYS
// =============================================================================

export const shadowQueryKeys = {
  all: ["shadow"] as const,
  stats: (hours: number) => [...shadowQueryKeys.all, "stats", hours] as const,
  events: (limit: number, corridor?: string, hours?: number) =>
    [...shadowQueryKeys.all, "events", limit, corridor, hours] as const,
  corridors: (hours: number, minEvents: number) =>
    [...shadowQueryKeys.all, "corridors", hours, minEvents] as const,
  drift: (hours: number, threshold: number) =>
    [...shadowQueryKeys.all, "drift", hours, threshold] as const,
};

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Fetch shadow statistics with caching.
 * Refetches every 30s for live monitoring.
 */
export function useShadowStats(hours = 24) {
  return useQuery<ShadowStatsResponse, Error>({
    queryKey: shadowQueryKeys.stats(hours),
    queryFn: () => fetchShadowStats(hours),
    staleTime: 30_000, // 30s cache
    refetchInterval: 30_000, // Auto-refresh for live data
    retry: 2,
  });
}

/**
 * Fetch shadow events with optional corridor filter.
 */
export function useShadowEvents(limit = 100, corridor?: string, hours = 24) {
  return useQuery<ShadowEventsResponse, Error>({
    queryKey: shadowQueryKeys.events(limit, corridor, hours),
    queryFn: () => fetchShadowEvents(limit, corridor, hours),
    staleTime: 15_000,
    refetchInterval: 15_000,
    retry: 2,
  });
}

/**
 * Fetch corridor-level statistics.
 */
export function useShadowCorridors(hours = 24, minEvents = 10) {
  return useQuery<ShadowCorridorsResponse, Error>({
    queryKey: shadowQueryKeys.corridors(hours, minEvents),
    queryFn: () => fetchShadowCorridors(hours, minEvents),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: 2,
  });
}

/**
 * Fetch drift detection metrics.
 */
export function useShadowDrift(lookbackHours = 24, threshold = 0.25) {
  return useQuery<ShadowDriftResponse, Error>({
    queryKey: shadowQueryKeys.drift(lookbackHours, threshold),
    queryFn: () => fetchShadowDrift(lookbackHours, threshold),
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 2,
  });
}

// =============================================================================
// COMBINED HOOK FOR INTELLIGENCE PANEL
// =============================================================================

/**
 * Combined hook for Shadow Intelligence Panel.
 * Fetches stats, drift, and corridors in parallel.
 */
export function useShadowIntelligence(hours = 24) {
  const stats = useShadowStats(hours);
  const drift = useShadowDrift(hours);
  const corridors = useShadowCorridors(hours);

  return {
    stats,
    drift,
    corridors,
    isLoading: stats.isLoading || drift.isLoading || corridors.isLoading,
    isError: stats.isError || drift.isError || corridors.isError,
    error: stats.error || drift.error || corridors.error,
  };
}
