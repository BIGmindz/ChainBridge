/**
 * OCExceptionQueue - Left Pane Exception List for The OC
 *
 * Displays the prioritized exception queue with severity badges,
 * type indicators, and selection highlighting.
 *
 * "The radar screen for operator situational awareness."
 */

import {
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  FileWarning,
  Loader2,
  Radio,
  Shield,
  ThermometerSun,
  Truck,
} from "lucide-react";

import { useExceptions } from "../../hooks/useExceptions";
import type { Exception, ExceptionSeverity, ExceptionType } from "../../types/exceptions";
import { classNames } from "../../utils/classNames";
import { Badge } from "../ui/Badge";
import { Skeleton } from "../ui/Skeleton";

interface OCExceptionQueueProps {
  selectedExceptionId: string | null;
  onSelectException: (exceptionId: string) => void;
}

// Severity badge variant mapping
const severityVariant: Record<ExceptionSeverity, "danger" | "warning" | "info" | "default"> = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "info",
  LOW: "default",
};

// Exception type icon mapping
const typeIcons: Record<ExceptionType, React.ReactNode> = {
  RISK_THRESHOLD: <Shield className="h-3.5 w-3.5" />,
  PAYMENT_HOLD: <DollarSign className="h-3.5 w-3.5" />,
  ETA_BREACH: <Clock className="h-3.5 w-3.5" />,
  COMPLIANCE_FLAG: <FileWarning className="h-3.5 w-3.5" />,
  DOCUMENT_MISSING: <FileWarning className="h-3.5 w-3.5" />,
  IOT_ALERT: <ThermometerSun className="h-3.5 w-3.5" />,
  CARRIER_ISSUE: <Truck className="h-3.5 w-3.5" />,
  CUSTOMS_DELAY: <AlertTriangle className="h-3.5 w-3.5" />,
  ESG_VIOLATION: <Radio className="h-3.5 w-3.5" />,
  MANUAL: <AlertTriangle className="h-3.5 w-3.5" />,
};

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

function ExceptionRow({
  exception,
  isSelected,
  onSelect,
}: {
  exception: Exception;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const isResolved = exception.status === "RESOLVED" || exception.status === "DISMISSED";

  return (
    <div
      onClick={onSelect}
      className={classNames(
        "px-4 py-3 cursor-pointer transition-all border-l-4",
        isSelected
          ? "bg-slate-700/80 border-emerald-400"
          : isResolved
            ? "bg-slate-800/30 border-slate-700 opacity-60 hover:opacity-80"
            : "bg-slate-800/50 border-slate-700 hover:bg-slate-700/50 hover:border-slate-600"
      )}
      tabIndex={0}
      data-selected={isSelected}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
    >
      {/* Header Row: Severity + Type + Time */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge variant={severityVariant[exception.severity]}>
            {exception.severity}
          </Badge>
          <span className="text-slate-400" title={exception.type}>
            {typeIcons[exception.type]}
          </span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          {formatRelativeTime(exception.created_at)}
        </span>
      </div>

      {/* Summary */}
      <div className={classNames(
        "text-sm font-medium mb-1 line-clamp-2",
        isSelected ? "text-white" : "text-slate-200"
      )}>
        {exception.summary}
      </div>

      {/* Footer: Shipment + Status + Owner */}
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-mono text-slate-400">
          {exception.shipment_reference ?? exception.shipment_id}
        </span>
        <div className="flex items-center gap-2">
          {exception.status === "IN_PROGRESS" && (
            <span className="flex items-center gap-1 text-amber-400">
              <Loader2 className="h-3 w-3 animate-spin" />
              In Progress
            </span>
          )}
          {isResolved && (
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle className="h-3 w-3" />
              Resolved
            </span>
          )}
          {exception.owner_name && (
            <span className="text-slate-500">
              {exception.owner_name}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function QueueSkeleton() {
  return (
    <div className="p-4 space-y-4">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-16" />
            <Skeleton className="h-4 w-4 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-3 w-32" />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="p-8 text-center">
      <CheckCircle className="h-12 w-12 mx-auto mb-3 text-emerald-500" />
      <p className="font-medium text-slate-200">No Open Exceptions</p>
      <p className="text-xs mt-1 text-slate-500">
        All systems nominal — queue is clear
      </p>
    </div>
  );
}

export function OCExceptionQueue({ selectedExceptionId, onSelectException }: OCExceptionQueueProps) {
  const { data, isLoading, error } = useExceptions();

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-rose-950/30 border border-rose-900/50 rounded-lg px-4 py-3 text-rose-300 text-sm">
          <AlertTriangle className="h-4 w-4 inline mr-2" />
          Unable to load exception queue
        </div>
      </div>
    );
  }

  if (isLoading) {
    return <QueueSkeleton />;
  }

  const exceptions = data?.exceptions ?? [];

  if (exceptions.length === 0) {
    return <EmptyState />;
  }

  // Split into open and resolved for visual separation
  const openExceptions = exceptions.filter(
    (e) => e.status !== "RESOLVED" && e.status !== "DISMISSED"
  );
  const resolvedExceptions = exceptions.filter(
    (e) => e.status === "RESOLVED" || e.status === "DISMISSED"
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700/50 bg-slate-800/30 flex justify-between items-center">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Exception Queue
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            {openExceptions.length} open
          </span>
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" title="Critical" />
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" title="High" />
            <span className="w-1.5 h-1.5 rounded-full bg-sky-500" title="Medium" />
          </div>
        </div>
      </div>

      {/* Scrollable List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-700/50">
        {openExceptions.map((exception) => (
          <ExceptionRow
            key={exception.id}
            exception={exception}
            isSelected={selectedExceptionId === exception.id}
            onSelect={() => onSelectException(exception.id)}
          />
        ))}

        {/* Resolved Section (collapsed) */}
        {resolvedExceptions.length > 0 && (
          <>
            <div className="px-4 py-2 bg-slate-800/20 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Recently Resolved ({resolvedExceptions.length})
            </div>
            {resolvedExceptions.slice(0, 3).map((exception) => (
              <ExceptionRow
                key={exception.id}
                exception={exception}
                isSelected={selectedExceptionId === exception.id}
                onSelect={() => onSelectException(exception.id)}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
