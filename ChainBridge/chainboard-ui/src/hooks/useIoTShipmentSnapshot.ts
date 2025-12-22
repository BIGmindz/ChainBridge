/**
 * useIoTShipmentSnapshot Hook (Renamed to useShipmentIoT for consistency)
 *
 * Fetches IoT telemetry snapshot for a specific shipment.
 * Implements stale-while-revalidate pattern with unified cache layer.
 */

import { useState, useEffect, useRef, useCallback } from "react";

import { ChainboardAPI } from "../core/api/client";
import { QUERY_KEYS, cacheStore, getCacheKey } from "../core/cache";
import type { ShipmentIoTSnapshot } from "../core/types/iot";

export interface UseShipmentIoTOptions {
  enabled?: boolean;
}

export interface UseShipmentIoTResult {
  snapshot: ShipmentIoTSnapshot | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch IoT snapshot for a specific shipment.
 * Returns null if no IoT data exists for the shipment.
 */
export function useShipmentIoT(
  shipmentId: string | null,
  options: UseShipmentIoTOptions = {}
): UseShipmentIoTResult {
  const { enabled = true } = options;
  const [snapshot, setSnapshot] = useState<ShipmentIoTSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Prevent double-fetch in React StrictMode
  const mountedRef = useRef(true);

  // Stable query key (only if shipmentId exists)
  const queryKey = shipmentId ? QUERY_KEYS.iot(shipmentId) : null;
  const cacheKey = queryKey ? getCacheKey(queryKey) : null;

  const fetchSnapshot = useCallback(async (skipCache = false): Promise<void> => {
    if (!shipmentId || !enabled) {
      setSnapshot(null);
      setLoading(false);
      setError(null);
      return;
    }

    try {
      // Check cache first unless explicitly skipping
      if (!skipCache && cacheKey) {
        const cached = cacheStore.get<ShipmentIoTSnapshot>(cacheKey);
        if (cached) {
          setSnapshot(cached);
          setLoading(false);

          // If stale, trigger background refresh
          if (cacheStore.isStale(cacheKey)) {
            fetchSnapshot(true).catch(console.error);
          }
          return;
        }
      }

      setLoading(true);
      const result = await ChainboardAPI.getIoTSnapshot(shipmentId);

      // Cache the result if not null
      if (result && cacheKey) {
        cacheStore.set(cacheKey, result);
      }

      if (mountedRef.current) {
        setSnapshot(result);
        setError(null);
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err));
      if (mountedRef.current) {
        setError(errorObj);
      }
      console.error(`Failed to fetch IoT snapshot for ${shipmentId}:`, errorObj);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [shipmentId, enabled, cacheKey]);

  useEffect(() => {
    mountedRef.current = true;
    fetchSnapshot().catch(console.error);

    return () => {
      mountedRef.current = false;
    };
  }, [fetchSnapshot]);

  return {
    snapshot,
    loading,
    error,
    refetch: () => fetchSnapshot(true),
  };
}

// Legacy export for backward compatibility
export const useIoTShipmentSnapshot = useShipmentIoT;
