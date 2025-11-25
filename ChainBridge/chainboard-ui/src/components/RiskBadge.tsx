/**
 * RiskBadge Component
 *
 * Displays risk category with optional score.
 */

import type { RiskCategory } from "../lib/types";

interface RiskBadgeProps {
  category: RiskCategory;
  score?: number;
  size?: "sm" | "md";
}

export function RiskBadge({ category, score, size = "md" }: RiskBadgeProps) {
  const colors = {
    low: "bg-green-100 text-green-700 border-green-200",
    medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
    high: "bg-red-100 text-red-700 border-red-200",
  };

  const sizes = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-sm",
  };

  const label = category.charAt(0).toUpperCase() + category.slice(1);

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium border rounded ${colors[category]} ${sizes[size]}`}
    >
      {label}
      {score !== undefined && <span className="opacity-75">({score})</span>}
    </span>
  );
}
