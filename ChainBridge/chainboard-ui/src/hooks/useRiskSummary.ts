/**
 * useRiskSummary Hook
 *
 * Production-grade ChainIQ Risk Intelligence data hook.
 * Implements stale-while-revalidate pattern with unified cache layer.
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type { RiskOverviewEnvelope } from "../core/types/iq";

export interface UseRiskSummaryResult {
  data: RiskOverviewEnvelope | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useRiskSummary(): UseRiskSummaryResult {
  const [data, setData] = useState<RiskOverviewEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Prevent double-fetch in React StrictMode
  const mountedRef = useRef(true);

  // Stable query key
  const queryKey = QUERY_KEYS.riskOverview();
  const cacheKey = getCacheKey(queryKey);

  const fetchRiskSummary = useCallback(async (skipCache = false): Promise<void> => {
    try {
      // Check cache first unless explicitly skipping
      if (!skipCache) {
        const cached = cacheStore.get<RiskOverviewEnvelope>(cacheKey);
        if (cached) {
          setData(cached);
          setLoading(false);

          // If stale, trigger background refresh
          if (cacheStore.isStale(cacheKey)) {
            fetchRiskSummary(true).catch(console.error);
          }
          return;
        }
      }

      setLoading(true);
      const result = await ChainboardAPI.getRiskOverview();

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
      console.error("Failed to fetch risk summary:", errorObj);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [cacheKey]);

  useEffect(() => {
    mountedRef.current = true;
    fetchRiskSummary().catch(console.error);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchRiskSummary]);

  return {
    data,
    loading,
    error,
    refetch: () => fetchRiskSummary(true),
  };
}
