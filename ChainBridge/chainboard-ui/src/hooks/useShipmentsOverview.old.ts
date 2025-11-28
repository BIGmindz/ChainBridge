import { useCallback, useEffect, useRef, useState } from "react";

import type { ShipmentsFilter } from "../lib/shipments";
import type { Shipment } from "../lib/types";
import { shipmentsClient } from "../services/shipmentsClient";

interface UseShipmentsOverviewResult {
  data: Shipment[];
  total: number;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useShipmentsOverview(filters?: ShipmentsFilter): UseShipmentsOverviewResult {
  const [data, setData] = useState<Shipment[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  // Stabilize filters to prevent infinite effect loops
  const filtersKey = JSON.stringify(filters ?? {});

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log("[useShipmentsOverview] MOUNTED");
    }

    // Reset mounted flag on mount (critical for StrictMode)
    mountedRef.current = true;

    return () => {
      if (import.meta.env.DEV) {
        console.log("[useShipmentsOverview] UNMOUNTED");
      }
      mountedRef.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    if (import.meta.env.DEV) {
      console.log("[useShipmentsOverview] Starting fetch with filters:", filters);
    }

    setLoading(true);
    setError(null);
    try {
      const result = await shipmentsClient.listShipments(filters);
      if (!mountedRef.current) {
        if (import.meta.env.DEV) {
          console.log("[useShipmentsOverview] Component unmounted, ignoring result");
        }
        return;
      }

      if (import.meta.env.DEV) {
        console.log(`[useShipmentsOverview] Successfully loaded ${result.shipments.length} shipments`);
      }

      setData(result.shipments);
      setTotal(result.total);
    } catch (err) {
      if (!mountedRef.current) {
        if (import.meta.env.DEV) {
          console.log("[useShipmentsOverview] Component unmounted, ignoring error");
        }
        return;
      }
      const message = err instanceof Error ? err.message : "Failed to load shipments";

      if (import.meta.env.DEV) {
        console.error("[useShipmentsOverview] Error loading shipments:", message, err);
      }

      setError(message);
    } finally {
      if (mountedRef.current) {
        if (import.meta.env.DEV) {
          console.log("[useShipmentsOverview] Fetch complete, setting loading=false");
        }
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey]); // Depend on filtersKey instead of filters object

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, total, loading, error, refresh };
}
