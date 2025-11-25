import { useMutation, useQuery, useQueryClient, type UseMutationResult, type UseQueryResult } from "@tanstack/react-query";

import { fetchChainDocsDossier, seedDemoDocuments } from "../services/apiClient";
import type { ChainDocsDossier } from "../types/chainbridge";

export function useChainDocsDossier(shipmentId: string): UseQueryResult<ChainDocsDossier> {
  return useQuery({
    queryKey: ["chaindocs", shipmentId],
    queryFn: async () => {
      try {
        return await fetchChainDocsDossier(shipmentId);
      } catch (error) {
        if (error instanceof Error) {
          throw error;
        }
        throw new Error("Unable to reach ChainDocs backend.");
      }
    },
    enabled: Boolean(shipmentId),
    staleTime: 60_000,
    retry: 2,
  });
}

export function useSeedDemoDocuments(shipmentId: string): UseMutationResult<ChainDocsDossier, Error, void> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!shipmentId) {
        throw new Error("Shipment ID is required for seeding demo documents");
      }
      return await seedDemoDocuments(shipmentId);
    },
    onSuccess: () => {
      // Refetch the dossier so UI updates immediately
      queryClient.invalidateQueries({ queryKey: ['chaindocs', shipmentId] });
    },
  });
}
