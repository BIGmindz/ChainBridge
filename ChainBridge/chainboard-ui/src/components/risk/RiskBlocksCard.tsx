/**
 * RiskBlocksCard
 *
 * Risk decision overlay showing compliance blocks and gates.
 * GitHub Checks-style UI for settlement intelligence.
 *
 * Features:
 * - Green = passed, Amber = pending, Red = blocked
 * - Compliance blocks array
 * - Risk gate reason
 * - Documentation issues
 * - Snapshot/export state
 */

import { classNames } from "../../utils/classNames";

export interface RiskBlock {
  id: string;
  type: "compliance" | "documentation" | "risk_gate" | "snapshot";
  status: "passed" | "pending" | "failed";
  title: string;
  description: string;
  severity: "info" | "warning" | "critical";
}

export interface RiskDecision {
  risk_level: string;
  riskScore: number;
  risk_gate_reason?: string | null;
  compliance_blocks: RiskBlock[];
  documentation_issues: string[];
  snapshot_status?: "SUCCESS" | "PENDING" | "IN_PROGRESS" | "FAILED" | null;
}

interface RiskBlocksCardProps {
  decision: RiskDecision | null;
  isLoading?: boolean;
  compact?: boolean;
}

const STATUS_CONFIG = {
  passed: {
    icon: "✓",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
  },
  pending: {
    icon: "○",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
  },
  failed: {
    icon: "✕",
    color: "text-rose-400",
    bg: "bg-rose-500/10",
    border: "border-rose-500/30",
  },
};

const SEVERITY_CONFIG = {
  info: "text-blue-400",
  warning: "text-amber-400",
  critical: "text-rose-400",
};

export function RiskBlocksCard({
  decision,
  isLoading = false,
  compact = false,
}: RiskBlocksCardProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-800 rounded w-32" />
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-5 h-5 bg-slate-800 rounded-full" />
                <div className="h-3 bg-slate-800 rounded flex-1" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!decision) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 text-center">
        <div className="text-slate-600 text-sm">
          🛡️ No risk decision data available
        </div>
      </div>
    );
  }

  const allBlocks = decision.compliance_blocks || [];
  const passedCount = allBlocks.filter((b) => b.status === "passed").length;
  const failedCount = allBlocks.filter((b) => b.status === "failed").length;
  const pendingCount = allBlocks.filter((b) => b.status === "pending").length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-800/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">🛡️</span>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Risk Decision</div>
              <div className="text-sm font-semibold text-slate-200">
                {decision.risk_level} ({decision.riskScore}/100)
              </div>
            </div>
          </div>

          {/* Summary Badges */}
          <div className="flex items-center gap-2 text-xs">
            {passedCount > 0 && (
              <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/30">
                ✓ {passedCount}
              </span>
            )}
            {pendingCount > 0 && (
              <span className="px-2 py-1 bg-amber-500/10 text-amber-400 rounded border border-amber-500/30">
                ○ {pendingCount}
              </span>
            )}
            {failedCount > 0 && (
              <span className="px-2 py-1 bg-rose-500/10 text-rose-400 rounded border border-rose-500/30">
                ✕ {failedCount}
              </span>
            )}
          </div>
        </div>

        {/* Risk Gate Reason */}
        {decision.risk_gate_reason && (
          <div className="mt-2 text-xs text-slate-400 leading-relaxed">
            {decision.risk_gate_reason}
          </div>
        )}
      </div>

      {/* Blocks List */}
      <div className={classNames("divide-y divide-slate-800", compact ? "max-h-64 overflow-y-auto" : "")}>
        {allBlocks.length === 0 ? (
          <div className="p-4 text-center text-slate-500 text-sm">
            No risk blocks configured
          </div>
        ) : (
          allBlocks.map((block) => {
            const statusConfig = STATUS_CONFIG[block.status];

            return (
              <div
                key={block.id}
                className="p-3 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  {/* Status Icon */}
                  <div
                    className={classNames(
                      "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border",
                      statusConfig.bg,
                      statusConfig.color,
                      statusConfig.border
                    )}
                  >
                    {statusConfig.icon}
                  </div>

                  {/* Block Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={classNames("text-sm font-medium", statusConfig.color)}>
                        {block.title}
                      </span>
                      <span className={classNames("text-xs", SEVERITY_CONFIG[block.severity])}>
                        ({block.severity})
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 leading-relaxed">
                      {block.description}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Documentation Issues */}
      {decision.documentation_issues.length > 0 && (
        <div className="border-t border-slate-800 p-3 bg-amber-500/5">
          <div className="text-xs text-amber-400 font-medium mb-2">
            📄 Documentation Issues ({decision.documentation_issues.length})
          </div>
          <ul className="space-y-1 text-xs text-slate-400">
            {decision.documentation_issues.slice(0, compact ? 3 : 10).map((issue, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-amber-500">•</span>
                <span>{issue}</span>
              </li>
            ))}
            {compact && decision.documentation_issues.length > 3 && (
              <li className="text-slate-500">
                +{decision.documentation_issues.length - 3} more...
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Snapshot Status */}
      {decision.snapshot_status && (
        <div className="border-t border-slate-800 p-3 bg-slate-800/30">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">Snapshot Export:</span>
            <span
              className={classNames(
                "px-2 py-0.5 rounded font-medium",
                decision.snapshot_status === "SUCCESS"
                  ? "bg-emerald-500/10 text-emerald-400"
                  : decision.snapshot_status === "FAILED"
                  ? "bg-rose-500/10 text-rose-400"
                  : "bg-amber-500/10 text-amber-400"
              )}
            >
              {decision.snapshot_status}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
