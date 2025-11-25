// chainboard-ui/src/hooks/useAlertsFeed.ts
/**
 * Alerts Feed Hook
 *
 * SWR-powered hook for listing and filtering Control Tower alerts.
 * Implements stale-while-revalidate pattern for optimal UX.
 *
 * Auto-refetches on real-time alert events via SSE.
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
}

/**
 * Hook for fetching the global alerts feed with optional filters.
 *
 * @param filters - Optional filters (source, severity, status, limit)
 * @returns Alerts data, loading state, error, and refresh function
 *
 * @example
 * ```tsx
 * const { alerts, loading, error, refresh } = useAlertsFeed({
 *   status: "open",
 *   limit: 50,
 * });
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
      console.error("Failed to fetch alerts:", errorObj);
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

  // Subscribe to real-time alert events
  useEventStream({
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
  };
}
