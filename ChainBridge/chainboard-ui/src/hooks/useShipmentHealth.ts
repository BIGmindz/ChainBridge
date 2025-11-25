import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { fetchShipmentHealth } from "../services/apiClient";
import type { ShipmentHealthResponse } from "../types/chainbridge";

export function useShipmentHealth(shipmentId: string | undefined): UseQueryResult<ShipmentHealthResponse> {
  return useQuery({
    queryKey: ["shipmentHealth", shipmentId],
    enabled: Boolean(shipmentId),
    queryFn: async () => {
      if (!shipmentId) {
        throw new Error("shipmentId is required");
      }
      try {
        return await fetchShipmentHealth(shipmentId);
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error("Unable to reach ChainIQ backend.");
      }
    },
    staleTime: 30_000,
    retry: 2,
  });
}
