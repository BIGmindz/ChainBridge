import type {
    FleetTelemetryResponse,
    GlobalIntelSnapshot,
    LiveShipmentPosition,
    OCIntelFeedResponse,
} from '@/types/chainbridge';

// Mock data for demo
const generateMockIntelFeed = (): OCIntelFeedResponse => {
  return {
    globalSnapshot: {
      globalTotals: {
        totalShipments: 1247,
        activeShipments: 1150,
        blockedShipments: 23,
        settlementsInFlight: 45678900,
      },
      corridorKpis: [
        { corridorId: 'ASIA-EU', corridorName: 'Asia-Europe', stpRate: 87.3, avgEtaDeltaMinutes: 12 * 60, highRiskShipments: 15, atRiskShipments: 45 },
        { corridorId: 'TRANS-PAC', corridorName: 'Trans-Pacific', stpRate: 92.1, avgEtaDeltaMinutes: 8 * 60, highRiskShipments: 5, atRiskShipments: 20 },
        { corridorId: 'AMERICAS', corridorName: 'Americas', stpRate: 89.5, avgEtaDeltaMinutes: 15 * 60, highRiskShipments: 3, atRiskShipments: 12 },
      ],
      modeKpis: [
        { mode: 'OCEAN', stpRate: 85.0, avgEtaDeltaMinutes: 24 * 60, activeShipments: 890, highRiskShipments: 40 },
        { mode: 'AIR', stpRate: 98.0, avgEtaDeltaMinutes: 2 * 60, activeShipments: 250, highRiskShipments: 5 },
        { mode: 'TRUCK_FTL', stpRate: 95.0, avgEtaDeltaMinutes: 45, activeShipments: 107, highRiskShipments: 2 },
      ],
      portHotspots: [
        { portCode: 'CNSHA', portName: 'Shanghai', country: 'China', congestionScore: 92, highRiskShipments: 12, activeShipments: 78 },
        { portCode: 'SGSIN', portName: 'Singapore', country: 'Singapore', congestionScore: 68, highRiskShipments: 8, activeShipments: 45 },
      ],
      timestamp: new Date().toISOString(),
    },
    queueCards: [],
    livePositionsMeta: {
      activeShipments: 1247,
      corridorsCovered: 3,
      portsCovered: 2,
    },
  };
};

/**
 * Fetch unified Operator Console Intel Feed
 * Returns global snapshot + live positions in one call
 * 10s cache, 1 retry on failure
 */
export const fetchOCIntelFeed = async (): Promise<OCIntelFeedResponse> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return generateMockIntelFeed();
};

/**
 * Fetch global intelligence snapshot
 * KPIs, corridor breakdowns, mode stats, port risk rankings
 */
export const fetchGlobalIntelSnapshot = async (): Promise<GlobalIntelSnapshot> => {
  await new Promise(resolve => setTimeout(resolve, 300));
  return generateMockIntelFeed().globalSnapshot;
};

/**
 * Fetch live shipment positions for map rendering
 * Returns array of all active shipments with lat/lon + metadata
 */
export const fetchLiveShipmentPositions = async (): Promise<LiveShipmentPosition[]> => {
  await new Promise(resolve => setTimeout(resolve, 200));
  return [];
};

/**
 * Fetch fleet telemetry for 3D map visualization
 * Returns real-time ship positions, headings, velocities for all active shipments
 * Poll at 2s interval for smooth animations
 */
export const fetchFleetTelemetry = async (): Promise<FleetTelemetryResponse> => {
  await new Promise(resolve => setTimeout(resolve, 200));
  return { shipments: [], timestamp: new Date().toISOString(), totalCount: 0 };
};
