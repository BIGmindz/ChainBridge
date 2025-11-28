/**
 * HUDStatCard - Minimal statistical display card for The OC
 * Pure presentational component with no business logic
 */

import { LucideIcon } from "lucide-react";

import { classNames } from "../../../utils/classNames";

export interface HUDStatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  severity?: "info" | "warning" | "danger" | "success";
  icon?: LucideIcon;
  className?: string;
}

const severityStyles = {
  info: "border-slate-700 bg-slate-900/50",
  warning: "border-amber-500/30 bg-amber-950/20",
  danger: "border-red-500/30 bg-red-950/20",
  success: "border-emerald-500/30 bg-emerald-950/20",
} as const;

const severityTextStyles = {
  info: "text-slate-100",
  warning: "text-amber-100",
  danger: "text-red-100",
  success: "text-emerald-100",
} as const;

const severityValueStyles = {
  info: "text-slate-50",
  warning: "text-amber-50",
  danger: "text-red-50",
  success: "text-emerald-50",
} as const;

export function HUDStatCard({
  title,
  value,
  subtitle,
  severity = "info",
  icon: Icon,
  className,
}: HUDStatCardProps): JSX.Element {
  return (
    <div
      className={classNames(
        "rounded-lg border p-4 transition-colors",
        severityStyles[severity],
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className={classNames("text-sm font-medium", severityTextStyles[severity])}>
            {title}
          </div>
          <div className={classNames("mt-1 text-2xl font-bold tabular-nums", severityValueStyles[severity])}>
            {value}
          </div>
          {subtitle && (
            <div className={classNames("mt-1 text-xs", severityTextStyles[severity], "opacity-75")}>
              {subtitle}
            </div>
          )}
        </div>
        {Icon && (
          <Icon className={classNames("h-8 w-8 opacity-60", severityTextStyles[severity])} />
        )}
      </div>
    </div>
  );
}
