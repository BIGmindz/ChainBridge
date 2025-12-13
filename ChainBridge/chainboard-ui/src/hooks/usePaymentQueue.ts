/**
 * usePaymentQueue Hook
 *
 * Production-grade ChainPay payment queue data hook.
 * Implements stale-while-revalidate pattern with unified cache layer.
 *
 * Auto-refetches on real-time payment state change events via SSE.
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type { PaymentQueueEnvelope } from "../core/types/payments";

import { useEventStream } from "./useEventStream";

export interface UsePaymentQueueResult {
  data: PaymentQueueEnvelope | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function usePaymentQueue(limit: number = 20): UsePaymentQueueResult {
  const [data, setData] = useState<PaymentQueueEnvelope | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Prevent double-fetch in React StrictMode
  const mountedRef = useRef(true);

  // Stable query key with limit
  const queryKey = QUERY_KEYS.paymentQueue(limit);
  const cacheKey = getCacheKey(queryKey);

  const fetchPaymentQueue = useCallback(async (skipCache = false): Promise<void> => {
    try {
      // Check cache first unless explicitly skipping
      if (!skipCache) {
        const cached = cacheStore.get<PaymentQueueEnvelope>(cacheKey);
        if (cached) {
          setData(cached);
          setLoading(false);

          // If stale, trigger background refresh
          if (cacheStore.isStale(cacheKey)) {
            fetchPaymentQueue(true).catch(console.error);
          }
          return;
        }
      }

      setLoading(true);
      const result = await ChainboardAPI.getPaymentQueue(limit);

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
      console.error("Failed to fetch payment queue:", errorObj);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [cacheKey, limit]);

  useEffect(() => {
    mountedRef.current = true;
    fetchPaymentQueue().catch(console.error);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchPaymentQueue]);

  // Subscribe to real-time payment events
  useEventStream({
    filter: {
      types: ["payment_state_changed"],
      sources: ["payments"],
    },
    onEvent: () => {
      // Refetch when any payment milestone changes state
      fetchPaymentQueue(true).catch(console.error);
    },
  });

  return {
    data,
    loading,
    error,
    refetch: () => fetchPaymentQueue(true),
  };
}
