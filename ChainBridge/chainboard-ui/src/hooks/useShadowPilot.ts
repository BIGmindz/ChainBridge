/**
 * Shadow Pilot React Query Hooks
 *
 * Custom hooks for fetching Shadow Pilot data with React Query.
 * Provides caching, background refetch, and error handling.
 * Falls back to mock data when API is unavailable.
 */

import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import {
    fetchShadowPilotShipments,
    fetchShadowPilotSummaries,
    fetchShadowPilotSummary,
} from '../services/apiClient';
import {
    MOCK_SHADOW_PILOT_SUMMARIES,
    generateMockShadowPilotSummary,
    getMockShadowPilotShipments,
} from '../services/mockShadowPilotData';
import type {
    PaginatedShadowPilotShipments,
    ShadowPilotSummary,
} from '../types/chainbridge';

// Enable demo mode (set to true to use mock data, false for live API)
const DEMO_MODE = true;

export function useShadowPilotSummaries() {
  return useQuery<ShadowPilotSummary[], Error>({
    queryKey: ['shadowPilot', 'summaries'],
    queryFn: async () => {
      if (DEMO_MODE) {
        return MOCK_SHADOW_PILOT_SUMMARIES;
      }
      try {
        return await fetchShadowPilotSummaries();
      } catch (error) {
        console.warn('Shadow Pilot API unavailable, falling back to demo data:', error);
        return MOCK_SHADOW_PILOT_SUMMARIES;
      }
    },
  });
}

export function useShadowPilotSummary(runId: string | undefined) {
  return useQuery<ShadowPilotSummary, Error>({
    queryKey: ['shadowPilot', 'summary', runId],
    queryFn: async () => {
      if (DEMO_MODE) {
        return generateMockShadowPilotSummary();
      }
      try {
        return await fetchShadowPilotSummary(runId!);
      } catch (error) {
        console.warn('Shadow Pilot API unavailable, falling back to demo data:', error);
        return generateMockShadowPilotSummary();
      }
    },
    enabled: !!runId,
  });
}

export function useShadowPilotShipments(runId: string | undefined) {
  return useInfiniteQuery<PaginatedShadowPilotShipments, Error>({
    queryKey: ['shadowPilot', 'shipments', runId],
    queryFn: async ({ pageParam }) => {
      if (DEMO_MODE) {
        return getMockShadowPilotShipments(runId!);
      }
      try {
        return await fetchShadowPilotShipments(runId!, pageParam as string | undefined);
      } catch (error) {
        console.warn('Shadow Pilot API unavailable, falling back to demo data:', error);
        return getMockShadowPilotShipments(runId!);
      }
    },
    enabled: !!runId,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    initialPageParam: undefined,
  });
}
