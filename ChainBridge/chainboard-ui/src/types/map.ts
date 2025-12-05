// Reality Gap Visualization
export interface GhostShip {
  shipmentId: string;
  plannedCoordinates: [number, number]; // From EDI 214/856
  actualCoordinates: [number, number];  // From IoT
  gapDistanceKm: number;
}
// Reality Gap Visualization
export interface GhostShip {
  shipmentId: string;
  plannedCoordinates: [number, number]; // From EDI 214/856
  actualCoordinates: [number, number];  // From IoT
  gapDistanceKm: number;
}
/**
 * Global Operations Map Type Definitions
 * "God View" telemetry and geospatial data structures
 */

export interface Coordinates {
  longitude: number;
  latitude: number;
}

export interface PortTelemetry {
  id: string;
  name: string;
  code: string;
  coordinates: Coordinates;
  congestionLevel: number; // 0-100
  throughput: number; // TEUs per day
  riskScore: number; // 0-100
  activeShipments: number;
}

export interface VesselTelemetry {
  id: string;
  name: string;
  imo?: string;
  coordinates: Coordinates;
  heading: number; // degrees 0-360
  speed: number; // knots
  riskScore: number; // 0-100
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  cargoValue: number; // USD
  origin: Coordinates;
  destination: Coordinates;
  eta: string; // ISO timestamp
  status: 'IN_TRANSIT' | 'AT_PORT' | 'DELAYED' | 'AT_RISK';
}

export interface RiskZone {
  id: string;
  name: string;
  polygon: Coordinates[];
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  reason: string; // "Weather Event", "Piracy", "Political Unrest"
  severity: number; // 0-100
}

export interface RouteSegment {
  from: Coordinates;
  to: Coordinates;
  vesselId: string;
  color: [number, number, number]; // RGB
  animated: boolean;
}

export interface GlobalMapState {
  vessels: VesselTelemetry[];
  ports: PortTelemetry[];
  riskZones: RiskZone[];
  routes: RouteSegment[];
  timestamp: string;
}

export interface MapViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
  transitionDuration?: number;
  transitionInterpolator?: any;
}

export interface MapTooltipInfo {
  object: VesselTelemetry | PortTelemetry | RiskZone;
  x: number;
  y: number;
  type: 'vessel' | 'port' | 'risk-zone';
}
