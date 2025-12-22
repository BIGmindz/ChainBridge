/**
 * useSLA - Real-time SLA monitoring hook
 *
 * Polls /sla/operator endpoint for operational health metrics.
 * Returns queue depth, p95 latency, ready/blocked counts, heartbeat age.
 */

import { useQuery } from "@tanstack/react-query";

export interface SLAStatus {
  queue_depth: number;
  p95_processing_time_seconds: number;
  ready_count: number;
  blocked_count: number;
  heartbeat_age_seconds: number;
  status: "healthy" | "degraded" | "critical";
}

/**
 * Fetch SLA status from backend.
 */
async function fetchSLAStatus(): Promise<SLAStatus> {
  const response = await fetch("/sla/operator");

  if (!response.ok) {
    throw new Error(`SLA fetch failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Hook to fetch and poll SLA metrics.
 */
export function useSLA() {
  return useQuery<SLAStatus, Error>({
    queryKey: ["slaStatus"],
    queryFn: fetchSLAStatus,
    refetchInterval: 30_000, // Poll every 30s
    staleTime: 25_000,
    retry: 2,
    retryDelay: 2000,
  });
}
