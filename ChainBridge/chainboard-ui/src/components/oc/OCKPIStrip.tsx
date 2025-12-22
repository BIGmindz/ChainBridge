/**
 * OCKPIStrip - Top KPI Bar for The OC Exception Cockpit
 *
 * NEUTRALIZED: PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 * - No semantic colors
 * - No icons
 * - Monospace data display
 * - No marketing language
 */

import { useExceptionStats } from "../../hooks/useExceptions";
import { Skeleton } from "../ui/Skeleton";

interface KPICardProps {
  label: string;
  value: string | number;
  subtext?: string;
  isLoading?: boolean;
}

function KPICard({ label, value, subtext, isLoading }: KPICardProps) {
  return (
    <div
      className="border border-slate-700/50 bg-slate-900/50 px-4 py-3 font-mono"
    >
      <p className="text-xs text-slate-600 uppercase tracking-wider mb-1">
        {label.toLowerCase().replace(/\s+/g, '_')}
      </p>
      {isLoading ? (
        <Skeleton className="h-8 w-16" />
      ) : (
        <p className="text-xl text-slate-400 tabular-nums">
          {value}
        </p>
      )}
      {subtext && (
        <p className="text-xs text-slate-600 mt-1">{subtext}</p>
      )}
    </div>
  );
}

export function OCKPIStrip() {
  const { data: stats, isLoading, error } = useExceptionStats();

  if (error) {
    return (
      <div className="border border-slate-700/50 bg-slate-900/50 px-4 py-3 font-mono">
        <p className="text-xs text-slate-500">status: load_error</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Demo data warning */}
      <div className="border border-slate-600 bg-slate-900/50 px-3 py-2 text-xs text-slate-500 font-mono">
        UNLINKED / DEMO DATA — Not linked to live backend
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <KPICard
          label="open_exceptions"
          value={stats?.total_open ?? 0}
          isLoading={isLoading}
        />

        <KPICard
          label="critical_count"
          value={stats?.critical_count ?? 0}
          isLoading={isLoading}
        />

        <KPICard
          label="high_count"
          value={stats?.high_count ?? 0}
          isLoading={isLoading}
        />

        <KPICard
          label="at_risk_shipments"
          value={(stats?.critical_count ?? 0) + (stats?.high_count ?? 0)}
          isLoading={isLoading}
        />

        <KPICard
          label="cash_in_flight"
          value="—"
          subtext="unlinked"
          isLoading={false}
        />
      </div>
    </div>
  );
}
