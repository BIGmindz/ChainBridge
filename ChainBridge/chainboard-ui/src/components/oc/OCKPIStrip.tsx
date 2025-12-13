/**
 * OCKPIStrip - Top KPI Bar for The OC Exception Cockpit
 *
 * Displays high-level metrics: total exceptions, severity breakdown,
 * at-risk shipments, and cash-in-flight placeholders.
 *
 * "Pilots need their instruments at a glance."
 */

import { AlertTriangle, DollarSign, Shield, TrendingDown, Truck } from "lucide-react";

import { useExceptionStats } from "../../hooks/useExceptions";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

interface KPICardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon: React.ReactNode;
  variant?: "default" | "critical" | "warning" | "success" | "info";
  isLoading?: boolean;
}

function KPICard({ label, value, subtext, icon, variant = "default", isLoading }: KPICardProps) {
  const variantStyles = {
    default: "border-slate-700/50 bg-slate-900/80",
    critical: "border-rose-900/50 bg-rose-950/30",
    warning: "border-amber-900/50 bg-amber-950/30",
    success: "border-emerald-900/50 bg-emerald-950/30",
    info: "border-sky-900/50 bg-sky-950/30",
  };

  const iconStyles = {
    default: "text-slate-400",
    critical: "text-rose-400",
    warning: "text-amber-400",
    success: "text-emerald-400",
    info: "text-sky-400",
  };

  const valueStyles = {
    default: "text-slate-100",
    critical: "text-rose-300",
    warning: "text-amber-300",
    success: "text-emerald-300",
    info: "text-sky-300",
  };

  return (
    <div
      className={classNames(
        "rounded-xl border px-4 py-3 backdrop-blur-sm transition-all hover:scale-[1.02]",
        variantStyles[variant]
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
          {label}
        </span>
        <span className={iconStyles[variant]}>{icon}</span>
      </div>
      {isLoading ? (
        <Skeleton className="h-8 w-16" />
      ) : (
        <div className={classNames("text-2xl font-mono font-bold", valueStyles[variant])}>
          {value}
        </div>
      )}
      {subtext && (
        <div className="text-[10px] text-slate-500 mt-1">{subtext}</div>
      )}
    </div>
  );
}

export function OCKPIStrip() {
  const { data: stats, isLoading, error } = useExceptionStats();

  if (error) {
    return (
      <div className="bg-rose-950/30 border border-rose-900/50 rounded-xl px-4 py-3 text-rose-300 text-sm">
        Unable to load exception statistics
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {/* Total Open Exceptions */}
      <KPICard
        label="Open Exceptions"
        value={stats?.total_open ?? 0}
        subtext="Requires attention"
        icon={<AlertTriangle className="h-4 w-4" />}
        variant={stats && stats.total_open > 10 ? "warning" : "default"}
        isLoading={isLoading}
      />

      {/* Critical Count */}
      <KPICard
        label="Critical"
        value={stats?.critical_count ?? 0}
        subtext="Immediate action"
        icon={<Shield className="h-4 w-4" />}
        variant={stats && stats.critical_count > 0 ? "critical" : "default"}
        isLoading={isLoading}
      />

      {/* High Severity Count */}
      <KPICard
        label="High Severity"
        value={stats?.high_count ?? 0}
        subtext="Elevated priority"
        icon={<TrendingDown className="h-4 w-4" />}
        variant={stats && stats.high_count > 2 ? "warning" : "default"}
        isLoading={isLoading}
      />

      {/* At-Risk Shipments - Placeholder for ChainIQ integration */}
      <KPICard
        label="At-Risk Shipments"
        value={(stats?.critical_count ?? 0) + (stats?.high_count ?? 0)}
        subtext="ChainIQ monitored"
        icon={<Truck className="h-4 w-4" />}
        variant="info"
        isLoading={isLoading}
      />

      {/* Cash in Flight - Placeholder for ChainPay integration */}
      <KPICard
        label="Cash in Flight"
        value="$—"
        subtext="ChainPay (coming soon)"
        icon={<DollarSign className="h-4 w-4" />}
        variant="default"
        isLoading={false}
      />
    </div>
  );
}
