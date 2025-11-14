import { useMemo } from "react";
import { AlertTriangle, ArrowUpRight, Shield, Ship } from "lucide-react";
import { MOCK_SHIPMENTS } from "../lib/mockData";
import type { Shipment } from "../lib/types";

export type CorridorId = "asia-us-west" | "eu-us-east" | "intra-us" | "other";

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

type CorridorClassification = { id: CorridorId; label: string };

export function classifyCorridor(shipment: Shipment): CorridorClassification {
  const origin = shipment.origin.toLowerCase();
  const destination = shipment.destination.toLowerCase();

  const isAsia =
    origin.includes("shanghai") ||
    origin.includes("singapore") ||
    origin.includes("cn") ||
    origin.includes("sg");

  const isEU =
    origin.includes("rotterdam") ||
    origin.includes("hamburg") ||
    origin.includes("nl") ||
    origin.includes("de");

  const isUSWest = destination.includes("los angeles") || destination.includes("long beach");
  const isUSEast =
    destination.includes("new york") || destination.includes("houston") || destination.includes("us");

  if (isAsia && isUSWest) {
    return { id: "asia-us-west", label: "Asia → US West" };
  }

  if (isEU && isUSEast) {
    return { id: "eu-us-east", label: "EU → US East" };
  }

  const originUS = origin.includes("us") || origin.includes("houston") || origin.includes("los angeles");
  if (originUS && isUSEast) {
    return { id: "intra-us", label: "Intra-US" };
  }

  return { id: "other", label: "Global / Other" };
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

export function CorridorIntelPanel() {
  const corridors = useMemo(() => buildCorridorStats(MOCK_SHIPMENTS), []);

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
          <CorridorCard key={corridor.id} corridor={corridor} />
        ))}
      </div>
    </section>
  );
}

function CorridorCard({ corridor }: { corridor: CorridorStats }) {
  const tone = corridor.avgRisk >= 70 ? "bad" : corridor.avgRisk >= 40 ? "warn" : "good";

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

  return (
    <div
      className={`flex flex-col justify-between rounded-xl border bg-slate-900/70 p-3 transition hover:border-slate-200/60 hover:bg-slate-900 ${borderColor} ${glow}`}
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

      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
        <span>
          Intel from <span className="font-mono text-slate-300">ChainFreight / ChainIQ / ChainPay</span>
        </span>
        <ArrowUpRight className="h-3 w-3 text-slate-400" />
      </div>
    </div>
  );
}
