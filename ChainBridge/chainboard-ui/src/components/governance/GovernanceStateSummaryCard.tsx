/**
 * GovernanceStateSummaryCard — PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 *
 * Dashboard card showing governance summary statistics.
 * Read-only display of system state.
 *
 * @see PAC-SONNY-G2-PHASE-2-GOVERNANCE-LEDGER-VISIBILITY-AND-OC-INTEGRATION-01
 */

import React from 'react';
import type { GovernanceSummary } from '../../types/governanceLedger';

export interface GovernanceStateSummaryCardProps {
  /** Summary data */
  summary: GovernanceSummary | null;
  /** Loading state */
  loading?: boolean;
  /** Error state */
  error?: Error | null;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Stat item component.
 */
function StatItem({
  label,
  value,
  variant = 'default',
}: {
  label: string;
  value: number | string;
  variant?: 'default' | 'success' | 'warning' | 'error';
}) {
  const valueColors = {
    default: 'text-gray-900 dark:text-gray-100',
    success: 'text-green-600 dark:text-green-400',
    warning: 'text-amber-600 dark:text-amber-400',
    error: 'text-red-600 dark:text-red-400',
  };

  return (
    <div className="flex flex-col">
      <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
        {label}
      </span>
      <span className={`text-2xl font-bold ${valueColors[variant]}`}>
        {value}
      </span>
    </div>
  );
}

/**
 * System health indicator.
 */
function HealthIndicator({ healthy }: { healthy: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`w-3 h-3 rounded-full ${
          healthy
            ? 'bg-green-500 animate-pulse'
            : 'bg-red-500 animate-pulse'
        }`}
        role="status"
        aria-label={healthy ? 'System healthy' : 'System unhealthy'}
      />
      <span className={`text-sm font-medium ${
        healthy ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
      }`}>
        {healthy ? 'Healthy' : 'Unhealthy'}
      </span>
    </div>
  );
}

/**
 * Loading skeleton.
 */
function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="h-3 w-16 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-8 w-12 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Error state display.
 */
function ErrorState({ error }: { error: Error }) {
  return (
    <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span className="text-sm">Failed to load governance summary</span>
    </div>
  );
}

/**
 * GovernanceStateSummaryCard component.
 *
 * Displays high-level governance statistics in a card format.
 */
export function GovernanceStateSummaryCard({
  summary,
  loading = false,
  error = null,
  className = '',
}: GovernanceStateSummaryCardProps) {
  return (
    <div
      className={`
        bg-white dark:bg-gray-800
        border border-gray-200 dark:border-gray-700
        rounded-lg shadow-sm p-4
        ${className}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Governance Summary
        </h3>
        {summary && <HealthIndicator healthy={summary.system_healthy} />}
      </div>

      {/* Content */}
      {loading && <LoadingSkeleton />}
      {error && <ErrorState error={error} />}
      {!loading && !error && summary && (
        <div className="space-y-4">
          {/* Main stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatItem label="Total PACs" value={summary.total_pacs} />
            <StatItem
              label="Active"
              value={summary.active_pacs}
              variant={summary.active_pacs > 0 ? 'warning' : 'default'}
            />
            <StatItem
              label="Blocked"
              value={summary.blocked_pacs}
              variant={summary.blocked_pacs > 0 ? 'error' : 'default'}
            />
            <StatItem
              label="Positive Closures"
              value={summary.positive_closures}
              variant="success"
            />
          </div>

          {/* Secondary stats */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <StatItem
              label="Correction Cycles"
              value={summary.correction_cycles}
              variant={summary.correction_cycles > 0 ? 'warning' : 'default'}
            />
            <StatItem
              label="Pending Ratifications"
              value={summary.pending_ratifications}
              variant={summary.pending_ratifications > 0 ? 'warning' : 'default'}
            />
            <div className="flex flex-col">
              <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Last Activity
              </span>
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {formatTimestamp(summary.last_activity)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Format timestamp for display.
 */
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}

export default GovernanceStateSummaryCard;
