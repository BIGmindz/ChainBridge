/**
 * useIoTHealth Hook
 *
 * M04-FRONTEND-FUSION: Real backend IoT health data hook.
 * Polls /operator/iot-health every 30s for device status.
 *
 * Returns device online/offline/stale counts for SLA widget badges.
 */

import { useQuery } from "@tanstack/react-query";

import { iotClient } from "../services/iotClient";

export function useIoTHealth() {
  return useQuery({
    queryKey: ["iotHealthSummary"],
    queryFn: () => iotClient.getHealthSummary(),
    refetchInterval: 30_000, // Poll every 30s (same as SLA)
    staleTime: 25_000, // Consider stale after 25s
    retry: 2,
    retryDelay: 2000,
  });
}
