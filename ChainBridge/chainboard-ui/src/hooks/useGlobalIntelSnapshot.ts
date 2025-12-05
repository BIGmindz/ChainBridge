/**
 * Global Intelligence Snapshot Hook
 *
 * React Query hook for fetching aggregated metrics for the Global Intelligence view.
 * Provides real-time snapshot of global operations with money and risk awareness.
 */

import { useQuery } from '@tanstack/react-query';

import type { GlobalIntelSnapshot } from '../types/chainbridge';

// Mock data for demonstration
const MOCK_GLOBAL_SNAPSHOT: GlobalIntelSnapshot = {
  globalTotals: {
    totalShipments: 1250,
    activeShipments: 1150,
    blockedShipments: 25,
    settlementsInFlight: 45000000,
  },
  corridorKpis: [
    { corridorId: 'US-MX', corridorName: 'US-Mexico', stpRate: 95, avgEtaDeltaMinutes: 30, highRiskShipments: 5, atRiskShipments: 10 },
    { corridorId: 'EU-US', corridorName: 'Europe-US', stpRate: 92, avgEtaDeltaMinutes: 60, highRiskShipments: 8, atRiskShipments: 15 },
  ],
  modeKpis: [
    { mode: 'OCEAN', stpRate: 88, avgEtaDeltaMinutes: 120, activeShipments: 600, highRiskShipments: 20 },
    { mode: 'AIR', stpRate: 98, avgEtaDeltaMinutes: 15, activeShipments: 200, highRiskShipments: 2 },
  ],
  portHotspots: [
    { portCode: 'USLAX', portName: 'Los Angeles', country: 'US', congestionScore: 85, highRiskShipments: 12, activeShipments: 50 },
    { portCode: 'CNSHA', portName: 'Shanghai', country: 'CN', congestionScore: 90, highRiskShipments: 15, activeShipments: 80 },
  ],
  timestamp: new Date().toISOString(),
};

export const useGlobalIntelSnapshot = () => {
  return useQuery({
    queryKey: ['globalIntelSnapshot'],
    queryFn: async () => {
      // In a real app, this would call the API
      // return apiClient.getGlobalIntelSnapshot();
      await new Promise((resolve) => setTimeout(resolve, 500));
      return MOCK_GLOBAL_SNAPSHOT;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
};
