import { useMemo, useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MOCK_SHIPMENTS } from "../lib/mockData";
import { CorridorIntelPanel } from "../components/CorridorIntel";
import type { CorridorId } from "../components/CorridorIntel";
import { PaymentRailsIntelPanel } from "../components/PaymentRailsIntel";
import { IoTHealthPanel } from "../components/IoTHealthPanel";
import type { GlobalSummary } from "../lib/metrics";
import { fetchGlobalSummary } from "../services/metricsClient";
import type { Shipment } from "../lib/types";

type Tone = "good" | "warn" | "bad";

const ACTIVE_STATUSES = new Set<Shipment["status"]>(["pickup", "in_transit", "delivery"]);
const EXCEPTION_STATUSES = new Set<Shipment["status"]>(["delayed", "blocked"]);

const toneClasses: Record<Tone, string> = {
  good: "text-emerald-400",
  warn: "text-amber-400",
  bad: "text-red-400",
};

const badgeClasses: Record<Tone, string> = {
  good: "bg-emerald-500/10 text-emerald-300",
  warn: "bg-amber-500/10 text-amber-300",
  bad: "bg-red-500/10 text-red-300",
};

function percentage(part: number, total: number): number {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}

function classifyPaymentHealth(shipments: Shipment[]): { label: string; tone: Tone } {
  const blocked = shipments.filter((s) => s.payment.state === "blocked").length;
  const total = shipments.length || 1;
  const blockedPct = (blocked / total) * 100;

  if (blockedPct >= 20) return { label: "Critical", tone: "bad" };
  if (blockedPct >= 10) return { label: "Degraded", tone: "warn" };
  return { label: "Healthy", tone: "good" };
}

function riskTone(score: number): Tone {
  if (score >= 80) return "bad";
  if (score >= 50) return "warn";
  return "good";
}

export default function OverviewPage(): JSX.Element {
  const navigate = useNavigate();
  const [globalSummary, setGlobalSummary] = useState<GlobalSummary | null>(null);

  useEffect(() => {
    let isMounted = true;

    (async () => {
      try {
        const summary = await fetchGlobalSummary();
        if (isMounted) {
          setGlobalSummary(summary);
        }
      } catch (error) {
        if (import.meta.env.DEV) {
          const message = error instanceof Error ? error.message : String(error);
          console.error("Failed to load global summary", message);
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, []);
  const metrics = useMemo(() => {
    const total = MOCK_SHIPMENTS.length;
    const activeShipments = MOCK_SHIPMENTS.filter((s) => ACTIVE_STATUSES.has(s.status)).length;
    const delayedOrBlocked = MOCK_SHIPMENTS.filter((s) => EXCEPTION_STATUSES.has(s.status)).length;
    const onTimePct = percentage(total - delayedOrBlocked, total);

    const exceptionShipments = MOCK_SHIPMENTS.filter(
      (s) =>
        EXCEPTION_STATUSES.has(s.status) ||
        s.payment.state === "blocked" ||
        s.governance.exceptions.length > 0 ||
        s.risk.category === "high"
    )
      .sort((a, b) => b.risk.score - a.risk.score)
      .slice(0, 6);

    const paymentHealth = classifyPaymentHealth(MOCK_SHIPMENTS);
    const blockedPayments = MOCK_SHIPMENTS.filter((s) => s.payment.state === "blocked").length;
    const partialPayments = MOCK_SHIPMENTS.filter((s) => s.payment.state === "partially_paid").length;
    const proofsVerified = MOCK_SHIPMENTS.filter((s) => s.governance.proofpackStatus === "VERIFIED").length;
    const highRiskPct = percentage(
      MOCK_SHIPMENTS.filter((s) => s.risk.category !== "low").length,
      total
    );

    return {
      totalShipments: total,
      activeShipments,
      onTimePct,
      exceptionsCount: exceptionShipments.length,
      paymentHealth,
      exceptionShipments,
      blockedPayments,
      partialPayments,
      proofsVerified,
      proofsPending: total - proofsVerified,
      highRiskPct,
    };
  }, []);

  const handleCorridorSelect = useCallback(
    (corridorId: CorridorId) => {
      navigate(`/shipments?corridor=${corridorId}`);
    },
    [navigate],
  );

  return (
    <div className="space-y-8 text-slate-100">
      <header className="flex flex-col gap-3 border-b border-slate-800/70 pb-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-500">
            ChainBridge // Control Tower
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-slate-50">
            Global Freight & Payment Overview
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            24/7 governance view across shipments, risk posture, and milestone-based payments.
          </p>
        </div>

        <div className="flex flex-wrap gap-3 text-[11px]">
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2">
            <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Watch Window</p>
            <p className="mt-1 font-mono text-slate-100">North America · Trans-Pacific</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2">
            <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Corridors Monitored</p>
            <p className="mt-1 font-mono text-slate-100">3 active · 0 paused</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2">
            <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Alerts (Last 24h)</p>
            <p className="mt-1 font-mono text-amber-300">High: 2 · Medium: 3</p>
          </div>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Active Shipments"
          value={metrics.activeShipments}
          helper={`${metrics.totalShipments} total tracked`}
          tone="good"
        />
        <KpiCard
          label="On-Time Performance"
          value={`${metrics.onTimePct}%`}
          helper="Delayed + blocked excluded"
          tone={metrics.onTimePct >= 90 ? "good" : metrics.onTimePct >= 75 ? "warn" : "bad"}
        />
        <KpiCard
          label="Exceptions Stack"
          value={metrics.exceptionsCount}
          helper="High-risk, blocked, or delayed"
          tone={metrics.exceptionsCount === 0 ? "good" : "bad"}
        />
        <KpiCard
          label="Payment Health"
          value={metrics.paymentHealth.label}
          helper={`${metrics.blockedPayments} blocked / ${metrics.partialPayments} partial`}
          tone={metrics.paymentHealth.tone}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <ExceptionsStack shipments={metrics.exceptionShipments} className="lg:col-span-2" />
        <NetworkHealth
          highRiskPct={metrics.highRiskPct}
          blockedPayments={metrics.blockedPayments}
          proofsVerified={metrics.proofsVerified}
          proofsPending={metrics.proofsPending}
        />
      </section>

      <CorridorIntelPanel onSelectCorridor={handleCorridorSelect} />

      <PaymentRailsIntelPanel />

      <IoTHealthPanel iot={globalSummary?.iot ?? null} />

      <section className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2">
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Live Event Feed (Mock)
        </p>
        <div className="flex flex-wrap gap-3 text-[11px] text-slate-300">
          <span className="rounded-full bg-slate-900 px-2 py-1 font-mono">
            [RISK] SHP-1004 blocked · ChainPay hold active
          </span>
          <span className="rounded-full bg-slate-900 px-2 py-1 font-mono">
            [ETA] SHP-1001 updated ETA &lt; 6h slip
          </span>
          <span className="rounded-full bg-slate-900 px-2 py-1 font-mono">
            [NETWORK] No corridor-wide outage detected
          </span>
        </div>
      </section>
    </div>
  );
}

interface KpiCardProps {
  label: string;
  value: string | number;
  helper: string;
  tone: Tone;
}

function KpiCard({ label, value, helper, tone }: KpiCardProps): JSX.Element {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-inner shadow-slate-950/40">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-3 flex items-end justify-between">
        <span className="text-3xl font-semibold text-white">{value}</span>
        <span className={`text-xs font-semibold ${toneClasses[tone]}`}>Live</span>
      </div>
      <p className="mt-2 text-sm text-slate-400">{helper}</p>
    </article>
  );
}

interface ExceptionsStackProps {
  shipments: Shipment[];
  className?: string;
}

function ExceptionsStack({ shipments, className }: ExceptionsStackProps): JSX.Element {
  return (
    <section className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-5 ${className ?? ""}`}>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-amber-400">Exception Stack</p>
          <h2 className="text-xl font-semibold text-white">High-Risk & Blocked</h2>
        </div>
        <AlertTriangle className="h-5 w-5 text-amber-400" />
      </div>
      {shipments.length === 0 ? (
        <p className="text-sm text-slate-400">All shipments nominal in the last scan.</p>
      ) : (
        <div className="space-y-3">
          {shipments.map((shipment) => (
            <article
              key={shipment.id}
              className="rounded-2xl border border-slate-800/80 bg-slate-950/40 p-4 transition hover:border-slate-700"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-white">{shipment.reference}</p>
                  <p className="text-xs text-slate-400">
                    {shipment.origin} → {shipment.destination}
                  </p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${badgeClasses[riskTone(shipment.risk.score)]}`}>
                  Risk {shipment.risk.score}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-1">
                  <ArrowUpRight className="h-3.5 w-3.5 text-amber-400" />
                  <span className="capitalize text-slate-300">{shipment.status.replace("_", " ")}</span>
                </div>
                <span className="capitalize text-slate-300">{shipment.payment.state.replace(/_/g, " ")}</span>
              </div>
              {shipment.governance.exceptions.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">
                  {shipment.governance.exceptions.join(" · ").replace(/_/g, " ")}
                </p>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

interface NetworkHealthProps {
  highRiskPct: number;
  blockedPayments: number;
  proofsVerified: number;
  proofsPending: number;
}

function NetworkHealth({ highRiskPct, blockedPayments, proofsVerified, proofsPending }: NetworkHealthProps): JSX.Element {
  const cards = [
    {
      label: "Risk Outlook",
      value: `${highRiskPct}% high`,
      subline: "Watchlisted shipments",
      tone: highRiskPct < 20 ? "good" : highRiskPct < 40 ? "warn" : "bad",
    },
    {
      label: "Payment Holds",
      value: `${blockedPayments} holds`,
      subline: "Escrows awaiting clearance",
      tone: blockedPayments === 0 ? "good" : blockedPayments <= 2 ? "warn" : "bad",
    },
    {
      label: "ProofPack Status",
      value: `${proofsVerified}/${proofsVerified + proofsPending} verified`,
      subline: `${proofsPending} awaiting signature`,
      tone: proofsPending === 0 ? "good" : proofsPending <= 1 ? "warn" : "bad",
    },
  ] as const;

  return (
    <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
      <div>
        <p className="text-xs uppercase tracking-widest text-slate-500">Network Health</p>
        <h2 className="text-xl font-semibold text-white">Real-time posture</h2>
      </div>
      <div className="space-y-4">
        {cards.map((card) => (
          <article key={card.label} className="rounded-2xl border border-slate-800/80 bg-slate-950/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {card.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-white">{card.value}</p>
                <p className="text-sm text-slate-400">{card.subline}</p>
              </div>
              {card.tone === "bad" ? (
                <ArrowDownRight className="h-8 w-8 text-red-400" />
              ) : card.tone === "warn" ? (
                <ArrowDownRight className="h-8 w-8 text-amber-400" />
              ) : (
                <ArrowUpRight className="h-8 w-8 text-emerald-400" />
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
