/**
 * Live Shipment Positions Hook
 *
 * React Query hook for fetching real-time shipment positions with money and settlement data.
 * Powers the interactive Global Intelligence map.
 */

import { useQuery } from '@tanstack/react-query';

import type { LiveShipmentPosition } from '@/types/chainbridge';

// Mock live shipment data for demonstration
const MOCK_LIVE_SHIPMENTS: LiveShipmentPosition[] = [
  {
    shipmentId: 'SHP-US-MX-001',
    canonicalShipmentRef: 'SHP-US-MX-001',
    externalRef: 'ACME-180K-01',
    lat: 32.715738,
    lon: -117.161084,
    corridor: 'US-MX',
    mode: 'OCEAN',
    status: 'ON_TIME',
    riskScore: 0.15,
    riskCategory: 'LOW',
    cargoValueUsd: 180000,
    financedAmountUsd: 126000,
    paidAmountUsd: 54000,
    settlementState: 'PARTIALLY_PAID',
    stakeApr: 3.2,
    stakeCapacityUsd: 95000,
    originPortCode: 'USLAX',
    originPortName: 'Los Angeles',
    destPortCode: 'MXENS',
    destPortName: 'Ensenada',
    distanceToNearestPortKm: 45,
    eta: '2025-11-24T12:00:00Z',
    lastEventCode: 'DEPARTED_PORT',
    lastEventTs: '2025-11-21T08:30:00Z',
  },
  {
    shipmentId: 'SHP-EU-US-002',
    canonicalShipmentRef: 'SHP-EU-US-002',
    externalRef: 'BETA-220K-02',
    lat: 51.9244,
    lon: 4.4777,
    corridor: 'EU-US',
    mode: 'OCEAN',
    status: 'AT_RISK',
    riskScore: 0.82,
    riskCategory: 'HIGH',
    cargoValueUsd: 220000,
    financedAmountUsd: 154000,
    paidAmountUsd: 0,
    settlementState: 'FINANCED_UNPAID',
    stakeApr: 4.4,
    stakeCapacityUsd: 180000,
    originPortCode: 'NLRTM',
    originPortName: 'Rotterdam',
    destPortCode: 'USNYC',
    destPortName: 'New York',
    distanceToNearestPortKm: 2,
    eta: '2025-11-26T15:00:00Z',
    lastEventCode: 'TEMP_BREACH',
    lastEventTs: '2025-11-21T10:15:00Z',
  },
  {
    shipmentId: 'SHP-APAC-US-003',
    canonicalShipmentRef: 'SHP-APAC-US-003',
    externalRef: 'GAMMA-410K-03',
    lat: 1.3521,
    lon: 103.8198,
    corridor: 'APAC-US',
    mode: 'OCEAN',
    status: 'ON_TIME',
    riskScore: 0.08,
    riskCategory: 'LOW',
    cargoValueUsd: 410000,
    financedAmountUsd: 287000,
    paidAmountUsd: 287000,
    settlementState: 'PAID',
    stakeApr: 3.8,
    stakeCapacityUsd: 210000,
    originPortCode: 'SGSIN',
    originPortName: 'Singapore',
    destPortCode: 'USLAX',
    destPortName: 'Los Angeles',
    distanceToNearestPortKm: 12,
    eta: '2025-11-28T09:00:00Z',
    lastEventCode: 'IN_TRANSIT',
    lastEventTs: '2025-11-21T06:45:00Z',
  },
  {
    shipmentId: 'SHP-US-CAN-004',
    canonicalShipmentRef: 'SHP-US-CAN-004',
    externalRef: 'DELTA-38K-04',
    lat: 49.2827,
    lon: -123.1207,
    corridor: 'US-CAN',
    mode: 'TRUCK_FTL',
    status: 'DELAYED',
    riskScore: 0.45,
    riskCategory: 'MEDIUM',
    cargoValueUsd: 38000,
    financedAmountUsd: 0,
    paidAmountUsd: 0,
    settlementState: 'UNFINANCED',
    stakeApr: 5.1,
    stakeCapacityUsd: 45000,
    originPortCode: 'USSEA',
    originPortName: 'Seattle',
    destPortCode: 'CAVAN',
    destPortName: 'Vancouver',
    distanceToNearestPortKm: 180,
    eta: '2025-11-22T18:00:00Z',
    lastEventCode: 'BORDER_DELAY',
    lastEventTs: '2025-11-21T11:30:00Z',
  },
  {
    shipmentId: 'SHP-US-DOM-005',
    canonicalShipmentRef: 'SHP-US-DOM-005',
    externalRef: 'ECHO-150K-05',
    lat: 41.8781,
    lon: -87.6298,
    corridor: 'US-DOMESTIC',
    mode: 'TRUCK_FTL',
    status: 'AT_RISK',
    riskScore: 0.67,
    riskCategory: 'HIGH',
    cargoValueUsd: 150000,
    financedAmountUsd: 105000,
    paidAmountUsd: 35000,
    settlementState: 'PARTIALLY_PAID',
    stakeApr: 6,
    stakeCapacityUsd: 125000,
    originPortCode: 'USCHI',
    originPortName: 'Chicago',
    destPortCode: 'USDET',
    destPortName: 'Detroit',
    distanceToNearestPortKm: 450,
    eta: '2025-11-23T14:00:00Z',
    lastEventCode: 'DRIVER_ISSUE',
    lastEventTs: '2025-11-21T09:20:00Z',
  },
];

async function fetchLiveShipmentPositions(): Promise<LiveShipmentPosition[]> {
  const response = await fetch('/api/intel/live-positions');
  if (!response.ok) {
    throw new Error('Live shipment API returned an error');
  }
  return (await response.json()) as LiveShipmentPosition[];
}

export function useLiveShipmentPositions() {
  return useQuery<LiveShipmentPosition[], Error>({
    queryKey: ['live-shipment-positions'],
    queryFn: async () => {
      try {
        return await fetchLiveShipmentPositions();
      } catch (error) {
        console.warn('Live positions API unavailable, using mock data:', error);
        return MOCK_LIVE_SHIPMENTS;
      }
    },
    refetchInterval: 30_000, // 30 seconds
    staleTime: 10_000, // 10 seconds
  });
}
