/**
 * OCSummaryBar - Top HUD Summary for The OC
 *
 * Displays real-time operator summary metrics in a color-coded horizontal layout.
 * Pure visualization component with no business logic - displays backend data as-is.
 */

import { AlertTriangle, Clock } from "lucide-react";

import type { OperatorSummary } from "../../types/chainbridge";
import { Skeleton } from "../ui/Skeleton";

import { HUDStatCard } from "./hud/HUDStatCard";

interface OCSummaryBarProps {
  summary: OperatorSummary | null;
  isLoading: boolean;
}

export function OCSummaryBar({ summary, isLoading }: OCSummaryBarProps) {
  if (isLoading) {
    return (
      <div className="flex gap-6 text-sm font-medium text-slate-300 px-4 py-3 bg-slate-800/50 border-b border-slate-700">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-24" />
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 bg-slate-900/50 border-b border-slate-700">
      <HUDStatCard
        title="Total At-Risk"
        value={summary.totalAtRisk}
        severity="info"
        icon={AlertTriangle}
      />
      <HUDStatCard
        title="Critical"
        value={summary.criticalCount}
        severity="danger"
      />
      <HUDStatCard
        title="High Risk"
        value={summary.highCount}
        severity="warning"
      />
      <HUDStatCard
        title="Needs Snapshot"
        value={summary.needsSnapshotCount}
        severity="info"
        icon={Clock}
      />
    </div>
  );
}
