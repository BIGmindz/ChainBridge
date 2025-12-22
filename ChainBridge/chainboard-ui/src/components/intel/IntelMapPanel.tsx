/**
 * IntelMapPanel Component
 *
 * Interactive Global Intelligence Map with money and settlement awareness.
 * Shows live shipment positions with financial data, risk scores, and settlement states.
 *
 * V3: SONNY PAC upgrade - Real shipment tracking with ChainPay integration.
 */

import { AlertTriangle, Circle, Globe } from "lucide-react";

import { useLiveShipmentPositions } from "../../hooks/useLiveShipmentPositions";
import type { LiveShipmentPosition } from "../../types/chainbridge";



function getRiskColor(status: string, riskScore: number): string {
  if (status === 'AT_RISK' || riskScore > 0.7) {
    return '#ef4444'; // red
  } else if (status === 'DELAYED' || riskScore > 0.4) {
    return '#f59e0b'; // amber
  } else {
    return '#10b981'; // emerald
  }
}





function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

interface ShipmentTooltipProps {
  shipment: LiveShipmentPosition;
}

function ShipmentTooltip({ shipment }: ShipmentTooltipProps): JSX.Element {
  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 w-72 rounded-lg border border-slate-700 bg-slate-900/95 p-3 text-xs shadow-xl backdrop-blur">
      {/* Line 1: Corridor, Mode, Value */}
      <p className="font-semibold text-slate-100">
        {shipment.corridor} · {shipment.mode} · {formatCurrency(shipment.cargoValueUsd)}
      </p>

      {/* Line 2: Financing & Payment */}
      <p className="mt-1 text-slate-300">
        Financed: {formatCurrency(shipment.financedAmountUsd)} · Paid: {formatCurrency(shipment.paidAmountUsd)}
        {(() => {
          const settlementState = shipment.settlement_state ?? shipment.settlementState ?? 'UNKNOWN';
          const colorClass =
            settlementState === 'PAID' ? 'text-emerald-400' :
            settlementState === 'PARTIALLY_PAID' ? 'text-purple-400' :
            settlementState === 'FINANCED_UNPAID' ? 'text-blue-400' :
            'text-slate-400';
          return (
            <span className={`ml-2 font-medium ${colorClass}`}>
              ({settlementState.replace('_', ' ')})
            </span>
          );
        })()}
      </p>

      {/* Line 3: Risk & Last Event */}
      <p className="mt-1 text-slate-300">
        Risk: {Math.round(shipment.riskScore * 100)}%
        <span className={`ml-1 font-medium ${getRiskColor(shipment.status, shipment.riskScore) === '#ef4444' ? 'text-red-400' : getRiskColor(shipment.status, shipment.riskScore) === '#f59e0b' ? 'text-amber-400' : 'text-emerald-400'}`}>
          ({shipment.status.replace('_', ' ')})
        </span>
        · Last: {(shipment.last_event_code ?? shipment.lastEventCode ?? 'UNKNOWN').replace('_', ' ')}
      </p>

      {/* Line 4: Location & ETA */}
      <p className="mt-1 text-slate-300">
        Near: {shipment.destPort_name || 'Unknown'} ({(shipment.distance_to_nearest_port_km ?? shipment.distanceToNearestPortKm ?? 0)}km)
        {shipment.eta && (
          <span className="ml-2">
            · ETA: {new Date(shipment.eta).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </p>
    </div>
  );
}

function MapBasemap(): JSX.Element {
  const latLines = [40, 70, 100, 130, 160];
  const longLines = [30, 70, 110, 150, 190, 230, 270, 310];

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 to-slate-900 opacity-90" />
      <svg
        viewBox="0 0 360 220"
        className="absolute inset-0 h-full w-full opacity-40"
        preserveAspectRatio="xMidYMid meet"
      >
        <g stroke="rgba(148,163,184,0.35)" strokeWidth={0.5} fill="none">
          {latLines.map((y) => (
            <ellipse key={`lat-${y}`} cx="180" cy="110" rx="160" ry={y} />
          ))}
          {longLines.map((x) => (
            <path key={`lon-${x}`} d={`M${x} 0C${x} 110 ${x} 110 ${x} 220`} />
          ))}
        </g>
        <g fill="rgba(56,189,248,0.15)">
          <ellipse cx="120" cy="90" rx="70" ry="28" />
          <ellipse cx="250" cy="80" rx="60" ry="24" />
          <ellipse cx="180" cy="140" rx="110" ry="35" />
        </g>
        <g fill="rgba(14,165,233,0.08)">
          <ellipse cx="50" cy="130" rx="45" ry="18" />
          <ellipse cx="230" cy="35" rx="55" ry="20" />
          <ellipse cx="300" cy="170" rx="35" ry="15" />
        </g>
      </svg>
    </div>
  );
}

export default function IntelMapPanel(): JSX.Element {
  const { data: liveShipments, isLoading } = useLiveShipmentPositions();

  return (
    <div className="rounded-xl border border-slate-800/70 bg-gradient-to-br from-slate-900/90 via-slate-950/95 to-slate-900/90 p-6 backdrop-blur">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-100">Global Intelligence Map</h3>
          <p className="mt-1 text-xs text-slate-400">
            Live shipment tracking with money and settlement awareness
          </p>
        </div>

        {/* LIVE Badge */}
        <div className="flex items-center gap-2 rounded-full border border-emerald-500/50 bg-emerald-500/10 px-3 py-1">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
            LIVE
          </span>
        </div>
      </div>

      {/* Map Visualization */}
      <div className="relative flex h-96 items-center justify-center rounded-lg border border-slate-800/50 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 overflow-hidden">
        {/* Stylish basemap with grid and continents */}
        <MapBasemap />

        {/* Loading State */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 text-slate-400">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-400"></div>
              <span className="text-sm">Loading live positions...</span>
            </div>
          </div>
        )}

        {/* Live Shipment Markers */}
        {liveShipments?.map((shipment, index) => {
          const isAtRisk = shipment.status === 'AT_RISK' || shipment.riskScore > 0.7;
          const isDelayed = shipment.status === 'DELAYED' || shipment.riskScore > 0.4;
          const isOcean = shipment.mode === 'OCEAN';
          const isAir = shipment.mode === 'AIR';
          const isRail = shipment.mode === 'RAIL';

          // Predefined positions for demo markers based on corridors
          const positions = [
            'left-[15%] top-[60%]', // US-MX (San Diego area)
            'left-[52%] top-[25%]', // EU-US (Rotterdam)
            'left-[80%] top-[55%]', // APAC-US (Singapore)
            'left-[20%] top-[20%]', // US-CAN (Vancouver)
            'left-[45%] top-[40%]', // US-DOMESTIC (Chicago)
          ];
          const positionClass = positions[index % positions.length];

          return (
            <div
              key={shipment.shipmentId}
              className={`absolute group ${positionClass}`}
            >
              {/* Settlement Ring */}
              <div className={`absolute -left-1 -top-1 rounded-full border-2 opacity-80 ${
                isOcean ? 'w-5 h-5' : isAir ? 'w-4 h-4' : isRail ? 'w-4.5 h-4.5' : 'w-3.5 h-3.5'
              } ${
                shipment.settlement_state === 'FINANCED_UNPAID' ? 'border-blue-400' :
                shipment.settlement_state === 'PARTIALLY_PAID' ? 'border-purple-400' :
                shipment.settlement_state === 'PAID' ? 'border-slate-300' :
                'border-slate-600'
              }`} />

              {/* Risk/Status Marker */}
              <div className={`relative flex items-center justify-center rounded-full border-2 ${
                isOcean ? 'w-4 h-4' : isAir ? 'w-3 h-3' : isRail ? 'w-3.5 h-3.5' : 'w-2.5 h-2.5'
              } ${
                isAtRisk ? 'border-red-500 bg-red-500/30' :
                isDelayed ? 'border-amber-400 bg-amber-400/30' :
                'border-emerald-500 bg-emerald-500/30'
              }`}>
                <div className={`rounded-full ${
                  isOcean ? 'w-2 h-2' : isAir ? 'w-1.5 h-1.5' : isRail ? 'w-1.5 h-1.5' : 'w-1 h-1'
                } ${
                  isAtRisk ? 'bg-red-500' :
                  isDelayed ? 'bg-amber-400' :
                  'bg-emerald-500'
                }`} />
              </div>

              {/* Tooltip on Hover */}
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
                <ShipmentTooltip shipment={shipment} />
              </div>
            </div>
          );
        })}

        {/* Center Globe Icon (background) */}
        <Globe className="h-32 w-32 text-slate-800/30" />
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-end gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <Circle className="h-3 w-3 fill-emerald-500 text-emerald-500" />
          <span className="text-slate-400">On Time</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Circle className="h-3 w-3 fill-amber-400 text-amber-400" />
          <span className="text-slate-400">Delayed</span>
        </div>
        <div className="flex items-center gap-1.5">
          <AlertTriangle className="h-3 w-3 text-red-400" />
          <span className="text-slate-400">At Risk</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="h-3 w-3 rounded-full border border-purple-400 bg-purple-400/20" />
          <span className="text-slate-400">Partially Paid</span>
        </div>
      </div>

      {/* Statistics */}
      <div className="mt-3 text-[10px] text-slate-500">
        {liveShipments && (
          <span>
            Tracking {liveShipments.length} active shipments ·
            {formatCurrency(liveShipments.reduce((sum: number, s: LiveShipmentPosition) => sum + s.cargoValueUsd, 0))} total value
          </span>
        )}
      </div>
    </div>
  );
}
