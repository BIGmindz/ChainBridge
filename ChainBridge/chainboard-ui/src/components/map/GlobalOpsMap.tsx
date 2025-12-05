import { HexagonLayer } from '@deck.gl/aggregation-layers';
import { AmbientLight, LightingEffect, PointLight } from '@deck.gl/core';
import { ScatterplotLayer, LineLayer, IconLayer } from '@deck.gl/layers';
import DeckGL from '@deck.gl/react';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useEffect, useMemo, useState } from 'react';
import { Map } from 'react-map-gl/mapbox';

import { fetchGlobalMapState } from '../../services/telemetryApi';
import type { GlobalMapState, VesselTelemetry, GhostShip } from '../../types/map';

// --- CONFIGURATION ---
// ✅ SATELLITE UPLINK ESTABLISHED
const MAPBOX_TOKEN =
  'pk.eyJ1Ijoiam9obmJvenphIiwiYSI6ImNtaWQ0a3FiazAyaTIyd29ybzl0YWU3NnIifQ.3RZRS5Zhq2ONHEhomNWwOw';
// SATELLITE HYBRID STYLE (Photorealistic Earth + City Labels)
const MAP_STYLE = 'mapbox://styles/mapbox/satellite-streets-v12';

// --- LIGHTING (3D Depth) ---
const ambientLight = new AmbientLight({ color: [255, 255, 255], intensity: 1.0 });
const pointLight = new PointLight({
  color: [255, 255, 255],
  intensity: 2.0,
  position: [-0.1276, 51.5074, 80000],
});
const lightingEffect = new LightingEffect({ ambientLight, pointLight });

export const GlobalOpsMap = () => {
  const [viewState, setViewState] = useState({
    longitude: -30,
    latitude: 30,
    zoom: 1.5,
    pitch: 45,
    bearing: 0,
  });

  const [time, setTime] = useState(0);
  const [mapData, setMapData] = useState<GlobalMapState | null>(null);

  const ghostShips: GhostShip[] = useMemo(() => {
    if (!mapData?.vessels) return [];
    return mapData.vessels.map((v) => ({
      shipmentId: v.id,
      plannedCoordinates: [v.origin.longitude, v.origin.latitude],
      actualCoordinates: [v.coordinates.longitude, v.coordinates.latitude],
      gapDistanceKm: 0,
    }));
  }, [mapData?.vessels]);

  // Fetch Data
  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchGlobalMapState();
        setMapData(data);
      } catch (err) {
        console.error('Failed to load map data', err);
      }
    };

    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  // Animation Loop (Auto-Rotate + Pulse)
  useEffect(() => {
    let animationFrame: number;
    const animate = () => {
      setTime((t) => (t + 1) % 360);
      // Slow Rotation for "Command Center" feel
      setViewState((v) => ({ ...v, longitude: v.longitude + 0.02 }));
      animationFrame = requestAnimationFrame(animate);
    };
    animate();
    return () => cancelAnimationFrame(animationFrame);
  }, []);

  // --- LAYERS ---
  const layers = [
    // 1. THE CITADEL (3D Hexagon Heatmap)
    // Shows density of assets at ports
    new HexagonLayer({
      id: 'heatmap',
      data: mapData?.vessels || [],
      getPosition: (d: VesselTelemetry) => [d.coordinates.longitude, d.coordinates.latitude],
      radius: 40000, // ~40km bins
      elevationScale: 500,
      extruded: true,
      pickable: true,
      upperPercentile: 100,
      material: { ambient: 0.64, diffuse: 0.6, shininess: 32, specularColor: [51, 51, 51] },
      // Matrix/Cyberpunk Palette
      colorRange: [
        [1, 152, 189],
        [73, 227, 206],
        [216, 254, 181],
        [254, 237, 177],
        [254, 173, 154],
        [209, 55, 78],
      ],
      transitions: {
        elevationScale: 3000,
      },
    }),

    // 2. RISK BEACONS (Pulsing Red Circles)
    // Highlights critical failures
    // GHOST FLEET: Planned EDI positions
    new ScatterplotLayer({
      id: 'ghost-fleet',
      data: ghostShips,
      getPosition: (d: GhostShip) => d.plannedCoordinates,
      getRadius: 5000,
      getFillColor: [100, 116, 139, 100],
      stroked: true,
      getLineColor: [100, 116, 139, 180],
      getLineWidth: 2000,
      filled: false,
      pickable: true,
      onHover: ({ object, x, y }) => {
        if (object) {
          const tooltip = document.getElementById('ghost-tooltip');
          if (tooltip) {
            tooltip.style.display = 'block';
            tooltip.style.left = `${x + 12}px`;
            tooltip.style.top = `${y - 12}px`;
            tooltip.innerHTML = `LATENCY GAP: <b>${object.gapDistanceKm.toFixed(1)} km</b><br/><span style='font-size:11px'>EDI Plan vs IoT Reality</span>`;
          }
        }
      },
      onLeave: () => {
        const tooltip = document.getElementById('ghost-tooltip');
        if (tooltip) tooltip.style.display = 'none';
      },
    }),

    // TETHER: Line from planned to actual
    new LineLayer({
      id: 'reality-gap-tether',
      data: ghostShips,
      getSourcePosition: (d: GhostShip) => d.plannedCoordinates,
      getTargetPosition: (d: GhostShip) => d.actualCoordinates,
      getColor: (d: GhostShip) => (d.gapDistanceKm > 50 ? [220, 38, 38, 180] : [34, 197, 94, 180]),
      getWidth: 2000,
      opacity: 0.9,
      pickable: true,
      onHover: ({ object, x, y }) => {
        if (object) {
          const tooltip = document.getElementById('ghost-tooltip');
          if (tooltip) {
            tooltip.style.display = 'block';
            tooltip.style.left = `${x + 12}px`;
            tooltip.style.top = `${y - 12}px`;
            tooltip.innerHTML = `LATENCY GAP: <b>${object.gapDistanceKm.toFixed(1)} km</b><br/><span style='font-size:11px'>EDI Plan vs IoT Reality</span>`;
          }
        }
      },
      onLeave: () => {
        const tooltip = document.getElementById('ghost-tooltip');
        if (tooltip) tooltip.style.display = 'none';
      },
    }),

    // REAL FLEET: Actual IoT positions
    new IconLayer({
      id: 'real-fleet',
      data: ghostShips,
      getPosition: (d: GhostShip) => d.actualCoordinates,
      getIcon: () => 'marker',
      getSize: 4,
      getColor: [59, 130, 246, 255],
      pickable: true,
    }),
    new ScatterplotLayer({
      id: 'risk-beacons',
      data: mapData?.vessels || [],
      getPosition: (d: VesselTelemetry) => [d.coordinates.longitude, d.coordinates.latitude],
      // Pulse Animation Logic
      getRadius: (d: VesselTelemetry) =>
        d.riskScore > 95 ? 80000 + Math.sin(time * 0.1) * 30000 : 0,
      getFillColor: [255, 0, 0, 150],
      stroked: true,
      getLineColor: [255, 0, 0, 255],
      getLineWidth: 4000,
      filled: true,
      updateTriggers: { getRadius: time },
    }),
  ];

  const hasToken = !!MAPBOX_TOKEN && MAPBOX_TOKEN.startsWith('pk');

  return (
    <div
      id="deckgl-wrapper"
      className="fixed inset-0 z-0 bg-slate-950"
      style={{ height: '100vh', width: '100vw' }}
    >
      <DeckGL
        viewState={viewState}
        controller={true}
        layers={layers}
        effects={[lightingEffect]}
        // @ts-expect-error - ViewState type mismatch
        onViewStateChange={(e) => setViewState(e.viewState)}
      >
        {hasToken ? (
          <Map
            mapboxAccessToken={MAPBOX_TOKEN}
            mapStyle={MAP_STYLE}
            reuseMaps
            // 🌍 ENABLE 3D TERRAIN (Mountains/Depth)
            terrain={{ source: 'mapbox-dem', exaggeration: 1.5 }}
            // Add Fog for depth perception at horizon (The "Curve of the Earth")
            fog={{
              range: [0.5, 10],
              color: '#0f172a',
              'horizon-blend': 0.3,
            }}
          />
        ) : (
          <>
            {/* Reality Gap Tooltip */}
            <div
              id="ghost-tooltip"
              style={{
                position: 'absolute',
                pointerEvents: 'none',
                background: 'rgba(30,41,59,0.95)',
                color: '#fff',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '13px',
                fontFamily: 'monospace',
                zIndex: 100,
                display: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              }}
            />

            {/* FAILSAFE: Tactical Grid if Token is Invalid */}
            <div className="w-full h-full bg-[linear-gradient(rgba(0,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,255,0.03)_1px,transparent_1px)] bg-[size:100px_100px]">
              <div className="absolute bottom-10 left-10 text-slate-600 font-mono text-xs">
                [WARN] SATELLITE LINK OFFLINE // WIREFRAME MODE ACTIVE
              </div>
            </div>
          </>
        )}
      </DeckGL>

      {/* SCANLINES OVERLAY */}
      <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-50 bg-[length:100%_2px,3px_100%] opacity-20"></div>
    </div>
  );
};
