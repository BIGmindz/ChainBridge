import { AlertTriangle, RefreshCcw, ShieldCheck } from "lucide-react";

import type { AgentHealthSummary } from "../../core/types/agents";

export interface AgentHealthCardProps {
  summary: AgentHealthSummary | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
}

function getHealthState(summary: AgentHealthSummary | null): {
  label: string;
  tone: "healthy" | "attention";
  description: string;
} {
  if (!summary || summary.invalid > 0) {
    const invalidCount = summary?.invalid ?? 0;
    return {
      label: invalidCount === 0 ? "Unknown" : "Attention Needed",
      tone: invalidCount === 0 ? "attention" : "attention",
      description:
        invalidCount > 0
          ? `${invalidCount} agent${invalidCount === 1 ? "" : "s"} require fixes`
          : "Awaiting latest status",
    };
  }

  return {
    label: "Healthy",
    tone: "healthy",
    description: "All agents validated",
  };
}

export function AgentHealthCard({ summary, loading, error, onRetry }: AgentHealthCardProps): JSX.Element {
  const state = getHealthState(summary);

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Agent Health</p>
            <div className="mt-4 h-8 w-32 animate-pulse rounded bg-slate-800" />
            <div className="mt-2 h-4 w-48 animate-pulse rounded bg-slate-800" />
          </div>
          <div className="h-12 w-12 animate-pulse rounded-full bg-slate-800" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-red-300">Agent Health</p>
            <p className="mt-3 text-base font-semibold text-red-200">Unable to load agent status</p>
            <p className="mt-1 text-sm text-red-200/70">{error.message}</p>
          </div>
          <AlertTriangle className="h-10 w-10 text-red-300" aria-hidden="true" />
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-red-200 transition hover:border-red-400"
        >
          <RefreshCcw className="h-4 w-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Agent Health</p>
          <div className="mt-4 flex items-center gap-3">
            {state.tone === "healthy" ? (
              <ShieldCheck className="h-9 w-9 text-emerald-400" aria-hidden="true" />
            ) : (
              <AlertTriangle className="h-9 w-9 text-amber-400" aria-hidden="true" />
            )}
            <div>
              <p
                className={`text-lg font-semibold ${
                  state.tone === "healthy" ? "text-emerald-300" : "text-amber-300"
                }`}
              >
                {state.label}
              </p>
              <p className="text-sm text-slate-400">{state.description}</p>
            </div>
          </div>
        </div>
        <div className="grid gap-2 text-right text-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Total</p>
            <p className="text-2xl font-bold text-slate-100">{summary?.total ?? "--"}</p>
          </div>
          <div className="text-emerald-300">
            <p className="text-xs uppercase tracking-wide text-emerald-500/80">Valid</p>
            <p className="text-xl font-semibold">{summary?.valid ?? "--"}</p>
          </div>
          <div className="text-amber-300">
            <p className="text-xs uppercase tracking-wide text-amber-400/80">Invalid</p>
            <p className="text-xl font-semibold">{summary?.invalid ?? "--"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
