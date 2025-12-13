import { useQuery, UseQueryResult } from "@tanstack/react-query";

import { fetchAtRiskShipments } from "../services/apiClient";
import type { AtRiskShipmentSummary } from "../types/chainbridge";

export interface AtRiskFilters {
  minRiskScore: number;
  maxResults: number;
  offset: number;
  corridorCode?: string;
  mode?: string;
  incoterm?: string;
  riskLevel?: string;
}

export function useAtRiskShipments(filters: AtRiskFilters): UseQueryResult<AtRiskShipmentSummary[], Error> {
  return useQuery<AtRiskShipmentSummary[], Error>({
    queryKey: ["atRiskShipments", filters],
    queryFn: () => fetchAtRiskShipments({
      min_riskScore: filters.minRiskScore,
      max_results: filters.maxResults,
      offset: filters.offset,
      corridor_code: filters.corridorCode,
      mode: filters.mode,
      incoterm: filters.incoterm,
      risk_level: filters.riskLevel,
    }),
    staleTime: 30_000, // 30 seconds
    retry: 2,
    refetchInterval: 15_000, // Auto-poll every 15 seconds for live status updates
  });
}
