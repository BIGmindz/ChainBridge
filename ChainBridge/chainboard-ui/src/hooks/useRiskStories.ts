/**
 * useRiskStories Hook
 *
 * Manages ChainIQ risk narratives with cache + stale-while-revalidate.
 * Provides human-readable risk intelligence for shipments.
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type { RiskStoryEnvelope } from "../core/types/iq";

export interface UseRiskStoriesResult {
  data: RiskStoryEnvelope | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and cache ChainIQ risk stories.
 *
 * @param limit - Max number of stories to return (default: 20)
 * @returns Risk stories data with loading/error states
 */
export function useRiskStories(limit: number = 20): UseRiskStoriesResult {
  const [data, setData] = useState<RiskStoryEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Prevent double-fetch in React StrictMode
  const mountedRef = useRef(true);

  // Stable query key with limit
  const queryKey = QUERY_KEYS.riskStories(limit);
  const cacheKey = getCacheKey(queryKey);

  const fetchRiskStories = useCallback(async (skipCache = false): Promise<void> => {
    try {
      // Check cache first unless explicitly skipping
      if (!skipCache) {
        const cached = cacheStore.get<RiskStoryEnvelope>(cacheKey);
        if (cached) {
          setData(cached);
          setLoading(false);

          // If stale, trigger background refresh
          if (cacheStore.isStale(cacheKey)) {
            fetchRiskStories(true).catch(console.error);
          }
          return;
        }
      }

      setLoading(true);
      const result = await ChainboardAPI.getRiskStories(limit);

      // Cache the result
      cacheStore.set(cacheKey, result);

      if (mountedRef.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      if (mountedRef.current) {
        setError(errorObj);
      }

      if (import.meta.env.DEV) {
        console.error("[useRiskStories] Failed to fetch risk stories:", errorObj);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [cacheKey, limit]);

  useEffect(() => {
    mountedRef.current = true;
    fetchRiskStories().catch(console.error);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchRiskStories]);

  const refetch = useCallback(async () => {
    return fetchRiskStories(true);
  }, [fetchRiskStories]);

  return { data, loading, error, refetch };
}
