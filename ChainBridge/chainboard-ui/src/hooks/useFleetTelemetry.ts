import { useQuery } from '@tanstack/react-query';

import { fetchFleetTelemetry } from '@/services/intelClient';

/**
 * Real-time fleet telemetry hook for 3D map visualization
 *
 * Polls every 2 seconds for live ship positions, headings, velocities
 * Used by GlobalOpsMap IconLayer for smooth real-time updates
 *
 * Cache: 5s stale, 2s refetch interval
 * Performance: 60fps target, throttle layer updates
 */
export function useFleetTelemetry() {
  return useQuery({
    queryKey: ['fleet-telemetry'],
    queryFn: fetchFleetTelemetry,
    refetchInterval: 2000, // 2s for real-time map updates
    staleTime: 5000,
    gcTime: 10000,
    retry: 1,
    retryDelay: 1000,
  });
}
