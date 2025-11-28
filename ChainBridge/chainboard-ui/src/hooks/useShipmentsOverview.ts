/**
 * Shipments Overview Hook (Refactored)
 *
 * Production-grade data hook with:
 * - Stale-while-revalidate caching
 * - Unified API façade
 * - Stable filter keys
 * - Predictable loading behavior
 * - No client-side re-filtering
 */

import { useState, useEffect, useCallback, useRef } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type { Shipment, ShipmentFilter, ShipmentEnvelope } from "../core/types";

interface UseShipmentsOverviewResult {
  data: Shipment[];
  total: number;
  filtered: boolean;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * Control Tower data hook for shipments overview.
 *
 * Features:
 * - Instant loading from cache (if available)
 * - Background revalidation (stale-while-revalidate)
 * - No unnecessary re-fetches
 * - Stable filter dependencies
 */
export function useShipmentsOverview(
  filters?: ShipmentFilter
): UseShipmentsOverviewResult {
  const [data, setData] = useState<Shipment[]>([]);
  const [total, setTotal] = useState(0);
  const [filtered, setFiltered] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  // Stable query key based on filter values (not object identity)
  const queryKey = QUERY_KEYS.shipments(filters);
  const cacheKey = getCacheKey(queryKey);

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log("[useShipmentsOverview] MOUNTED");
    }

    mountedRef.current = true;

    return () => {
      if (import.meta.env.DEV) {
        console.log("[useShipmentsOverview] UNMOUNTED");
      }
      mountedRef.current = false;
    };
  }, []);

  /**
   * Fetch shipments from API and update cache.
   */
  const fetchShipments = useCallback(async (): Promise<ShipmentEnvelope> => {
    if (import.meta.env.DEV) {
      console.log("[useShipmentsOverview] Fetching from API", { filters, cacheKey });
    }

    const envelope = await ChainboardAPI.listShipments(filters);

    // Update cache with fresh data
    cacheStore.set(cacheKey, envelope, {
      staleTime: 30 * 1000, // 30 seconds
      cacheTime: 5 * 60 * 1000, // 5 minutes
    });

    return envelope;
  }, [filters, cacheKey]);

  /**
   * Load data with stale-while-revalidate logic.
   */
  const loadData = useCallback(async () => {
    try {
      // Step 1: Check cache
      const cached = cacheStore.get<ShipmentEnvelope>(cacheKey);

      if (cached) {
        // Instant load from cache
        if (mountedRef.current) {
          if (import.meta.env.DEV) {
            console.log("[useShipmentsOverview] Loading from cache", cached);
          }

          setData(cached.shipments);
          setTotal(cached.total);
          setFiltered(cached.filtered);
          setError(null);
          setLoading(false);
        }

        // Step 2: Revalidate in background if stale
        if (cacheStore.isStale(cacheKey)) {
          if (import.meta.env.DEV) {
            console.log("[useShipmentsOverview] Cache is stale, revalidating in background");
          }

          const fresh = await fetchShipments();

          if (mountedRef.current) {
            setData(fresh.shipments);
            setTotal(fresh.total);
            setFiltered(fresh.filtered);
          }
        }
      } else {
        // Step 3: No cache, fetch fresh data
        if (import.meta.env.DEV) {
          console.log("[useShipmentsOverview] No cache, fetching fresh data");
        }

        setLoading(true);
        const fresh = await fetchShipments();

        if (mountedRef.current) {
          setData(fresh.shipments);
          setTotal(fresh.total);
          setFiltered(fresh.filtered);
          setError(null);
          setLoading(false);
        }
      }
    } catch (err) {
      if (!mountedRef.current) return;

      const message = err instanceof Error ? err.message : "Failed to load shipments";

      if (import.meta.env.DEV) {
        console.error("[useShipmentsOverview] Error loading shipments:", err);
      }

      setError(message);
      setLoading(false);
    }
  }, [cacheKey, fetchShipments]);

  /**
   * Manual refresh (bypasses cache).
   */
  const refresh = useCallback(async () => {
    if (import.meta.env.DEV) {
      console.log("[useShipmentsOverview] Manual refresh");
    }

    setLoading(true);
    setError(null);

    try {
      const fresh = await fetchShipments();

      if (mountedRef.current) {
        setData(fresh.shipments);
        setTotal(fresh.total);
        setFiltered(fresh.filtered);
        setError(null);
        setLoading(false);
      }
    } catch (err) {
      if (!mountedRef.current) return;

      const message = err instanceof Error ? err.message : "Failed to refresh shipments";

      if (import.meta.env.DEV) {
        console.error("[useShipmentsOverview] Error refreshing:", err);
      }

      setError(message);
      setLoading(false);
    }
  }, [fetchShipments]);

  // Load data when cache key changes
  useEffect(() => {
    loadData();
  }, [loadData]);

  return { data, total, filtered, loading, error, refresh };
}
