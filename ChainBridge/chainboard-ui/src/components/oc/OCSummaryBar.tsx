/**
 * OCSummaryBar - Top HUD Summary for The OC
 *
 * NEUTRALIZED: PAC-BENSON-SONNY-ACTIVATION-BLOCK-UI-ENFORCEMENT-02
 * - No semantic colors
 * - No icons
 * - Monospace data display
 */

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
      <div className="flex gap-6 text-sm font-mono text-slate-400 px-4 py-3 bg-slate-900/50 border-b border-slate-700">
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
        title="total_at_risk"
        value={summary.totalAtRisk}
      />
      <HUDStatCard
        title="critical_count"
        value={summary.criticalCount}
      />
      <HUDStatCard
        title="high_count"
        value={summary.highCount}
      />
      <HUDStatCard
        title="needs_snapshot"
        value={summary.needsSnapshotCount}
      />
    </div>
  );
}
