import { useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';

import { fetchOCIntelFeed } from '@/services/intelClient';
import type { OCIntelFeedResponse } from '@/types/chainbridge';

/**
 * Operator Console Intel Feed Hook
 * Unified data source for OC cockpit intelligence
 * Professional error handling with retry capabilities
 */
export function useOCIntelFeed() {
  const query = useQuery<OCIntelFeedResponse>({
    queryKey: ['oc-intel-feed'],
    queryFn: fetchOCIntelFeed,
    staleTime: 5000, // 5s stale time
    gcTime: 10000, // 10s cache
    retry: 2, // Increased retry count
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000), // Exponential backoff
    refetchInterval: 30000, // Auto-refetch every 30s
    refetchOnWindowFocus: false, // Prevent excessive refetching
  });

  // Professional retry function
  const retry = useCallback(() => {
    query.refetch();
  }, [query]);

  return {
    ...query,
    retry,
    // Expose professional loading states
    isInitialLoading: query.isLoading && !query.data,
    isRefreshing: query.isFetching && !!query.data,
    hasError: !!query.error,
  };
}
