/**
 * LastEvaluatedBadge — PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 *
 * Timestamp badge showing when governance state was last evaluated.
 * Provides freshness indicator with visual hierarchy for situational awareness.
 *
 * Freshness States:
 * - 🟢 Fresh: < 1 minute ago
 * - 🟡 Recent: 1-5 minutes ago
 * - 🟠 Stale: 5-15 minutes ago
 * - 🔴 Outdated: > 15 minutes ago
 *
 * GUARANTEES:
 * - read_only: Display only, no mutations
 * - terminal_parity: Matches "Last Evaluated @" terminal output
 *
 * @see PAC-SONNY-P30-GOVERNANCE-UI-PARITY-SHIELD-01
 */

import { useMemo } from 'react';

/**
 * Freshness level — how stale the data is.
 */
export type FreshnessLevel = 'FRESH' | 'RECENT' | 'STALE' | 'OUTDATED';

/**
 * Calculate freshness level from timestamp.
 */
export function calculateFreshness(timestamp: string | null): FreshnessLevel {
  if (!timestamp) {
    return 'OUTDATED';
  }

  const now = Date.now();
  const evalTime = new Date(timestamp).getTime();
  const ageMs = now - evalTime;
  const ageMinutes = ageMs / (1000 * 60);

  if (ageMinutes < 1) {
    return 'FRESH';
  } else if (ageMinutes < 5) {
    return 'RECENT';
  } else if (ageMinutes < 15) {
    return 'STALE';
  } else {
    return 'OUTDATED';
  }
}

/**
 * Format timestamp for display.
 */
export function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) {
    return 'Never';
  }

  const date = new Date(timestamp);
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/**
 * Format relative time (e.g., "2 minutes ago").
 */
export function formatRelativeTime(timestamp: string | null): string {
  if (!timestamp) {
    return 'Unknown';
  }

  const now = Date.now();
  const evalTime = new Date(timestamp).getTime();
  const ageMs = now - evalTime;
  const ageSeconds = Math.floor(ageMs / 1000);
  const ageMinutes = Math.floor(ageSeconds / 60);
  const ageHours = Math.floor(ageMinutes / 60);

  if (ageSeconds < 60) {
    return 'Just now';
  } else if (ageMinutes < 60) {
    return `${ageMinutes}m ago`;
  } else if (ageHours < 24) {
    return `${ageHours}h ago`;
  } else {
    return formatTimestamp(timestamp);
  }
}

/**
 * Freshness metadata for rendering.
 */
interface FreshnessMeta {
  level: FreshnessLevel;
  glyph: string;
  label: string;
  colorClasses: {
    bg: string;
    border: string;
    text: string;
    dot: string;
  };
}

/**
 * Get metadata for freshness level.
 */
function getFreshnessMeta(level: FreshnessLevel): FreshnessMeta {
  switch (level) {
    case 'FRESH':
      return {
        level: 'FRESH',
        glyph: '🟢',
        label: 'Fresh',
        colorClasses: {
          bg: 'bg-green-50 dark:bg-green-900/20',
          border: 'border-green-200 dark:border-green-800',
          text: 'text-green-700 dark:text-green-300',
          dot: 'bg-green-500',
        },
      };
    case 'RECENT':
      return {
        level: 'RECENT',
        glyph: '🟡',
        label: 'Recent',
        colorClasses: {
          bg: 'bg-amber-50 dark:bg-amber-900/20',
          border: 'border-amber-200 dark:border-amber-800',
          text: 'text-amber-700 dark:text-amber-300',
          dot: 'bg-amber-500',
        },
      };
    case 'STALE':
      return {
        level: 'STALE',
        glyph: '🟠',
        label: 'Stale',
        colorClasses: {
          bg: 'bg-orange-50 dark:bg-orange-900/20',
          border: 'border-orange-200 dark:border-orange-800',
          text: 'text-orange-700 dark:text-orange-300',
          dot: 'bg-orange-500',
        },
      };
    case 'OUTDATED':
    default:
      return {
        level: 'OUTDATED',
        glyph: '🔴',
        label: 'Outdated',
        colorClasses: {
          bg: 'bg-red-50 dark:bg-red-900/20',
          border: 'border-red-200 dark:border-red-800',
          text: 'text-red-700 dark:text-red-300',
          dot: 'bg-red-500',
        },
      };
  }
}

export interface LastEvaluatedBadgeProps {
  /** Timestamp of last evaluation */
  timestamp: string | null;
  /** Show relative time instead of absolute */
  showRelative?: boolean;
  /** Show freshness indicator dot */
  showFreshnessIndicator?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional CSS classes */
  className?: string;
}

/**
 * LastEvaluatedBadge — Timestamp badge with freshness indicator.
 */
export function LastEvaluatedBadge({
  timestamp,
  showRelative = true,
  showFreshnessIndicator = true,
  size = 'md',
  className = '',
}: LastEvaluatedBadgeProps) {
  const freshness = useMemo(() => calculateFreshness(timestamp), [timestamp]);
  const meta = useMemo(() => getFreshnessMeta(freshness), [freshness]);
  const displayTime = useMemo(
    () => (showRelative ? formatRelativeTime(timestamp) : formatTimestamp(timestamp)),
    [timestamp, showRelative]
  );
  const absoluteTime = useMemo(() => formatTimestamp(timestamp), [timestamp]);

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5',
  };

  return (
    <div
      className={`
        inline-flex items-center gap-2
        ${meta.colorClasses.bg}
        border ${meta.colorClasses.border}
        rounded-md
        ${sizeClasses[size]}
        ${className}
      `}
      role="status"
      aria-label={`Last evaluated: ${absoluteTime}`}
      data-testid="last-evaluated-badge"
      data-freshness={freshness}
    >
      {/* Freshness indicator dot */}
      {showFreshnessIndicator && (
        <span
          className={`
            ${dotSizes[size]}
            rounded-full
            ${meta.colorClasses.dot}
            ${freshness === 'FRESH' ? 'animate-pulse' : ''}
          `}
          data-testid="freshness-indicator"
        />
      )}

      {/* Label */}
      <span className={`font-medium ${meta.colorClasses.text}`}>
        Last Evaluated @
      </span>

      {/* Timestamp */}
      <span
        className={`font-mono font-semibold ${meta.colorClasses.text}`}
        title={absoluteTime}
        data-testid="timestamp-value"
      >
        {displayTime}
      </span>
    </div>
  );
}

/**
 * LastEvaluatedCompact — Minimal inline variant.
 */
export function LastEvaluatedCompact({
  timestamp,
  className = '',
}: Pick<LastEvaluatedBadgeProps, 'timestamp' | 'className'>) {
  const freshness = calculateFreshness(timestamp);
  const meta = getFreshnessMeta(freshness);
  const displayTime = formatRelativeTime(timestamp);

  return (
    <span
      className={`
        inline-flex items-center gap-1 text-xs
        ${meta.colorClasses.text}
        ${className}
      `}
      role="status"
      aria-label={`Last evaluated: ${displayTime}`}
      data-testid="last-evaluated-compact"
      data-freshness={freshness}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${meta.colorClasses.dot}`}
        aria-hidden="true"
      />
      <span className="font-mono">{displayTime}</span>
    </span>
  );
}

export default LastEvaluatedBadge;
