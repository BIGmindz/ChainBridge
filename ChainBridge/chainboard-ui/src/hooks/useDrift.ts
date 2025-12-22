/**
 * useDrift - React Query Hooks for Drift API
 *
 * Wire-up to Maggie+Cody drift endpoints with caching + error handling.
 * WCAG AA compliant loading states.
 *
 * @module hooks/useDrift
 */

import { useQuery } from "@tanstack/react-query";

import {
  fetchDriftScore,
  fetchDriftFeatures,
  fetchDriftCorridors,
  fetchDriftHistory,
  type DriftScoreResponse,
  type DriftFeaturesResponse,
  type DriftCorridorsResponse,
  type DriftHistoryResponse,
} from "../api/driftApi";

// =============================================================================
// QUERY KEYS
// =============================================================================

export const driftQueryKeys = {
  all: ["drift"] as const,
  score: (hours: number, threshold: number) =>
    [...driftQueryKeys.all, "score", hours, threshold] as const,
  features: (hours: number, topN: number) =>
    [...driftQueryKeys.all, "features", hours, topN] as const,
  corridors: (hours: number, minEvents: number) =>
    [...driftQueryKeys.all, "corridors", hours, minEvents] as const,
  history: (hours: number, interval: number) =>
    [...driftQueryKeys.all, "history", hours, interval] as const,
};

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Fetch drift score with caching.
 * Auto-refresh every 30s for live monitoring.
 */
export function useDriftScore(lookbackHours = 24, threshold = 0.25) {
  return useQuery<DriftScoreResponse, Error>({
    queryKey: driftQueryKeys.score(lookbackHours, threshold),
    queryFn: () => fetchDriftScore(lookbackHours, threshold),
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 2,
  });
}

/**
 * Fetch drifting features.
 * Auto-refresh every 60s.
 */
export function useDriftFeatures(lookbackHours = 24, topN = 10) {
  return useQuery<DriftFeaturesResponse, Error>({
    queryKey: driftQueryKeys.features(lookbackHours, topN),
    queryFn: () => fetchDriftFeatures(lookbackHours, topN),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: 2,
  });
}

/**
 * Fetch corridor-level drift.
 * Auto-refresh every 30s.
 */
export function useDriftCorridors(lookbackHours = 24, minEvents = 10) {
  return useQuery<DriftCorridorsResponse, Error>({
    queryKey: driftQueryKeys.corridors(lookbackHours, minEvents),
    queryFn: () => fetchDriftCorridors(lookbackHours, minEvents),
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 2,
  });
}

/**
 * Fetch drift history for sparkline.
 * Auto-refresh every 60s.
 */
export function useDriftHistory(lookbackHours = 24, intervalMinutes = 15) {
  return useQuery<DriftHistoryResponse, Error>({
    queryKey: driftQueryKeys.history(lookbackHours, intervalMinutes),
    queryFn: () => fetchDriftHistory(lookbackHours, intervalMinutes),
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: 2,
  });
}

// =============================================================================
// COMBINED HOOK
// =============================================================================

/**
 * Combined hook for full drift intelligence.
 * Fetches score, features, corridors, and history in parallel.
 */
export function useDriftIntelligence(lookbackHours = 24) {
  const score = useDriftScore(lookbackHours);
  const features = useDriftFeatures(lookbackHours, 5); // Top 5 for panel
  const corridors = useDriftCorridors(lookbackHours);
  const history = useDriftHistory(lookbackHours, 15);

  return {
    score,
    features,
    corridors,
    history,
    isLoading: score.isLoading || features.isLoading || corridors.isLoading || history.isLoading,
    isError: score.isError || features.isError || corridors.isError || history.isError,
    error: score.error || features.error || corridors.error || history.error,
    refetchAll: () => {
      score.refetch();
      features.refetch();
      corridors.refetch();
      history.refetch();
    },
  };
}

// =============================================================================
// DERIVED DATA HOOKS
// =============================================================================

/**
 * Get sparkline data from drift history.
 */
export function useDriftSparklineData(lookbackHours = 24) {
  const { data, isLoading, error } = useDriftHistory(lookbackHours);

  const sparklineData = data?.history.map((point) => ({
    timestamp: point.timestamp,
    score: point.p95_delta,
  })) ?? [];

  return { data: sparklineData, isLoading, error };
}

/**
 * Get top drifting features.
 */
export function useTopDriftingFeatures(topN = 3) {
  const { data, isLoading, error } = useDriftFeatures(24, topN);

  return {
    features: data?.top_drifting ?? [],
    totalDrifting: data?.drifting_count ?? 0,
    isLoading,
    error,
  };
}

/**
 * Get corridor status for animations.
 */
export function useCorridorDriftStatus() {
  const { data, isLoading, error } = useDriftCorridors(24);

  const corridorStatuses = data?.corridors.map((c) => ({
    corridor: c.corridor,
    eventCount: c.event_count,
    driftScore: c.drift_score,
    driftFlag: c.is_drifting,
    healthScore: c.health_score,
    lastUpdated: c.last_updated,
  })) ?? [];

  return {
    corridors: corridorStatuses,
    driftingCount: data?.drifting_count ?? 0,
    healthyCount: data?.healthy_count ?? 0,
    isLoading,
    error,
  };
}
