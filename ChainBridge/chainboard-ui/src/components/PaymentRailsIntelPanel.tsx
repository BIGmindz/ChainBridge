import { ArrowDownRight, ArrowUpRight, Clock, DollarSign, Activity } from "lucide-react";
import type { ReactNode } from "react";
import {
  getBenchmarkRails,
  MOCK_PAYMENT_RAILS_METRICS,
  type PaymentRailMetrics,
} from "../lib/paymentRails";

export function PaymentRailsIntelPanel() {
  // In v1 we just use mock data. Later this can be upgraded to live API metrics.
  const { swift, blockchain } = getBenchmarkRails();
  const deltas = computeDeltas(swift, blockchain);
  const annualizedSavings = computeAnnualizedSavings(deltas, 10_000);

  return (
    <section className="mt-4 grid gap-4 rounded-2xl border border-slate-800 bg-slate-950/85 px-5 py-4 md:grid-cols-2">
      <div className="space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">Payment Rails Intel</p>
          <h2 className="mt-1 text-sm font-semibold text-slate-100">Bank rails vs blockchain — impact per payment</h2>
          <p className="mt-1 text-xs text-slate-400">
            Modeled comparison using typical cross-border SWIFT behavior vs ChainBridge settlement (tracking {MOCK_PAYMENT_RAILS_METRICS.length} rails).
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <DeltaCard
            icon={<Clock className="h-4 w-4" />}
            label="Time saved"
            primary={`${formatNumber(deltas.hoursSaved)}h`}
            helper="Faster settlement vs SWIFT"
            tone="good"
          />
          <DeltaCard
            icon={<DollarSign className="h-4 w-4" />}
            label="Fee savings"
            primary={`$${formatNumber(deltas.feeSaved, 2)}`}
            helper="Per payment processed"
            tone="good"
          />
          <DeltaCard
            icon={<Activity className="h-4 w-4" />}
            label="Capital unlocked"
            primary={`${formatNumber(deltas.capitalUnlockedHours)}h`}
            helper="Less cash stuck in limbo"
            tone="good"
          />
        </div>

        <p className="mt-2 text-[11px] text-slate-500">
          Example: On 10,000 payments/year, blockchain rails free
          <span className="mx-1 font-mono text-emerald-300">{annualizedSavings.hours.toLocaleString()} hrs</span>
          of working capital and save
          <span className="mx-1 font-mono text-emerald-300">${annualizedSavings.fees.toLocaleString()}</span>
          in direct fees vs SWIFT.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2">
        <RailSnapshotCard title="Traditional rail" subtitle="SWIFT / correspondent banking" rail={swift} tone="bad" />
        <RailSnapshotCard
          title="Blockchain rail"
          subtitle="Always-on crypto settlement"
          rail={blockchain}
          tone="good"
        />
      </div>
    </section>
  );
}

interface Deltas {
  hoursSaved: number;
  feeSaved: number;
  capitalUnlockedHours: number;
}

function computeDeltas(traditional: PaymentRailMetrics, blockchain: PaymentRailMetrics): Deltas {
  return {
    hoursSaved: clampPositive(traditional.avg_settlement_hours - blockchain.avg_settlement_hours),
    feeSaved: clampPositive(traditional.avg_fee_usd - blockchain.avg_fee_usd),
    capitalUnlockedHours: clampPositive(traditional.capital_locked_hours - blockchain.capital_locked_hours),
  };
}

function computeAnnualizedSavings(deltas: Deltas, paymentsPerYear: number) {
  return {
    hours: Math.round(deltas.capitalUnlockedHours * paymentsPerYear),
    fees: Math.round(deltas.feeSaved * paymentsPerYear),
  };
}

function clampPositive(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, value);
}

function formatNumber(value: number, digits = 1): string {
  return value.toFixed(digits);
}

interface DeltaCardProps {
  icon: ReactNode;
  label: string;
  primary: string;
  helper: string;
  tone: "good" | "warn" | "bad";
}

function DeltaCard({ icon, label, primary, helper, tone }: DeltaCardProps) {
  let color = "text-slate-100";
  let border = "border-slate-700";
  let glow = "";

  if (tone === "good") {
    color = "text-emerald-400";
    border = "border-emerald-500/40";
    glow = "shadow-[0_0_32px_rgba(16,185,129,0.28)]";
  } else if (tone === "warn") {
    color = "text-amber-300";
    border = "border-amber-500/40";
    glow = "shadow-[0_0_32px_rgba(245,158,11,0.28)]";
  } else if (tone === "bad") {
    color = "text-red-400";
    border = "border-red-500/40";
    glow = "shadow-[0_0_32px_rgba(239,68,68,0.28)]";
  }

  return (
    <div className={`flex flex-col justify-between rounded-xl border bg-slate-900/70 p-3 ${border} ${glow}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-300">
          {icon}
          <span className="text-[10px] uppercase tracking-[0.18em] text-slate-400">{label}</span>
        </div>
        <ArrowUpRight className="h-3 w-3 text-slate-500" />
      </div>
      <p className={`mt-2 text-lg font-semibold ${color}`}>{primary}</p>
      <p className="mt-1 text-[11px] text-slate-500">{helper}</p>
    </div>
  );
}

interface RailSnapshotCardProps {
  title: string;
  subtitle: string;
  rail: PaymentRailMetrics;
  tone: "good" | "bad";
}

function RailSnapshotCard({ title, subtitle, rail, tone }: RailSnapshotCardProps) {
  const isGood = tone === "good";
  const accent = isGood ? "border-emerald-500/40 bg-emerald-500/5" : "border-red-500/40 bg-red-500/5";
  const labelColor = isGood ? "text-emerald-300" : "text-red-300";
  const Icon = isGood ? ArrowUpRight : ArrowDownRight;

  return (
    <div className={`flex flex-col justify-between rounded-xl border bg-slate-900/80 p-3 ${accent}`}>
      <div className="mb-2 flex items-center justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">{title}</p>
          <p className="text-sm font-semibold text-slate-100">{rail.label}</p>
          <p className="text-[11px] text-slate-500">{subtitle}</p>
        </div>
        <Icon className={`h-4 w-4 ${labelColor}`} />
      </div>

      <dl className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
        <MetricRow label="Avg settlement" value={`${formatNumber(rail.avg_settlement_hours)}h`} />
        <MetricRow label="Fee per payment" value={`$${formatNumber(rail.avg_fee_usd, 2)}`} />
        <MetricRow label="FX spread" value={`${rail.avg_fx_spread_bps.toFixed(0)} bps`} />
        <MetricRow label="Fail/return rate" value={`${rail.fail_rate_bps.toFixed(0)} bps`} />
        <MetricRow label="Capital locked" value={`${formatNumber(rail.capital_locked_hours)}h`} />
        <MetricRow label="Profile" value={rail.description} wide />
      </dl>
    </div>
  );
}

function MetricRow({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  const spanClass = wide ? "col-span-2" : "";
  return (
    <>
      <dt className={`text-[10px] uppercase tracking-[0.16em] text-slate-500 ${spanClass}`}>{label}</dt>
      <dd className={`mt-0.5 font-mono text-slate-200 ${spanClass}`}>{value}</dd>
    </>
  );
}
