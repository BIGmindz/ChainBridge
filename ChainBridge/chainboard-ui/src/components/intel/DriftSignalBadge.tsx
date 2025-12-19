/**
 * DriftSignalBadge - Neutral drift indicator
 *
 * NEUTRALIZED: PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 * - No semantic colors
 * - No icons
 * - No marketing labels ("ALIGNED", "ELEVATED")
 * - Monospace data display
 */

import { classNames } from "../../utils/classNames";

interface DriftSignalBadgeProps {
  driftDetected: boolean;
  p95Delta: number;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function DriftSignalBadge({
  driftDetected,
  p95Delta,
  className,
  size = "md",
}: DriftSignalBadgeProps): JSX.Element {
  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px]",
    md: "px-3 py-1 text-xs",
    lg: "px-4 py-1.5 text-sm",
  };

  const baseClasses =
    "inline-flex items-center gap-1.5 border border-slate-700/50 bg-slate-900/50 font-mono";

  return (
    <span
      className={classNames(baseClasses, sizeClasses[size], className)}
      role="status"
      aria-label={`P95 delta: ${(p95Delta * 100).toFixed(1)}%`}
    >
      <span className="text-slate-600">p95:</span>
      <span className="text-slate-400">{(p95Delta * 100).toFixed(1)}%</span>
      {driftDetected && (
        <span className="text-slate-500 ml-1">drift</span>
      )}
    </span>
  );
}

/**
 * Compact drift indicator for inline use.
 * NEUTRALIZED: No semantic colors.
 */
export function DriftDot({
  driftDetected,
  className,
}: {
  driftDetected: boolean;
  p95Delta: number;
  className?: string;
}): JSX.Element {
  return (
    <span
      className={classNames(
        "inline-flex h-2 w-2 bg-slate-600",
        driftDetected && "bg-slate-400",
        className
      )}
      aria-hidden="true"
    />
  );
}
