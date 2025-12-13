/**
 * OCAuditLog - Bottom Audit/Decision Log Panel for The OC
 *
 * Displays recent decision records from the audit trail.
 * Shows who decided what and when for compliance/governance visibility.
 *
 * "Every decision leaves a trace. Every trace tells a story."
 */

import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle,
  Clock,
  DollarSign,
  GitBranch,
  Play,
  Shield,
  User,
} from "lucide-react";

import { useDecisionRecords } from "../../hooks/useExceptions";
import type { DecisionRecord, DecisionType } from "../../types/exceptions";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "../ui/Skeleton";

interface OCAuditLogProps {
  shipmentId?: string;
  exceptionId?: string;
  limit?: number;
}

// Decision type icon and color mapping
const decisionMeta: Record<DecisionType, { icon: React.ReactNode; color: string; label: string }> = {
  RISK_DECISION: {
    icon: <Shield className="h-3.5 w-3.5" />,
    color: "text-sky-400",
    label: "Risk",
  },
  SETTLEMENT_DECISION: {
    icon: <DollarSign className="h-3.5 w-3.5" />,
    color: "text-emerald-400",
    label: "Settlement",
  },
  EXCEPTION_RESOLUTION: {
    icon: <CheckCircle className="h-3.5 w-3.5" />,
    color: "text-violet-400",
    label: "Resolution",
  },
  PLAYBOOK_STEP: {
    icon: <Play className="h-3.5 w-3.5" />,
    color: "text-amber-400",
    label: "Playbook",
  },
  MANUAL_OVERRIDE: {
    icon: <GitBranch className="h-3.5 w-3.5" />,
    color: "text-rose-400",
    label: "Override",
  },
  AUTOMATED_ACTION: {
    icon: <Bot className="h-3.5 w-3.5" />,
    color: "text-slate-400",
    label: "Automated",
  },
};

// Actor type icon
function ActorIcon({ actorType }: { actorType: "SYSTEM" | "OPERATOR" | "API" }) {
  switch (actorType) {
    case "SYSTEM":
      return <Bot className="h-3 w-3 text-slate-500" />;
    case "OPERATOR":
      return <User className="h-3 w-3 text-slate-400" />;
    case "API":
      return <Activity className="h-3 w-3 text-slate-500" />;
  }
}

// Format relative time
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function DecisionRow({ record }: { record: DecisionRecord }) {
  const meta = decisionMeta[record.type];

  return (
    <div className="px-4 py-2.5 hover:bg-slate-800/30 transition-colors">
      <div className="flex items-start gap-3">
        {/* Type Icon */}
        <div className={classNames("mt-0.5", meta.color)}>
          {meta.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Summary */}
          <p className="text-sm text-slate-200 leading-snug">
            {record.summary}
          </p>

          {/* Meta Row */}
          <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500">
            {/* Actor */}
            <span className="flex items-center gap-1">
              <ActorIcon actorType={record.actor_type} />
              {record.actor}
            </span>

            {/* Policy (if present) */}
            {record.policy_name && (
              <span className="truncate max-w-[120px]" title={record.policy_name}>
                Policy: {record.policy_name}
              </span>
            )}

            {/* Time */}
            <span className="flex items-center gap-1 ml-auto">
              <Clock className="h-2.5 w-2.5" />
              {formatRelativeTime(record.created_at)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="p-4 space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <Skeleton className="h-4 w-4 rounded-full" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="px-4 py-6 text-center">
      <Activity className="h-8 w-8 mx-auto mb-2 text-slate-600" />
      <p className="text-sm text-slate-400">No decision records</p>
      <p className="text-xs text-slate-500 mt-1">
        Decisions will appear here as they are made
      </p>
    </div>
  );
}

export function OCAuditLog({ shipmentId, exceptionId, limit = 10 }: OCAuditLogProps) {
  const { data, isLoading, error } = useDecisionRecords({
    shipment_id: shipmentId,
    exception_id: exceptionId,
    limit,
  });

  return (
    <div className="bg-slate-900/80 border border-slate-800/70 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800/50 bg-slate-800/30 flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
          <Activity className="h-3.5 w-3.5" />
          Decision Audit Log
        </h3>
        <span className="text-[10px] text-slate-500">
          {data?.records.length ?? 0} records
        </span>
      </div>

      {/* Content */}
      {error ? (
        <div className="px-4 py-3">
          <div className="flex items-center gap-2 text-rose-400 text-sm">
            <AlertTriangle className="h-4 w-4" />
            Unable to load audit log
          </div>
        </div>
      ) : isLoading ? (
        <LoadingSkeleton rows={3} />
      ) : !data?.records.length ? (
        <EmptyState />
      ) : (
        <div className="divide-y divide-slate-800/30 max-h-48 overflow-y-auto">
          {data.records.map((record) => (
            <DecisionRow key={record.id} record={record} />
          ))}
        </div>
      )}

      {/* Footer hint */}
      <div className="px-4 py-2 border-t border-slate-800/30 bg-slate-800/20">
        <p className="text-[10px] text-slate-500 text-center">
          All decisions are recorded for compliance and governance
        </p>
      </div>
    </div>
  );
}
