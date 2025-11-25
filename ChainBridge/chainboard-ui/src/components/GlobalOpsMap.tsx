/**
 * GlobalOpsMap - Enhanced "God View" with High-Visibility Globe
 *
 * CHAINBRIDGE PAC - Standardized Location Version
 * Enterprise-grade 3D geospatial visualization with visible wireframe earth
 *
 * @author Sonny, Senior Frontend Engineer
 */

import { HexagonLayer } from '@deck.gl/aggregation-layers';
import type { PickingInfo } from '@deck.gl/core';
import { AmbientLight, FlyToInterpolator, LightingEffect, PointLight } from '@deck.gl/core';
import { ArcLayer, IconLayer, PathLayer, PolygonLayer } from '@deck.gl/layers';
import DeckGL from '@deck.gl/react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Map } from 'react-map-gl/mapbox';

import 'mapbox-gl/dist/mapbox-gl.css';

import { useGlobalMapState, useVesselTelemetry } from '@/hooks/useMapTelemetry';
import type { MapViewState, PortTelemetry, RiskZone, VesselTelemetry } from '@/types/map';

// Mapbox token (will gracefully degrade if placeholder)
const MAPBOX_ACCESS_TOKEN =
  import.meta.env.VITE_MAPBOX_TOKEN ||
  'pk.eyJ1IjoiY2hhaW5icmlkZ2UiLCJhIjoiY2x2M3RtZGFkMDFtNjJqbzQ3aWN2ZWNhYSJ9.placeholder';

// Generate visible globe wireframe grid
const generateGlobeWireframe = () => {
  const lines = [];
  const latLines = 18; // Latitude circles
  const lonLines = 36; // Longitude meridians

  // Latitude lines (horizontal)
  for (let i = 0; i <= latLines; i++) {
    const lat = -90 + (180 * i) / latLines;
    const points = [];
    for (let j = 0; j <= lonLines; j++) {
      const lon = -180 + (360 * j) / lonLines;
      points.push([lon, lat]);
    }
    lines.push({ coordinates: points });
  }

  // Longitude lines (vertical)
  for (let i = 0; i <= lonLines; i++) {
    const lon = -180 + (360 * i) / lonLines;
    const points = [];
    for (let j = 0; j <= latLines; j++) {
      const lat = -90 + (180 * j) / latLines;
      points.push([lon, lat]);
    }
    lines.push({ coordinates: points });
  }

  return lines;
};

// Mock Data Generation for "Data Citadel"
const generateMockFleet = () => {
  const fleet = [];
  const ports = [
    { lon: -118.24, lat: 34.05, name: 'LA' },
    { lon: 121.47, lat: 31.23, name: 'Shanghai' },
    { lon: 4.47, lat: 51.92, name: 'Rotterdam' },
    { lon: 103.81, lat: 1.35, name: 'Singapore' },
    { lon: -74.0, lat: 40.71, name: 'NY' },
    { lon: 55.27, lat: 25.2, name: 'Dubai' },
    { lon: 139.69, lat: 35.68, name: 'Tokyo' },
    { lon: -0.12, lat: 51.5, name: 'London' },
  ];

  for (let i = 0; i < 500; i++) {
    const port = ports[Math.floor(Math.random() * ports.length)];
    // Random spread around the port
    const spread = 15; // degrees spread
    fleet.push({
      coordinates: [
        port.lon + (Math.random() - 0.5) * spread,
        port.lat + (Math.random() - 0.5) * spread,
      ],
    });
  }
  return fleet;
};

const MOCK_FLEET = generateMockFleet();

// Initial view: Elevated for full globe visibility
const INITIAL_VIEW_STATE: MapViewState = {
  longitude: -40,
  latitude: 20,
  zoom: 1.2,
  pitch: 45, // Angled for 3D effect
  bearing: 0,
};

// 3D Lighting
const ambientLight = new AmbientLight({
  color: [255, 255, 255],
  intensity: 1.2,
});

const pointLight = new PointLight({
  color: [255, 255, 255],
  intensity: 2.0,
  position: [-0.144528, 49.739968, 80000],
});

const lightingEffect = new LightingEffect({ ambientLight, pointLight });

type GlobalOpsMapProps = {
  onVesselClick?: (vesselId: string) => void;
  selectedVesselId?: string | null;
  mapStyle?: 'dark' | 'satellite';
  flyToVessel?: string | null;
};

const getRiskColor = (
  riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW',
): [number, number, number] => {
  switch (riskLevel) {
    case 'CRITICAL':
      return [239, 68, 68]; // red-500
    case 'HIGH':
      return [251, 146, 60]; // orange-400
    case 'MEDIUM':
      return [251, 191, 36]; // amber-400
    case 'LOW':
    default:
      return [52, 211, 153]; // emerald-400
  }
};

const getMapStyle = (style: 'dark' | 'satellite') => {
  return style === 'satellite'
    ? 'mapbox://styles/mapbox/satellite-streets-v12'
    : 'mapbox://styles/mapbox/dark-v11';
};

export default function GlobalOpsMap({
  onVesselClick,
  selectedVesselId,
  mapStyle = 'dark',
  flyToVessel,
}: GlobalOpsMapProps) {
  const { data: globalState } = useGlobalMapState();
  const { data: vessels } = useVesselTelemetry();

  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW_STATE);
  const animationFrameRef = useRef<number>();
  const [pulseRadius, setPulseRadius] = useState(1.0);

  // Pulsing animation for CRITICAL vessels
  useEffect(() => {
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const pulse = 1.0 + Math.sin(elapsed / 300) * 0.3;
      setPulseRadius(pulse);

      // Auto-rotate effect
      setViewState((v) => ({
        ...v,
        longitude: v.longitude + 0.02, // Slow spin
      }));

      animationFrameRef.current = requestAnimationFrame(animate);
    };
    animationFrameRef.current = requestAnimationFrame(animate);
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Cinematic camera fly-to
  useEffect(() => {
    if (flyToVessel && vessels) {
      const vessel = vessels.find((v) => v.id === flyToVessel);
      if (vessel) {
        setViewState({
          longitude: vessel.coordinates.longitude,
          latitude: vessel.coordinates.latitude,
          zoom: 10,
          pitch: 60,
          bearing: vessel.heading || 0,
          transitionDuration: 1500,
          transitionInterpolator: new FlyToInterpolator(),
        });
      }
    }
  }, [flyToVessel, vessels]);

  // LAYER 0: Globe Wireframe (High Visibility Base)
  const globeWireframeLayer = useMemo(
    () =>
      new PathLayer<{ coordinates: number[][] }>({
        id: 'globe-wireframe',
        data: generateGlobeWireframe(),
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        getPath: (d: any) => d.coordinates,
        getColor: [100, 116, 139, 80], // slate-500 with higher opacity
        getWidth: 1.5,
        widthMinPixels: 1,
        pickable: false,
      }),
    [],
  );

  // LAYER 1: Risk Zones
  const riskZoneLayer = useMemo(
    () =>
      new PolygonLayer({
        id: 'risk-zones',
        data: globalState?.riskZones || [],
        getPolygon: (d: RiskZone) => d.polygon.map((coord) => [coord.longitude, coord.latitude]),
        getFillColor: (d: RiskZone) => {
          const alpha = d.riskLevel === 'CRITICAL' ? 80 : d.riskLevel === 'HIGH' ? 50 : 30;
          return [239, 68, 68, alpha];
        },
        getLineColor: [239, 68, 68, 200],
        getLineWidth: 2,
        lineWidthMinPixels: 1,
        pickable: true,
        stroked: true,
        filled: true,
      }),
    [globalState?.riskZones],
  );

  // LAYER 2: Port Congestion (3D Hexagons)
  const portLayer = useMemo(
    () =>
      new IconLayer<PortTelemetry>({
        id: 'ports',
        data: globalState?.ports || [],
        getPosition: (d) => [d.coordinates.longitude, d.coordinates.latitude],
        getIcon: () => ({
          url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cG9seWdvbiBwb2ludHM9IjMyLDggNTIsMjAgNTIsNDQgMzIsNTYgMTIsNDQgMTIsMjAiIGZpbGw9ImN1cnJlbnRDb2xvciIgb3BhY2l0eT0iMC44Ii8+CiAgPHBvbHlnb24gcG9pbnRzPSIzMiwxNiA0NCwyNCA0NCw0MCAzMiw0OCAyMCw0MCAyMCwyNCIgZmlsbD0id2hpdGUiIG9wYWNpdHk9IjAuMyIvPgo8L3N2Zz4=',
          width: 64,
          height: 64,
        }),
        getSize: (d) => {
          const baseSize = 40;
          const congestionScale = 1 + d.congestionLevel / 100;
          return baseSize * congestionScale;
        },
        getColor: (d) => {
          if (d.congestionLevel > 80) return [239, 68, 68];
          if (d.congestionLevel > 50) return [251, 146, 60];
          return [52, 211, 153];
        },
        pickable: true,
        onClick: (info: PickingInfo) => {
          if (info.object) {
            const port = info.object as PortTelemetry;
            console.log('Port clicked:', port);
          }
        },
      }),
    [globalState?.ports],
  );

  // LAYER 3: Vessel Icons (The Fleet)
  const vesselLayer = useMemo(
    () =>
      new IconLayer<VesselTelemetry>({
        id: 'vessels',
        data: vessels || [],
        getPosition: (d) => [d.coordinates.longitude, d.coordinates.latitude],
        getIcon: () => ({
          url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHZpZXdCb3g9IjAgMCA0OCA0OCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cG9seWdvbiBwb2ludHM9IjI0LDggMzYsMTYgMzYsMzIgMjQsNDAgMTIsMzIgMTIsMTYiIGZpbGw9ImN1cnJlbnRDb2xvciIvPgogIDxwb2x5Z29uIHBvaW50cz0iMjQsMTYgMzAsMjAgMzAsMjggMjQsMzIgMTgsMjggMTgsMjAiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPg==',
          width: 48,
          height: 48,
        }),
        getSize: (d) => {
          const baseSize = 24;
          const selectedScale = d.id === selectedVesselId ? 1.5 : 1.0;
          const riskPulse = d.riskLevel === 'CRITICAL' ? pulseRadius : 1.0;
          return baseSize * selectedScale * riskPulse;
        },
        getColor: (d) => getRiskColor(d.riskLevel),
        getAngle: (d) => 360 - (d.heading || 0),
        pickable: true,
        onClick: (info: PickingInfo) => {
          if (info.object && onVesselClick) {
            const vessel = info.object as VesselTelemetry;
            onVesselClick(vessel.id);
          }
        },
        updateTriggers: {
          getSize: [selectedVesselId, pulseRadius],
        },
      }),
    [vessels, selectedVesselId, pulseRadius, onVesselClick],
  );

  // LAYER 4: Route Arcs
  const routeLayer = useMemo(
    () =>
      new ArcLayer<VesselTelemetry>({
        id: 'routes',
        data: vessels?.filter((v) => v.status === 'IN_TRANSIT') || [],
        getSourcePosition: (d) => [d.origin.longitude, d.origin.latitude],
        getTargetPosition: (d) => [d.coordinates.longitude, d.coordinates.latitude],
        getSourceColor: [100, 100, 100, 80],
        getTargetColor: (d) => [...getRiskColor(d.riskLevel), 120],
        getWidth: 2,
        pickable: false,
      }),
    [vessels],
  );

  // LAYER 5: The Citadel (3D Hexagons)
  const hexagonLayer = useMemo(
    () =>
      new HexagonLayer({
        id: 'heatmap',
        data: MOCK_FLEET,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        getPosition: (d: any) => d.coordinates,
        radius: 20000, // Size of the hex bins (in meters)
        elevationScale: 500, // Height multiplier
        extruded: true, // Make them 3D columns
        pickable: true,
        upperPercentile: 100,
        material: {
          ambient: 0.64,
          diffuse: 0.6,
          shininess: 32,
          specularColor: [51, 51, 51],
        },
        // The "Matrix" Color Palette (Cyan -> Blue -> Purple)
        colorRange: [
          [1, 152, 189],
          [73, 227, 206],
          [216, 254, 181],
          [254, 237, 177],
          [254, 173, 154],
          [209, 55, 78],
        ],
        transitions: {
          elevationScale: 3000, // Smooth grow animation on load
        },
      }),
    [],
  );

  // Layers array (Globe wireframe renders first!)
  const layers = useMemo(
    () => [globeWireframeLayer, hexagonLayer, riskZoneLayer, portLayer, routeLayer, vesselLayer],
    [globeWireframeLayer, hexagonLayer, riskZoneLayer, portLayer, routeLayer, vesselLayer],
  );

  const handleViewStateChange = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (params: any) => {
      setViewState(params.viewState);
    },
    [],
  );

  return (
    <div className="relative w-full h-full bg-slate-900">
      {/* CRT Scanline Overlay */}
      <div
        className="absolute inset-0 z-10 pointer-events-none opacity-30"
        style={{
          background:
            'repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.15) 0px, rgba(0, 0, 0, 0.15) 1px, transparent 1px, transparent 2px)',
        }}
      />

      {/* Deck.GL with Visible Globe */}
      <DeckGL
        viewState={viewState}
        onViewStateChange={handleViewStateChange}
        controller={true}
        layers={layers}
        effects={[lightingEffect]}
      >
        {/* Only render Mapbox if valid token exists */}
        {MAPBOX_ACCESS_TOKEN && !MAPBOX_ACCESS_TOKEN.includes('placeholder') ? (
          <Map
            mapboxAccessToken={MAPBOX_ACCESS_TOKEN}
            mapStyle={getMapStyle(mapStyle)}
            attributionControl={false}
          />
        ) : null}
      </DeckGL>
    </div>
  );
}
