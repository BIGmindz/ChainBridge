import {
  AlertTriangle,
  Clock,
  DollarSign,
  ShieldAlert,
  Truck,
} from "lucide-react";
import { useMemo } from "react";
import type { ReactNode } from "react";

import { MOCK_SHIPMENTS } from "../lib/mockData";
import type { Shipment } from "../lib/types";

type ExceptionType = "risk" | "payment" | "eta";

interface ExceptionItem {
  shipment: Shipment;
  type: ExceptionType;
  priority: number;
  reason: string;
}

const EXCEPTION_TYPES: ExceptionType[] = ["risk", "payment", "eta"];

const TYPE_META: Record<ExceptionType, { label: string; accent: string; icon: ReactNode }> = {
  payment: {
    label: "Payment Intelligence",
    accent: "text-amber-300",
    icon: <DollarSign className="h-4 w-4 text-amber-300" />,
  },
  risk: {
    label: "Risk Escalations",
    accent: "text-red-300",
    icon: <AlertTriangle className="h-4 w-4 text-red-300" />,
  },
  eta: {
    label: "ETA Pressure",
    accent: "text-sky-300",
    icon: <Clock className="h-4 w-4 text-sky-300" />,
  },
};

export default function ExceptionsPage() {
  const { exceptions, stats, critical, grouped } = useMemo(() => {
    const items: ExceptionItem[] = [];

    for (const shipment of MOCK_SHIPMENTS) {
      // Payment-based exceptions
      if (
        shipment.payment.state === "blocked" ||
        shipment.payment.state === "partially_paid"
      ) {
        items.push({
          shipment,
          type: "payment",
          priority: computeExceptionPriority(shipment, "payment"),
          reason:
            shipment.payment.state === "blocked"
              ? "Payment blocked at ChainPay"
              : "Payment partially released; remaining balance at risk",
        });
      }

      // Risk-based exceptions
      if (
        shipment.risk.category === "high" ||
        shipment.risk.category === "medium"
      ) {
        items.push({
          shipment,
          type: "risk",
          priority: computeExceptionPriority(shipment, "risk"),
          reason:
            shipment.risk.category === "high"
              ? "High ChainIQ risk score"
              : "Elevated ChainIQ risk score",
        });
      }

      // ETA / status exceptions
      if (shipment.status === "delayed" || shipment.status === "blocked") {
        items.push({
          shipment,
          type: "eta",
          priority: computeExceptionPriority(shipment, "eta"),
          reason:
            shipment.status === "blocked"
              ? "Movement blocked; investigate corridor"
              : "ETA slippage detected",
        });
      }
    }

    const unique = dedupeExceptions(items);

    const stats = computeStats(unique);
    const critical = [...unique]
      .sort((a, b) => {
        if (b.priority !== a.priority) return b.priority - a.priority;
        return (b.shipment.risk.score ?? 0) - (a.shipment.risk.score ?? 0);
      })
      .slice(0, 3);

    const grouped = unique.reduce<Record<ExceptionType, ExceptionItem[]>>(
      (acc, item) => {
        acc[item.type].push(item);
        return acc;
      },
      { payment: [], risk: [], eta: [] },
    );

    for (const type of EXCEPTION_TYPES) {
      grouped[type].sort((a, b) => b.priority - a.priority);
    }

    return {
      exceptions: unique,
      stats,
      critical,
      grouped,
    };
  }, []);

  return (
    <div className="flex flex-col gap-4 text-slate-100 lg:flex-row">
      {/* Left: Critical Triage */}
      <section className="w-full space-y-3 rounded-2xl border border-red-500/40 bg-slate-950/80 p-4 shadow-[0_0_40px_rgba(239,68,68,0.12)] lg:w-1/3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-red-400">
              Critical Triage
            </p>
            <h1 className="mt-1 text-sm font-semibold text-slate-50">
              Highest-impact exceptions right now
            </h1>
          </div>
          <ShieldAlert className="h-5 w-5 text-red-400" />
        </div>

        {critical.length === 0 ? (
          <p className="mt-3 text-xs text-slate-400">
            No critical exceptions detected. Network in acceptable range.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {critical.map((exception) => (
              <li
                key={`${exception.shipment.id}-${exception.type}`}
                className="group rounded-xl border border-red-500/40 bg-gradient-to-br from-red-950/60 via-slate-950/80 to-slate-950/30 p-3 transition hover:border-red-400 hover:bg-red-950/70"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="space-y-1">
                    <p className="font-mono text-[11px] text-slate-100">
                      {exception.shipment.reference}
                    </p>
                    <p className="text-[11px] text-slate-300">
                      {exception.shipment.origin} → {exception.shipment.destination}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold text-slate-50">
                      {exception.shipment.risk.score}
                    </p>
                    <p className="text-[10px] text-slate-400">ChainIQ</p>
                  </div>
                </div>
                <p className="mt-2 text-[11px] text-red-100">{exception.reason}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px]">
                  <ExceptionTypePill type={exception.type} />
                  <span className="rounded-full bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                    Status: {exception.shipment.status}
                  </span>
                  <span className="rounded-full bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                    Payment: {exception.shipment.payment.state}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Right: Summary + Exception Grid */}
      <div className="flex w-full flex-col gap-4 lg:w-2/3">
        {/* Summary strip */}
        <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 shadow-[0_10px_25px_rgba(15,23,42,0.4)]">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
                Exceptions Command Center
              </p>
              <p className="mt-1 text-sm text-slate-300">
                Aggregated view of risk, payment, and ETA anomalies.
              </p>
            </div>
            <AlertTriangle className="h-5 w-5 text-amber-400" />
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <SummaryStat
              label="Open Exceptions"
              value={stats.totalExceptions}
              tone={stats.totalExceptions > 0 ? "warn" : "good"}
            />
            <SummaryStat
              label="Blocked Payments"
              value={stats.totalBlockedPayments}
              tone={stats.totalBlockedPayments > 0 ? "bad" : "good"}
              icon={<DollarSign className="h-3 w-3" />}
            />
            <SummaryStat
              label="High-Risk Shipments"
              value={stats.highRiskCount}
              tone={stats.highRiskCount > 0 ? "warn" : "good"}
              icon={<Truck className="h-3 w-3" />}
            />
            <SummaryStat
              label="Avg Exception Risk"
              value={`${stats.avgRisk}`}
              tone={stats.avgRisk >= 70 ? "bad" : stats.avgRisk >= 40 ? "warn" : "good"}
            />
          </div>
        </section>

        {/* Exception Grid */}
        <section className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Exception Inventory
            </p>
            <p className="text-[11px] text-slate-500">Grouped by Driver · Risk · Payment · ETA</p>
          </div>

          {exceptions.length === 0 ? (
            <p className="text-xs text-slate-400">
              No exception inventory to display. All monitored legs within configured tolerances.
            </p>
          ) : (
            <div className="grid gap-3 md:grid-cols-3">
              {EXCEPTION_TYPES.map((type) => (
                <ExceptionGroup key={type} type={type} items={grouped[type]} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function ExceptionGroup({ type, items }: { type: ExceptionType; items: ExceptionItem[] }) {
  const meta = TYPE_META[type];

  return (
    <div className="rounded-2xl border border-slate-900 bg-slate-900/70 p-3">
      <div className="mb-2 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-2">
          {meta.icon}
          <span className={`${meta.accent} font-semibold tracking-[0.16em] uppercase`}>
            {meta.label}
          </span>
        </div>
        <span className="font-mono text-slate-400">{items.length} cases</span>
      </div>

      {items.length === 0 ? (
        <p className="text-[11px] text-slate-500">Nominal · No watchlisted shipments.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <ExceptionCard key={`${item.shipment.id}-${item.type}`} exception={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function ExceptionTypePill({ type }: { type: ExceptionType }) {
  const base =
    "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em]";

  if (type === "payment") {
    return (
      <span className={`${base} border-amber-500/40 bg-amber-500/10 text-amber-300`}>
        <DollarSign className="h-3 w-3" />
        Payment
      </span>
    );
  }
  if (type === "eta") {
    return (
      <span className={`${base} border-sky-500/40 bg-sky-500/10 text-sky-300`}>
        <Clock className="h-3 w-3" />
        ETA
      </span>
    );
  }
  return (
    <span className={`${base} border-red-500/40 bg-red-500/10 text-red-300`}>
      <AlertTriangle className="h-3 w-3" />
      Risk
    </span>
  );
}

function SummaryStat({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number | string;
  tone: "good" | "warn" | "bad";
  icon?: ReactNode;
}) {
  let color = "text-slate-100";
  if (tone === "good") color = "text-emerald-400";
  if (tone === "warn") color = "text-amber-300";
  if (tone === "bad") color = "text-red-400";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-3">
      <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <div className="mt-2 flex items-center gap-2">
        {icon}
        <p className={`text-lg font-semibold ${color}`}>{value}</p>
      </div>
    </div>
  );
}

function ExceptionCard({ exception }: { exception: ExceptionItem }) {
  const { shipment, type, reason } = exception;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 transition hover:border-slate-500 hover:bg-slate-900">
      <div className="flex items-center justify-between gap-2">
        <div className="space-y-0.5">
          <p className="font-mono text-[11px] text-slate-100">{shipment.reference}</p>
          <p className="text-[11px] text-slate-400">
            {shipment.origin} → {shipment.destination}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-semibold text-slate-50">{shipment.risk.score}</p>
          <p className="text-[10px] text-slate-500">ChainIQ</p>
        </div>
      </div>
      <p className="text-[11px] text-slate-300">{reason}</p>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px]">
        <ExceptionTypePill type={type} />
        <span className="rounded-full bg-slate-950 px-2 py-0.5 text-slate-300">
          Status: {shipment.status}
        </span>
        <span className="rounded-full bg-slate-950 px-2 py-0.5 text-slate-300">
          Payment: {shipment.payment.state}
        </span>
      </div>
    </div>
  );
}

function computeExceptionPriority(shipment: Shipment, type: ExceptionType): number {
  if (type === "payment") {
    if (shipment.payment.state === "blocked") return 100;
    if (shipment.payment.state === "partially_paid") return 80;
  }

  if (type === "risk") {
    if (shipment.risk.category === "high" && shipment.status === "in_transit") {
      return 90;
    }
    if (shipment.risk.category === "high") {
      return 75;
    }
    if (shipment.risk.category === "medium") {
      return 60;
    }
  }

  if (type === "eta") {
    if (shipment.status === "delayed" && shipment.risk.category === "high") {
      return 80;
    }
    if (shipment.status === "blocked") {
      return 75;
    }
    if (shipment.status === "delayed") {
      return 65;
    }
  }

  return 40;
}

function dedupeExceptions(items: ExceptionItem[]): ExceptionItem[] {
  const map = new Map<string, ExceptionItem>();
  for (const item of items) {
    const key = `${item.shipment.id}:${item.type}`;
    const existing = map.get(key);
    if (!existing || item.priority > existing.priority) {
      map.set(key, item);
    }
  }
  return Array.from(map.values());
}

function computeStats(items: ExceptionItem[]) {
  const totalExceptions = items.length;
  const totalBlockedPayments = items.filter(
    (item) => item.type === "payment" && item.shipment.payment.state === "blocked",
  ).length;
  const highRiskCount = items.filter(
    (item) => item.type === "risk" && item.shipment.risk.category === "high",
  ).length;
  const avgRisk =
    items.length > 0
      ? Math.round(items.reduce((sum, item) => sum + (item.shipment.risk.score ?? 0), 0) / items.length)
      : 0;

  return {
    totalExceptions,
    totalBlockedPayments,
    highRiskCount,
    avgRisk,
  };
}
