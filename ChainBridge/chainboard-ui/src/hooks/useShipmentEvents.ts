/**
 * useShipmentEvents - Hook for fetching shipment events from debug endpoint
 * Handles loading, error states, and automatic sorting by occurredAt
 */

import { useQuery, UseQueryResult } from "@tanstack/react-query";

import { fetchShipmentEvents } from "../services/apiClient";
import type { ShipmentEvent } from "../types/chainbridge";

export function useShipmentEvents(
  shipmentId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
): UseQueryResult<ShipmentEvent[], Error> {
  return useQuery<ShipmentEvent[], Error>({
    queryKey: ["shipmentEvents", shipmentId],
    queryFn: () => fetchShipmentEvents(shipmentId),
    enabled: Boolean(shipmentId) && (options?.enabled !== false),
    staleTime: 10_000, // 10 seconds
    retry: 2,
    refetchInterval: options?.refetchInterval ?? 30_000, // 30 seconds default
    select: (data) => {
      // Sort events by occurredAt descending (newest first)
      return [...data].sort((a, b) =>
        new Date(b.occurredAt).getTime() - new Date(a.occurredAt).getTime()
      );
    },
  });
}
