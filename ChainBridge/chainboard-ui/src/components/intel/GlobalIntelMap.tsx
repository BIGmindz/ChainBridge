import React, { useState } from 'react';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

import type { RiskLevel } from '@/types/chainbridge';
import type { IntelShipmentPoint } from '@/types/intel';

// TopoJSON for world map - using public CDN
const WORLD_TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

type GlobalIntelMapProps = {
  points: IntelShipmentPoint[];
  isLoading?: boolean;
  onSelectShipment?: (shipment: IntelShipmentPoint) => void;
};

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
};

const getRiskColor = (riskCategory?: RiskLevel): string => {
  switch (riskCategory) {
    case 'CRITICAL':
      return '#f87171'; // red-400
    case 'HIGH':
      return '#fb923c'; // orange-400
    case 'MEDIUM':
      return '#fcd34d'; // amber-300
    case 'LOW':
    default:
      return '#34d399'; // emerald-400
  }
};

const GlobalIntelMap: React.FC<GlobalIntelMapProps> = ({ points, isLoading, onSelectShipment }) => {
  const [hoveredPoint, setHoveredPoint] = useState<IntelShipmentPoint | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const handleMarkerEnter = (point: IntelShipmentPoint, event: React.MouseEvent<SVGGElement>) => {
    setHoveredPoint(point);
    setMousePos({ x: event.clientX, y: event.clientY });
  };

  const handleMarkerLeave = () => {
    setHoveredPoint(null);
  };

  const handleMarkerClick = (point: IntelShipmentPoint) => {
    if (onSelectShipment) {
      onSelectShipment(point);
    }
  };

  if (isLoading && points.length === 0) {
    return (
      <div className="w-full h-[520px] rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg overflow-hidden flex items-center justify-center">
        <div className="text-slate-400 text-sm animate-pulse">Loading global intel…</div>
      </div>
    );
  }

  return (
    <>
      <div className="w-full h-[520px] rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg overflow-hidden relative">
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: 147 } as any}
          width={800}
          height={520}
        >
          <Geographies geography={WORLD_TOPO_URL}>
            {({ geographies }: any) =>
              geographies.map((geo: any) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#1e293b"
                  stroke="#475569"
                  strokeWidth={0.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { outline: 'none', fill: '#334155' },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {points.map((point) => {
            const color = getRiskColor(point.riskCategory);
            const isHovered = hoveredPoint?.id === point.id;

            return (
              <Marker key={point.id} coordinates={[point.lon, point.lat]}>
                <g
                  onMouseEnter={(e) => handleMarkerEnter(point, e)}
                  onMouseLeave={handleMarkerLeave}
                  onClick={() => handleMarkerClick(point)}
                  style={{ cursor: 'pointer' }}
                >
                  <circle
                    r={isHovered ? 8 : 6}
                    fill={color}
                    fillOpacity={0.9}
                    stroke={color}
                    strokeWidth={isHovered ? 2 : 1}
                    filter={isHovered ? 'url(#glow)' : undefined}
                  />
                </g>
              </Marker>
            );
          })}

          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        </ComposableMap>
      </div>

      {hoveredPoint && (
        <div
          className="pointer-events-none fixed z-40 rounded-xl border border-slate-700 bg-slate-900/95 px-3 py-2 text-xs text-slate-50 shadow-xl"
          style={{
            left: `${mousePos.x + 12}px`,
            top: `${mousePos.y + 12}px`,
          }}
        >
          <div className="space-y-1">
            <div className="font-semibold text-slate-100">{hoveredPoint.id}</div>
            <div className="text-slate-300">
              {hoveredPoint.corridorLabel || hoveredPoint.corridorId || 'Unknown Corridor'}
            </div>
            <div className="flex items-center gap-2 pt-1 border-t border-slate-700">
              <span className="text-slate-400">Value:</span>
              <span className="font-mono text-emerald-400">
                {formatCurrency(hoveredPoint.valueUsd)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Risk:</span>
              <span
                className="font-mono"
                style={{ color: getRiskColor(hoveredPoint.riskCategory) }}
              >
                {hoveredPoint.riskCategory || 'UNKNOWN'} (
                {(hoveredPoint.riskScore / 100).toFixed(2)})
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Financed:</span>
              <span className="text-slate-300">
                {(hoveredPoint.stakeCapacityUsd ?? 0) > 0 ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default GlobalIntelMap;
