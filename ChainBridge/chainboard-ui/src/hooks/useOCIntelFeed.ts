import { useQuery } from '@tanstack/react-query';

import { fetchOCIntelFeed } from '@/services/intelClient';
import type { OCIntelFeedResponse } from '@/types/chainbridge';

/**
 * Operator Console Intel Feed Hook
 * Unified data source for OC cockpit intelligence
 * 10s cache, 1 retry, 5s stale time
 */
export function useOCIntelFeed() {
  return useQuery<OCIntelFeedResponse>({
    queryKey: ['oc-intel-feed'],
    queryFn: fetchOCIntelFeed,
    staleTime: 5000, // 5s stale time
    gcTime: 10000, // 10s cache
    retry: 1,
    refetchInterval: 30000, // Auto-refetch every 30s
  });
}
