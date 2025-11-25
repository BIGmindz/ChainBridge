/**
 * Telemetry API Client
 * Fetches real-time geospatial data for Global Operations Map
 */

import type { LiveShipmentPosition } from '@/types/chainbridge';
import type { GlobalMapState, PortTelemetry, RiskZone, VesselTelemetry } from '@/types/map';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * Fetch complete global state for God View map
 * Returns vessels, ports, risk zones, and active routes
 */
export const fetchGlobalMapState = async (): Promise<GlobalMapState> => {
  // For now, we only fetch vessels from the real API.
  // Ports and Risk Zones can remain mock or be fetched from another endpoint if available.
  // In a real scenario, we might want to parallelize these fetches.

  const vessels = await fetchVesselTelemetry();
  const ports = generateMockPorts(); // Keep mock ports for now
  const riskZones = generateMockRiskZones(); // Keep mock risk zones for now

  return {
    vessels,
    ports,
    riskZones,
    routes: [],
    timestamp: new Date().toISOString(),
  };
};

/**
 * Fetch live vessel telemetry from backend
 */
export const fetchVesselTelemetry = async (): Promise<VesselTelemetry[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/intel/live-positions`);
    if (!response.ok) {
      throw new Error(`Failed to fetch live positions: ${response.statusText}`);
    }
    const data: LiveShipmentPosition[] = await response.json();

    return data.map((pos) => ({
      id: pos.shipmentId,
      name: pos.canonicalShipmentRef || pos.shipmentId,
      imo: pos.externalRef,
      coordinates: { longitude: pos.lon, latitude: pos.lat },
      heading: 0, // Backend doesn't provide heading yet
      speed: 0, // Backend doesn't provide speed yet
      riskScore: Math.round(pos.riskScore * 100),
      riskLevel: (pos.riskBand as any) || 'LOW', // Cast or map correctly
      cargoValue: pos.cargoValueUsd,
      origin: { longitude: 0, latitude: 0 }, // Backend doesn't provide origin coords yet
      destination: { longitude: 0, latitude: 0 }, // Backend doesn't provide dest coords yet
      eta: pos.eta || new Date().toISOString(),
      status: mapStatus(pos.status),
    }));
  } catch (error) {
    console.error('Error fetching vessel telemetry:', error);
    return [];
  }
};

function mapStatus(status: string): 'IN_TRANSIT' | 'AT_PORT' | 'DELAYED' | 'AT_RISK' {
  switch (status) {
    case 'ON_TIME':
      return 'IN_TRANSIT';
    case 'DELAYED':
      return 'DELAYED';
    case 'AT_RISK':
      return 'AT_RISK';
    default:
      return 'IN_TRANSIT';
  }
}

// Mock data generators (kept for Ports and Risk Zones)

const generateMockPorts = (): PortTelemetry[] => {
  const majorPorts = [
    { name: 'Shanghai', code: 'CNSHA', lon: 121.5, lat: 31.2 },
    { name: 'Singapore', code: 'SGSIN', lon: 103.8, lat: 1.3 },
    { name: 'Rotterdam', code: 'NLRTM', lon: 4.5, lat: 51.9 },
    { name: 'Los Angeles', code: 'USLAX', lon: -118.2, lat: 33.7 },
    { name: 'Hamburg', code: 'DEHAM', lon: 9.9, lat: 53.5 },
    { name: 'Hong Kong', code: 'HKHKG', lon: 114.2, lat: 22.3 },
    { name: 'Dubai', code: 'AEDXB', lon: 55.3, lat: 25.2 },
    { name: 'New York', code: 'USNYC', lon: -74.0, lat: 40.7 },
  ];

  return majorPorts.map((port, i) => ({
    id: `port-${i}`,
    name: port.name,
    code: port.code,
    coordinates: { longitude: port.lon, latitude: port.lat },
    congestionLevel: Math.floor(Math.random() * 100),
    throughput: 10000 + Math.floor(Math.random() * 50000),
    riskScore: Math.floor(Math.random() * 100),
    activeShipments: Math.floor(Math.random() * 200),
  }));
};

const generateMockRiskZones = (): RiskZone[] => {
  return [
    {
      id: 'risk-1',
      name: 'Gulf of Aden - Piracy Risk',
      polygon: [
        { longitude: 43, latitude: 12 },
        { longitude: 51, latitude: 12 },
        { longitude: 51, latitude: 15 },
        { longitude: 43, latitude: 15 },
      ],
      riskLevel: 'HIGH',
      reason: 'Piracy',
      severity: 75,
    },
    {
      id: 'risk-2',
      name: 'South China Sea - Political Tension',
      polygon: [
        { longitude: 110, latitude: 8 },
        { longitude: 120, latitude: 8 },
        { longitude: 120, latitude: 20 },
        { longitude: 110, latitude: 20 },
      ],
      riskLevel: 'MEDIUM',
      reason: 'Political Unrest',
      severity: 50,
    },
  ];
};
