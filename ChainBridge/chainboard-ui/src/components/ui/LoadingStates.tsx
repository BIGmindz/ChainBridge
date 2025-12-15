/**
 * LoadingStates - Professional loading, error, and empty state components
 *
 * Command-center grade UI states that maintain layout stability and trust.
 */

import { AlertTriangle, RefreshCw, Search } from "lucide-react";
import { classNames } from "../../utils/classNames";
import { Skeleton } from "./Skeleton";

// =============================================================================
// SKELETON COMPONENTS
// =============================================================================

/**
 * TableSkeleton - Content-shaped skeleton for queue tables
 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3" data-testid="table-skeleton">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-3 bg-slate-800/30 rounded-lg">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-3 w-12" />
          </div>
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/**
 * CardSkeleton - Content-shaped skeleton for KPI cards
 */
export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={classNames("bg-slate-800/30 rounded-lg p-4 space-y-3", className)} data-testid="card-skeleton">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4 rounded" />
      </div>
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-3 w-32" />
    </div>
  );
}

/**
 * KPISkeleton - Grid of KPI card skeletons
 */
export function KPISkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

// =============================================================================
// ERROR COMPONENTS
// =============================================================================

interface ErrorStateProps {
  title: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

/**
 * ErrorState - Localized error component with retry capability
 *
 * LIRA: Calm under stress - uses softer colors and encouraging language
 */
export function ErrorState({ title, message, onRetry, className }: ErrorStateProps) {
  return (
    <div className={classNames(
      "flex flex-col items-center justify-center p-8 text-center bg-slate-800/30 rounded-lg border border-slate-700/30",
      "transition-all duration-300",
      className
    )}>
      <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center mb-4">
        <AlertTriangle className="h-5 w-5 text-amber-400/80" />
      </div>
      <h3 className="text-sm font-medium text-slate-200 mb-1">{title}</h3>
      {message && (
        <p className="text-xs text-slate-400/80 mb-4 max-w-sm leading-relaxed">{message}</p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 rounded-lg transition-all duration-200"
        >
          <RefreshCw className="h-3 w-3" />
          Try again
        </button>
      )}
    </div>
  );
}

/**
 * InlineError - Compact error for table cells or small spaces
 */
export function InlineError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center gap-2 text-xs text-amber-400/80">
      <div className="w-1.5 h-1.5 rounded-full bg-amber-400/60" />
      <span className="text-slate-400">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-slate-500 hover:text-slate-300 transition-colors"
          title="Retry"
          aria-label="Retry"
        >
          <RefreshCw className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

// =============================================================================
// EMPTY STATES
// =============================================================================

interface EmptyStateProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  className?: string;
}

/**
 * EmptyState - Professional empty data state
 */
export function EmptyState({ title, subtitle, icon, className }: EmptyStateProps) {
  const defaultIcon = <Search className="h-12 w-12 text-slate-500" />;

  return (
    <div className={classNames(
      "flex flex-col items-center justify-center p-12 text-center",
      className
    )}>
      <div className="mb-4 opacity-60">
        {icon || defaultIcon}
      </div>
      <h3 className="text-sm font-medium text-slate-300 mb-2">{title}</h3>
      {subtitle && (
        <p className="text-xs text-slate-500 max-w-sm">{subtitle}</p>
      )}
    </div>
  );
}
