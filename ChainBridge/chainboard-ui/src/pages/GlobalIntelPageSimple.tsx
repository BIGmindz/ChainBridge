import { X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import GlobalIntelMap from '@/components/intel/GlobalIntelMap';
import { ShadowIntelligencePanel } from '@/components/intel/ShadowIntelligencePanel';
import { useLiveShipmentPositions } from '@/hooks/useLiveShipmentPositions';
import { formatPct, formatUsd } from '@/lib/intelStats';
import type { RiskLevel } from '@/types/chainbridge';
import type { IntelShipmentPoint } from '@/types/intel';

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);

type RiskFilter = 'ALL' | RiskLevel;

const normalizeStatus = (status: string): IntelShipmentPoint["status"] => {
  const normalized = (status ?? "").toUpperCase();
  if (normalized === 'DELAYED') return 'DELAYED';
  if (normalized === 'AT_RISK' || normalized === 'AT RISK') return 'AT_RISK';
  if (normalized === 'ON_TIME' || normalized === 'ON TIME') return 'ON_TIME';
  return undefined;
};

function filterIntelPositions(
  positions: IntelShipmentPoint[],
  filters: {
    riskFilter: RiskFilter;
    corridorFilter: string;
  },
): IntelShipmentPoint[] {
  return positions.filter((p) => {
    // Risk filter
    if (filters.riskFilter !== 'ALL' && p.riskCategory !== filters.riskFilter) {
      return false;
    }

    // Corridor filter
    if (
      filters.corridorFilter !== 'ALL' &&
      p.corridorId !== filters.corridorFilter &&
      p.corridorLabel !== filters.corridorFilter
    ) {
      return false;
    }

    return true;
  });
}

export default function GlobalIntelPageSimple() {
  const { data: liveShipments = [], isLoading } = useLiveShipmentPositions();
  const [selectedShipment, setSelectedShipment] = useState<IntelShipmentPoint | null>(null);

  // Filter state
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('ALL');
  const [corridorFilter, setCorridorFilter] = useState<string>('ALL');

  // Transform to IntelShipmentPoint
  const allShipments = useMemo(
    () =>
      liveShipments.map((shipment) => ({
        id: shipment.shipmentId,
        lat: shipment.lat,
        lon: shipment.lon,
        corridorId: shipment.corridor,
        corridorLabel: shipment.corridor,
        laneLabel: shipment.destPortName ?? shipment.originPortName ?? shipment.corridor,
        valueUsd: shipment.cargoValueUsd,
        riskScore: Math.min(100, Math.max(0, (shipment.riskScore ?? 0) * 100)),
        riskCategory: shipment.riskCategory,
        status: normalizeStatus(shipment.status),
        stakeApr: shipment.stakeApr ?? 0,
        stakeCapacityUsd: shipment.stakeCapacityUsd ?? 0,
      })),
    [liveShipments],
  );

  // Filtered shipments
  const filteredShipments = useMemo(
    () => filterIntelPositions(allShipments, { riskFilter, corridorFilter }),
    [allShipments, riskFilter, corridorFilter],
  );

  // KPIs from filtered data
  const totalValue = useMemo(
    () => filteredShipments.reduce((sum, shipment) => sum + shipment.valueUsd, 0),
    [filteredShipments],
  );

  const financedValue = useMemo(
    () => filteredShipments.reduce((sum, shipment) => sum + (shipment.stakeCapacityUsd ?? 0), 0),
    [filteredShipments],
  );

  const atRiskValue = useMemo(
    () =>
      filteredShipments.reduce((sum, shipment) => {
        const isAtRisk = shipment.riskCategory === 'HIGH' || shipment.riskCategory === 'CRITICAL';
        return isAtRisk ? sum + shipment.valueUsd : sum;
      }, 0),
    [filteredShipments],
  );

  const topCorridorByValue = useMemo(() => {
    const corridorMap = new Map<string, number>();
    filteredShipments.forEach((shipment) => {
      const corridor = shipment.corridorLabel || shipment.corridorId || 'UNKNOWN';
      corridorMap.set(corridor, (corridorMap.get(corridor) || 0) + shipment.valueUsd);
    });
    const entries = Array.from(corridorMap.entries()).sort((a, b) => b[1] - a[1]);
    return entries.length > 0 ? entries[0] : null;
  }, [filteredShipments]);

  // Unique corridors for filter
  const uniqueCorridors = useMemo(() => {
    const corridors = new Set<string>();
    allShipments.forEach((s) => {
      const corridor = s.corridorLabel || s.corridorId || 'UNKNOWN';
      corridors.add(corridor);
    });
    return Array.from(corridors).sort();
  }, [allShipments]);

  const financedPct = totalValue > 0 ? (financedValue / totalValue) * 100 : 0;
  const atRiskPct = totalValue > 0 ? (atRiskValue / totalValue) * 100 : 0;

  // Close drawer on ESC
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedShipment(null);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  const handleSelectShipment = useCallback((shipment: IntelShipmentPoint) => {
    setSelectedShipment(shipment);
  }, []);

  return (
    <div className="relative space-y-6 px-6 py-8">
      <header className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-500">
          Global Intelligence
        </p>
        <h1 className="text-4xl font-semibold text-slate-900">Risk + Yield Radar</h1>
        <p className="max-w-3xl text-base text-slate-600">
          Live shipment telemetry, corridor KPIs, and ChainIQ risk scoring across every trading
          lane.
        </p>
      </header>

      {/* KPI Strip */}
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total Freight Value
          </p>
          <p className="mt-2 text-2xl font-bold text-slate-900">{formatUsd(totalValue)}</p>
          <p className="text-xs text-slate-600">All active shipments</p>
        </div>

        <div className="rounded-xl border border-emerald-300 bg-gradient-to-br from-emerald-50 to-emerald-100 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
            Financed Coverage
          </p>
          <p className="mt-2 text-2xl font-bold text-emerald-900">{formatPct(financedPct)}</p>
          <p className="text-xs text-emerald-700">Financed vs total value</p>
        </div>

        <div className="rounded-xl border border-red-300 bg-gradient-to-br from-red-50 to-red-100 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-red-700">
            At-Risk Exposure
          </p>
          <p className="mt-2 text-2xl font-bold text-red-900">{formatPct(atRiskPct)}</p>
          <p className="text-xs text-red-700">Value in HIGH/CRITICAL buckets</p>
        </div>

        <div className="rounded-xl border border-indigo-300 bg-gradient-to-br from-indigo-50 to-indigo-100 p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Top Corridor by Value
          </p>
          <p className="mt-2 text-lg font-bold text-indigo-900">
            {topCorridorByValue ? topCorridorByValue[0] : 'N/A'}
          </p>
          <p className="text-xs text-indigo-700">
            {topCorridorByValue ? formatUsd(topCorridorByValue[1]) : '—'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Risk:
          </span>
          {(['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const).map((risk) => (
            <button
              key={risk}
              type="button"
              onClick={() => setRiskFilter(risk)}
              className={`rounded-lg border px-3 py-1 text-xs font-medium transition-colors ${
                riskFilter === risk
                  ? 'border-emerald-600 bg-emerald-500 text-white'
                  : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'
              }`}
            >
              {risk}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            Corridor:
          </span>
          <select
            value={corridorFilter}
            onChange={(e) => setCorridorFilter(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50"
            aria-label="Select corridor filter"
          >
            <option value="ALL">All</option>
            {uniqueCorridors.map((corridor) => (
              <option key={corridor} value={corridor}>
                {corridor}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Map */}
      <GlobalIntelMap
        points={filteredShipments}
        isLoading={isLoading}
        onSelectShipment={handleSelectShipment}
      />

      {/* Shadow Intelligence Panel - Compact Mode */}
      <ShadowIntelligencePanel compact />

      {/* Detail Drawer */}
      {selectedShipment && (
        <>
          {/* Overlay */}
          <div
            className="fixed inset-0 z-40 bg-black/40"
            onClick={() => setSelectedShipment(null)}
          />

          {/* Drawer */}
          <div className="fixed bottom-0 right-0 top-0 z-50 w-full overflow-y-auto bg-white shadow-2xl md:w-96">
            <div className="space-y-6 p-6">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{selectedShipment.id}</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    {selectedShipment.corridorLabel || selectedShipment.corridorId}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedShipment(null)}
                  className="text-slate-400 transition-colors hover:text-slate-600"
                  aria-label="Close detail drawer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Value & Risk */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Value & Risk
                </h3>
                <div className="space-y-2 rounded-lg bg-slate-50 p-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">Cargo Value</span>
                    <span className="font-mono text-sm font-semibold text-slate-900">
                      {formatCurrency(selectedShipment.valueUsd)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">Risk Score</span>
                    <span className="font-mono text-sm font-semibold text-slate-900">
                      {selectedShipment.riskScore.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-600">Risk Bucket</span>
                    <span
                      className={`rounded px-2 py-1 text-xs font-semibold ${
                        selectedShipment.riskCategory === 'CRITICAL'
                          ? 'bg-red-100 text-red-800'
                          : selectedShipment.riskCategory === 'HIGH'
                            ? 'bg-orange-100 text-orange-800'
                            : selectedShipment.riskCategory === 'MEDIUM'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {selectedShipment.riskCategory || 'UNKNOWN'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Finance */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Financing
                </h3>
                <div className="space-y-2 rounded-lg bg-slate-50 p-4">
                  {(selectedShipment.stakeCapacityUsd ?? 0) > 0 ? (
                    <>
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-emerald-500" />
                        <span className="text-sm font-semibold text-emerald-800">
                          ChainPay Pipeline: Active
                        </span>
                      </div>
                      <div className="mt-2 flex justify-between">
                        <span className="text-sm text-slate-600">Stake Capacity</span>
                        <span className="font-mono text-sm font-semibold text-slate-900">
                          {formatCurrency(selectedShipment.stakeCapacityUsd ?? 0)}
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-slate-400" />
                      <span className="text-sm font-medium text-slate-600">
                        Opportunity to finance
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Location */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Location
                </h3>
                <div className="space-y-2 rounded-lg bg-slate-50 p-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-600">Coordinates</span>
                    <span className="font-mono text-sm text-slate-900">
                      {selectedShipment.lat.toFixed(4)}, {selectedShipment.lon.toFixed(4)}
                    </span>
                  </div>
                  {selectedShipment.laneLabel && (
                    <div className="flex justify-between">
                      <span className="text-sm text-slate-600">Lane</span>
                      <span className="text-sm text-slate-900">{selectedShipment.laneLabel}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* CTA */}
              <a
                href={`/operator-console?shipmentId=${encodeURIComponent(selectedShipment.id)}`}
                className="block w-full rounded-lg bg-indigo-600 px-4 py-3 text-center font-semibold text-white transition-colors hover:bg-indigo-700"
              >
                Open in Operator Console
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
