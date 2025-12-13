/**
 * DriftSignalBadge - Color-coded drift indicator
 *
 * WCAG AA compliant contrast ratios.
 * ADHD-friendly: clear visual hierarchy with motion for attention.
 */

import { AlertTriangle, CheckCircle, TrendingUp } from "lucide-react";

import { classNames } from "../../utils/classNames";

interface DriftSignalBadgeProps {
  driftDetected: boolean;
  p95Delta: number;
  className?: string;
  size?: "sm" | "md" | "lg";
}

/**
 * Get drift severity level based on P95 delta.
 * Thresholds: <0.15 = good, 0.15-0.25 = warning, >0.25 = critical
 */
function getDriftLevel(p95Delta: number): "good" | "warning" | "critical" {
  if (p95Delta < 0.15) return "good";
  if (p95Delta < 0.25) return "warning";
  return "critical";
}

export function DriftSignalBadge({
  driftDetected,
  p95Delta,
  className,
  size = "md",
}: DriftSignalBadgeProps): JSX.Element {
  const level = getDriftLevel(p95Delta);

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px]",
    md: "px-3 py-1 text-xs",
    lg: "px-4 py-1.5 text-sm",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-3.5 w-3.5",
    lg: "h-4 w-4",
  };

  const baseClasses =
    "inline-flex items-center gap-1.5 rounded-full font-semibold tracking-wide transition-all";

  if (driftDetected || level === "critical") {
    return (
      <span
        className={classNames(
          baseClasses,
          sizeClasses[size],
          "border border-red-500/50 bg-red-500/10 text-red-400",
          "animate-pulse",
          className
        )}
        role="status"
        aria-label="Drift detected - critical"
      >
        <AlertTriangle className={iconSizes[size]} />
        DRIFT
      </span>
    );
  }

  if (level === "warning") {
    return (
      <span
        className={classNames(
          baseClasses,
          sizeClasses[size],
          "border border-amber-500/50 bg-amber-500/10 text-amber-400",
          className
        )}
        role="status"
        aria-label="Drift warning"
      >
        <TrendingUp className={iconSizes[size]} />
        ELEVATED
      </span>
    );
  }

  return (
    <span
      className={classNames(
        baseClasses,
        sizeClasses[size],
        "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        className
      )}
      role="status"
      aria-label="Models aligned"
    >
      <CheckCircle className={iconSizes[size]} />
      ALIGNED
    </span>
  );
}

/**
 * Compact drift indicator for inline use.
 */
export function DriftDot({
  driftDetected,
  p95Delta,
  className,
}: {
  driftDetected: boolean;
  p95Delta: number;
  className?: string;
}): JSX.Element {
  const level = getDriftLevel(p95Delta);

  const colors = {
    good: "bg-emerald-500",
    warning: "bg-amber-500",
    critical: "bg-red-500",
  };

  return (
    <span
      className={classNames(
        "inline-flex h-2 w-2 rounded-full",
        colors[driftDetected ? "critical" : level],
        (driftDetected || level === "critical") && "animate-pulse",
        className
      )}
      aria-hidden="true"
    />
  );
}
