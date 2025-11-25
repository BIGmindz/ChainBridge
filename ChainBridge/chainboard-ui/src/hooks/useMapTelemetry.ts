import { useQuery } from '@tanstack/react-query';

import { fetchGlobalMapState, fetchVesselTelemetry } from '@/services/telemetryApi';

/**
 * Hook for complete global map state
 * Use for initial load - contains all layers
 * 30s cache, 60s refetch
 */
export function useGlobalMapState() {
  return useQuery({
    queryKey: ['global-map-state'],
    queryFn: fetchGlobalMapState,
    refetchInterval: 60000, // 1 minute
    staleTime: 30000,
    gcTime: 120000,
    retry: 2,
  });
}

/**
 * Hook for vessel telemetry only
 * Use for high-frequency updates (ships move fast)
 * 3s cache, 5s refetch for near-real-time
 */
export function useVesselTelemetry() {
  return useQuery({
    queryKey: ['vessel-telemetry'],
    queryFn: fetchVesselTelemetry,
    refetchInterval: 5000, // 5 seconds for smooth animation
    staleTime: 3000,
    gcTime: 10000,
    retry: 1,
  });
}
