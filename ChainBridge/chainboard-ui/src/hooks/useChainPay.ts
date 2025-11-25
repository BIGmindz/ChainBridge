import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { fetchChainPayPlan } from "../services/apiClient";
import type { ChainPayPlan } from "../types/chainbridge";

export function useChainPayPlan(shipmentId: string): UseQueryResult<ChainPayPlan> {
  return useQuery({
    queryKey: ["chainpay", shipmentId],
    queryFn: async () => {
      try {
        return await fetchChainPayPlan(shipmentId);
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error("Unable to reach ChainPay backend.");
      }
    },
    enabled: Boolean(shipmentId),
    staleTime: 60_000,
    retry: 2,
  });
}
