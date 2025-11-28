import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  Shield,
  Ship,
} from "lucide-react";
import { useMemo } from "react";
import type { KeyboardEvent } from "react";

import { MOCK_SHIPMENTS } from "../lib/mockData";
import type { Shipment } from "../lib/types";
import type { CorridorId } from "../utils/corridors";
import { classifyCorridor } from "../utils/corridors";

export type { CorridorId } from "../utils/corridors";
export { classifyCorridor } from "../utils/corridors";

export interface CorridorStats {
  id: CorridorId;
  label: string;
  shipments: Shipment[];
  shipmentCount: number;
  activeCount: number;
  highRiskCount: number;
  blockedPayments: number;
  avgRisk: number;
}

type CorridorAccumulator = CorridorStats & { riskSum: number };

export type RiskTrendDirection = "up" | "flat" | "down";

export interface RiskTrendInsight {
  direction: RiskTrendDirection;
  label: "Rising" | "Stable" | "Improving";
  delta: number;
  series: number[];
}

export function buildCorridorStats(shipments: Shipment[]): CorridorStats[] {
  const map = new Map<CorridorId, CorridorAccumulator>();

  for (const shipment of shipments) {
    const { id, label } = classifyCorridor(shipment);
    const riskScore = shipment.risk.score ?? 0;
    const active = shipment.status !== "completed";
    const isHighRisk = shipment.risk.category === "high";
    const isPaymentBlocked = shipment.payment.state === "blocked";

    const existing = map.get(id);

    if (!existing) {
      map.set(id, {
        id,
        label,
        shipments: [shipment],
        shipmentCount: 1,
        activeCount: active ? 1 : 0,
        highRiskCount: isHighRisk ? 1 : 0,
        blockedPayments: isPaymentBlocked ? 1 : 0,
        avgRisk: riskScore,
        riskSum: riskScore,
      });
      continue;
    }

    existing.shipments.push(shipment);
    existing.shipmentCount += 1;
    if (active) existing.activeCount += 1;
    if (isHighRisk) existing.highRiskCount += 1;
    if (isPaymentBlocked) existing.blockedPayments += 1;
    existing.riskSum += riskScore;
    existing.avgRisk = Math.round(existing.riskSum / existing.shipmentCount);
  }

  return Array.from(map.values())
    .map(({ riskSum: _riskSum, ...corridor }) => corridor)
    .sort((a, b) => b.avgRisk - a.avgRisk);
}

export interface CorridorIntelPanelProps {
  onSelectCorridor?: (corridorId: CorridorId) => void;
}

interface CorridorCardData extends CorridorStats {
  trend: RiskTrendInsight;
}

export function CorridorIntelPanel({ onSelectCorridor }: CorridorIntelPanelProps) {
  const corridors = useMemo<CorridorCardData[]>(() => {
    return buildCorridorStats(MOCK_SHIPMENTS).map((corridor) => {
      const series = generateMockTrendForCorridor(corridor.id, corridor.avgRisk);
      const trend = classifyTrendFromSeries(series);
      return { ...corridor, trend };
    });
  }, []);

  if (corridors.length === 0) {
    return null;
  }

  return (
    <section className="mt-4 space-y-3 rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
            Corridor Intel
          </p>
          <p className="mt-1 text-sm text-slate-300">
            Lane-level view of risk, flow, and payment friction.
          </p>
        </div>
        <Ship className="h-5 w-5 text-slate-400" />
      </div>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {corridors.map((corridor) => (
          <CorridorCard key={corridor.id} corridor={corridor} onSelect={onSelectCorridor} />
        ))}
      </div>
    </section>
  );
}

function CorridorCard({
  corridor,
  onSelect,
}: {
  corridor: CorridorCardData;
  onSelect?: (corridorId: CorridorId) => void;
}) {
  const tone = corridor.avgRisk >= 70 ? "bad" : corridor.avgRisk >= 40 ? "warn" : "good";
  const clickable = Boolean(onSelect);

  let borderColor = "border-emerald-500/30";
  let glow = "shadow-[0_0_24px_rgba(16,185,129,0.2)]";
  let riskColor = "text-emerald-400";

  if (tone === "warn") {
    borderColor = "border-amber-500/30";
    glow = "shadow-[0_0_24px_rgba(245,158,11,0.22)]";
    riskColor = "text-amber-300";
  } else if (tone === "bad") {
    borderColor = "border-red-500/40";
    glow = "shadow-[0_0_28px_rgba(239,68,68,0.26)]";
    riskColor = "text-red-400";
  }

  const trendTone =
    corridor.trend.direction === "up"
      ? "text-red-300"
      : corridor.trend.direction === "down"
        ? "text-emerald-300"
        : "text-slate-400";

  const trendIcon = (() => {
    if (corridor.trend.direction === "up") {
      return <ArrowUpRight className="h-3 w-3 text-red-300" />;
    }
    if (corridor.trend.direction === "down") {
      return <ArrowDownRight className="h-3 w-3 text-emerald-300" />;
    }
    return <Minus className="h-3 w-3 text-slate-400" />;
  })();

  const handleClick = () => {
    onSelect?.(corridor.id);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!onSelect) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(corridor.id);
    }
  };

  const interactiveProps = clickable
    ? {
        role: "button" as const,
        tabIndex: 0,
        onClick: handleClick,
        onKeyDown: handleKeyDown,
      }
    : {
        tabIndex: -1,
      };

  return (
    <div
      {...interactiveProps}
      className={`flex flex-col justify-between rounded-xl border bg-slate-900/70 p-3 transition ${
        clickable ? "cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-400" : ""
      } hover:border-slate-200/60 hover:bg-slate-900 ${borderColor} ${glow}`}
    >
      <div className="mb-2 flex items-center justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Corridor</p>
          <p className="text-sm font-semibold text-slate-100">{corridor.label}</p>
        </div>
        <div className="flex flex-col items-end text-[10px] text-slate-500">
          <span>Shipments: {corridor.shipmentCount}</span>
          <span>Active: {corridor.activeCount}</span>
        </div>
      </div>

      <div className="mt-1 grid grid-cols-2 gap-2 text-[11px]">
        <div className="flex flex-col">
          <span className="text-slate-500">Avg Risk</span>
          <span className={`text-sm font-semibold ${riskColor}`}>{corridor.avgRisk || 0}</span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-slate-500">High Risk</span>
          <span className="text-sm font-semibold text-slate-100">{corridor.highRiskCount}</span>
        </div>
        <div className="flex items-center gap-1 text-slate-400">
          <AlertTriangle className="h-3 w-3 text-amber-300" />
          <span>Blocked payments: {corridor.blockedPayments}</span>
        </div>
        <div className="flex items-center justify-end gap-1 text-slate-400">
          <Shield className="h-3 w-3 text-slate-300" />
          <span>Coverage lanes: 1</span>
        </div>
      </div>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-300">
          <span className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Trend</span>
            <span className={`flex items-center gap-1 font-mono ${trendTone}`}>
              {trendIcon}
              {corridor.trend.label}
              {Math.abs(corridor.trend.delta) > 0 && (
                <span className="text-slate-400">Δ{Math.abs(corridor.trend.delta)}</span>
              )}
            </span>
          </span>
          <ArrowUpRight className="h-3 w-3 text-slate-400" />
        </div>

        <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500">
          <span>
            Intel from <span className="font-mono text-slate-300">ChainFreight / ChainIQ / ChainPay</span>
          </span>
          <ArrowUpRight className="h-3 w-3 text-slate-400" />
        </div>
    </div>
  );
}

  const TREND_SERIES_LENGTH = 7;

  export function generateMockTrendForCorridor(corridorId: CorridorId, baseRisk: number): number[] {
    const seed = corridorId.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0) + Math.round(baseRisk || 50);
    const random = createDeterministicRandom(seed);
    const series: number[] = [];
    let current = clamp(baseRisk || 50, 5, 95);

    for (let i = 0; i < TREND_SERIES_LENGTH; i += 1) {
      const drift = (random() - 0.5) * 12; // +/- 6 pts
      current = clamp(current + drift, 1, 99);
      series.push(Math.round(current));
    }

    return series;
  }

  export function classifyTrendFromSeries(series: number[]): RiskTrendInsight {
    if (series.length === 0) {
      return { direction: "flat", label: "Stable", delta: 0, series };
    }

    const first = series[0];
    const last = series[series.length - 1];
    const delta = last - first;

    if (delta > 4) {
      return { direction: "up", label: "Rising", delta, series };
    }

    if (delta < -4) {
      return { direction: "down", label: "Improving", delta, series };
    }

    return { direction: "flat", label: "Stable", delta, series };
  }

  function createDeterministicRandom(seed: number): () => number {
    let value = seed % 2147483647;
    if (value <= 0) value += 2147483646;
    return () => {
      value = (value * 16807) % 2147483647;
      return (value - 1) / 2147483646;
    };
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
  }
