// chainboard-ui/src/hooks/useAlertsFeed.ts
/**
 * Alerts Feed Hook
 *
 * Fetches alerts from /api/chainboard/alerts (real backend).
 * Auto-refetches on real-time SSE alert events.
 * Exposes connection status for "Live" indicator.
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type {
  AlertsEnvelope,
  AlertSource,
  AlertSeverity,
  AlertStatus,
} from "../core/types/alerts";

import { useEventStream } from "./useEventStream";

export interface AlertsFilters {
  source?: AlertSource;
  severity?: AlertSeverity;
  status?: AlertStatus;
  limit?: number;
}

export interface UseAlertsFeedResult {
  alerts: AlertsEnvelope["alerts"] | undefined;
  total: number;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  /** True when SSE stream is connected (real-time updates active) */
  isLive: boolean;
}

/**
 * Hook for fetching the global alerts feed with optional filters.
 * Connects to real backend - no mock fallback.
 *
 * @param filters - Optional filters (source, severity, status, limit)
 * @returns Alerts data, loading state, error, refresh function, and live status
 *
 * @example
 * ```tsx
 * const { alerts, loading, error, refresh, isLive } = useAlertsFeed({
 *   status: "open",
 *   limit: 50,
 * });
 *
 * return (
 *   <>
 *     {isLive && <span className="text-green-400">● Live</span>}
 *     {alerts?.map(a => <AlertCard key={a.id} alert={a} />)}
 *   </>
 * );
 * ```
 */
export function useAlertsFeed(filters?: AlertsFilters): UseAlertsFeedResult {
  const [data, setData] = useState<AlertsEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Prevent double-fetch in React StrictMode
  const mountedRef = useRef(true);

  // Stable query key with filters
  const queryKey = QUERY_KEYS.alerts(filters);
  const cacheKey = getCacheKey(queryKey);

  const fetchAlerts = useCallback(async (skipCache = false): Promise<void> => {
    try {
      // Check cache first unless explicitly skipping
      if (!skipCache) {
        const cached = cacheStore.get<AlertsEnvelope>(cacheKey);
        if (cached) {
          setData(cached);
          setLoading(false);

          // If stale, trigger background refresh
          if (cacheStore.isStale(cacheKey)) {
            fetchAlerts(true).catch(console.error);
          }
          return;
        }
      }

      setLoading(true);
      const result = await ChainboardAPI.listAlerts(filters);

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
      console.error("[useAlertsFeed] Failed to fetch alerts:", errorObj);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [cacheKey, filters]);

  useEffect(() => {
    mountedRef.current = true;
    fetchAlerts().catch(console.error);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchAlerts]);

  // Subscribe to real-time alert events and get connection status
  const { isConnected } = useEventStream({
    filter: {
      types: ["alert_created", "alert_updated", "alert_status_changed"],
      sources: ["alerts"],
    },
    onEvent: () => {
      // Refetch when any alert event occurs
      fetchAlerts(true).catch(console.error);
    },
  });

  const refresh = useCallback(async () => {
    await fetchAlerts(true);
  }, [fetchAlerts]);

  return {
    alerts: data?.alerts,
    total: data?.total ?? 0,
    loading,
    error,
    refresh,
    isLive: isConnected,
  };
}
