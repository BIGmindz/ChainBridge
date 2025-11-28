// chainboard-ui/src/hooks/useShipmentAlerts.ts
/**
 * Shipment Alerts Hook
 *
 * Hook for fetching alerts specific to a single shipment.
 * Filters the global alerts feed by shipment reference.
 */

import { useMemo } from "react";

import type { ControlTowerAlert } from "../core/types/alerts";

import { useAlertsFeed } from "./useAlertsFeed";

export interface UseShipmentAlertsResult {
  alertsForShipment: ControlTowerAlert[] | undefined;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

/**
 * Hook for fetching alerts for a specific shipment.
 *
 * @param shipmentReference - Shipment reference ID (e.g., "SHP-2025-027")
 * @returns Filtered alerts for the shipment, loading state, error, and refresh function
 *
 * @example
 * ```tsx
 * const { alertsForShipment, loading } = useShipmentAlerts("SHP-2025-027");
 * ```
 */
export function useShipmentAlerts(
  shipmentReference: string | undefined
): UseShipmentAlertsResult {
  // Fetch all alerts (limit to recent 100 to avoid over-fetching)
  const { alerts, loading, error, refresh } = useAlertsFeed({ limit: 100 });

  // Filter alerts for this shipment
  const alertsForShipment = useMemo(() => {
    if (!shipmentReference || !alerts) {
      return undefined;
    }

    return alerts.filter(
      (alert) => alert.shipment_reference === shipmentReference
    );
  }, [alerts, shipmentReference]);

  return {
    alertsForShipment,
    loading,
    error,
    refresh,
  };
}
