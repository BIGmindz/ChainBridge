/**
 * useAgentHealth Hook
 *
 * Fetches the backend agent health summary with cache + SWR semantics.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type { AgentHealthSummary } from "../core/types/agents";

export interface UseAgentHealthResult {
  data: AgentHealthSummary | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useAgentHealth(): UseAgentHealthResult {
  const [data, setData] = useState<AgentHealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const mountedRef = useRef(true);
  const queryKey = QUERY_KEYS.agentHealth();
  const cacheKey = getCacheKey(queryKey);

  const fetchAgentHealth = useCallback(
    async (skipCache = false): Promise<void> => {
      try {
        if (!skipCache) {
          const cached = cacheStore.get<AgentHealthSummary>(cacheKey);
          if (cached) {
            setData(cached);
            setLoading(false);

            if (cacheStore.isStale(cacheKey)) {
              fetchAgentHealth(true).catch(() => undefined);
            }
            return;
          }
        }

        setLoading(true);
        const summary = await ChainboardAPI.getAgentHealthSummary();
        cacheStore.set(cacheKey, summary, {
          staleTime: 15 * 1000,
          cacheTime: 2 * 60 * 1000,
        });

        if (mountedRef.current) {
          setData(summary);
          setError(null);
        }
      } catch (err) {
        const normalized = err instanceof Error ? err : new Error(String(err));
        if (mountedRef.current) {
          setError(normalized);
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [cacheKey],
  );

  useEffect(() => {
    mountedRef.current = true;
    fetchAgentHealth().catch(() => undefined);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchAgentHealth]);

  return {
    data,
    loading,
    error,
    refetch: () => fetchAgentHealth(true),
  };
}
