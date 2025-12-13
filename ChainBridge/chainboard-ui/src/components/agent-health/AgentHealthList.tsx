import { AlertTriangle, CheckCircle2 } from "lucide-react";

export interface AgentHealthListProps {
  invalidRoles: string[];
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
}

export function AgentHealthList({ invalidRoles, loading, error, onRetry }: AgentHealthListProps): JSX.Element {
  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
          Invalid Roles
        </p>
        <div className="mt-4 space-y-3">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-5 w-full animate-pulse rounded bg-slate-800" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-red-300">Invalid Roles</p>
        <p className="mt-3 text-sm text-red-200">{error.message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-red-500/40 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-red-200 transition hover:border-red-400"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!invalidRoles.length) {
    return (
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-6">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="h-8 w-8 text-emerald-400" aria-hidden="true" />
          <div>
            <p className="text-base font-semibold text-emerald-200">All agents valid</p>
            <p className="text-sm text-emerald-200/70">No invalid roles detected in latest check.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-amber-500/40 bg-amber-500/5 p-6">
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-6 w-6 text-amber-300" aria-hidden="true" />
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-amber-300">Invalid Roles</p>
          <p className="text-sm text-amber-100/80">Agents missing required prompts or metadata</p>
        </div>
      </div>
      <ul className="mt-4 space-y-2 text-sm text-slate-100">
        {invalidRoles.map((role) => (
          <li
            key={role}
            className="rounded border border-amber-500/20 bg-slate-950/50 px-3 py-2 text-amber-100"
          >
            {role}
          </li>
        ))}
      </ul>
    </div>
  );
}
