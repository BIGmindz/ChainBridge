/**
 * RiskBadge - Color-coded risk level indicator for The OC
 * Maps canonical RiskLevel enum to visual styling
 */

import { RiskLevel } from "../../../types/chainbridge";
import { classNames } from "../../../utils/classNames";

export interface RiskBadgeProps {
  riskLevel: RiskLevel;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const riskStyles = {
  LOW: {
    bg: "bg-emerald-500/20",
    border: "border-emerald-500/40",
    text: "text-emerald-300",
  },
  MEDIUM: {
    bg: "bg-amber-500/20",
    border: "border-amber-500/40",
    text: "text-amber-300",
  },
  HIGH: {
    bg: "bg-orange-500/20",
    border: "border-orange-500/40",
    text: "text-orange-300",
  },
  CRITICAL: {
    bg: "bg-red-500/20",
    border: "border-red-500/40",
    text: "text-red-300",
  },
} as const;

const sizeStyles = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3 py-1.5 text-base",
} as const;

export function RiskBadge({
  riskLevel,
  size = "md",
  className
}: RiskBadgeProps): JSX.Element {
  const styles = riskStyles[riskLevel];

  return (
    <span
      className={classNames(
        "inline-flex items-center rounded-full border font-medium",
        styles.bg,
        styles.border,
        styles.text,
        sizeStyles[size],
        className
      )}
    >
      {riskLevel}
    </span>
  );
}
