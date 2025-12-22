/**
 * useAlertWorkQueue Hook
 *
 * SWR-based hook for fetching and managing the alert work queue.
 * Provides filtered views of alerts with triage context (owner, notes, actions).
 *
 * Auto-refetches on real-time alert events via SSE.
 */

import { useRef, useState, useEffect, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, serializeKey } from "../core/cache/queryKeys";
import { cacheStore } from "../core/cache/store";
import type { AlertWorkQueueResponse, AlertStatus, AlertSource, AlertSeverity } from "../core/types/alerts";

import { useEventStream } from "./useEventStream";


interface UseAlertWorkQueueParams {
  ownerId?: string;
  status?: AlertStatus;
  source?: AlertSource;
  severity?: AlertSeverity;
  limit?: number;
}

interface UseAlertWorkQueueResult {
  data: AlertWorkQueueResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

const STALE_TIME = 10000; // 10 seconds
const ERROR_RETRY_DELAY = 3000; // 3 seconds

export function useAlertWorkQueue(
  params?: UseAlertWorkQueueParams,
  options?: { enabled?: boolean; skipCache?: boolean }
): UseAlertWorkQueueResult {
  const { enabled = true, skipCache = false } = options ?? {};

  const [data, setData] = useState<AlertWorkQueueResponse | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const mountedRef = useRef(true);
  const lastFetchRef = useRef(0);

  const cacheKeyStr = serializeKey(QUERY_KEYS.alertWorkQueue(params));

  const fetchData = useCallback(async (force = false) => {
    if (!enabled) return;

    const now = Date.now();

    // Prevent double-fetch on mount
    if (!force && now - lastFetchRef.current < 100) {
      return;
    }

    // Check cache first (if not forcing and not skipping cache)
    if (!force && !skipCache) {
      const cached = cacheStore.get<AlertWorkQueueResponse>(cacheKeyStr);
      if (cached) {
        setData(cached);
        setLoading(false);

        // Background refresh if stale
        if (now - lastFetchRef.current > STALE_TIME) {
          // Continue to fetch in background
        } else {
          return;
        }
      }
    }

    lastFetchRef.current = now;
    setLoading(true);
    setError(null);

    try {
      const result = await ChainboardAPI.getAlertWorkQueue({
        ownerId: params?.ownerId,
        status: params?.status,
        source: params?.source,
        severity: params?.severity,
        limit: params?.limit,
      });

      if (!mountedRef.current) return;

      setData(result);
      setError(null);
      cacheStore.set(cacheKeyStr, result);
    } catch (err) {
      if (!mountedRef.current) return;

      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      console.error("Failed to fetch alert work queue:", error);

      // Retry on error after delay
      setTimeout(() => {
        if (mountedRef.current && enabled) {
          fetchData(true);
        }
      }, ERROR_RETRY_DELAY);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled, skipCache, cacheKeyStr, params?.ownerId, params?.status, params?.source, params?.severity, params?.limit]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();

    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  // Subscribe to real-time alert events
  useEventStream({
    enabled,
    filter: {
      types: ["alert_updated", "alert_status_changed", "alert_note_added"],
      sources: ["alerts"],
    },
    onEvent: () => {
      // Refetch when any alert event occurs
      fetchData(true);
    },
  });

  return {
    data,
    loading,
    error,
    refetch: () => fetchData(true),
  };
}
